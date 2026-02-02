#!/usr/bin/env python3
"""
Benchmark average tokens for a "complex process" by running an API call and
aggregating LLM token usage from audit_events by trace_id.

Default mode uses chat:
  - POST /api/v1/chat/start
  - POST /api/v1/chat/message (with a complex prompt)
  - Query audit_events for that trace_id and sum input/output tokens

Requires:
  - Janus API running
  - Postgres reachable (for chat mode)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from uuid import uuid4

try:
    import psycopg  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency at runtime
    psycopg = None  # type: ignore
    _PSYCOPG_IMPORT_ERROR = exc
else:
    _PSYCOPG_IMPORT_ERROR = None

try:
    import psycopg2  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency at runtime
    psycopg2 = None  # type: ignore
    _PSYCOPG2_IMPORT_ERROR = exc
else:
    _PSYCOPG2_IMPORT_ERROR = None

try:
    import requests  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency at runtime
    requests = None  # type: ignore
    _REQUESTS_IMPORT_ERROR = exc
else:
    _REQUESTS_IMPORT_ERROR = None


DEFAULT_PROMPT = (
    "You are a senior systems architect.\n"
    "Task:\n"
    "1) Summarize requirements for a multi-agent AI assistant for a small team.\n"
    "2) Propose a 3-phase implementation plan with milestones.\n"
    "3) List 10 risks with mitigations.\n"
    "4) Provide a minimal API schema with 5 endpoints in JSON.\n"
    "5) Provide a test strategy with 8 bullet points.\n"
    "\n"
    "Constraints:\n"
    "- Use clear headings and lists.\n"
    "- Do not call external tools or access the network.\n"
)


@dataclass
class TokenSample:
    trace_id: str
    calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_s: float


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return values
    except Exception as exc:
        raise RuntimeError(f"Failed to read env file: {path} ({exc})") from exc

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _get_setting(env: Dict[str, str], key: str, default: Optional[str]) -> Optional[str]:
    return os.getenv(key) or env.get(key) or default


def _require_requests() -> None:
    if requests is None:
        raise RuntimeError(f"requests is required but not available: {_REQUESTS_IMPORT_ERROR}")


def _require_psycopg() -> None:
    if psycopg is None and psycopg2 is None:
        msg = "psycopg or psycopg2 is required for DB access but not available."
        if _PSYCOPG_IMPORT_ERROR:
            msg += f" psycopg error: {_PSYCOPG_IMPORT_ERROR}"
        if _PSYCOPG2_IMPORT_ERROR:
            msg += f" psycopg2 error: {_PSYCOPG2_IMPORT_ERROR}"
        raise RuntimeError(msg)


def _post_json(
    url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float
) -> Dict[str, Any]:
    _require_requests()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)  # type: ignore[arg-type]
    except Exception as exc:
        raise RuntimeError(f"HTTP request failed for {url}: {exc}") from exc
    try:
        data = resp.json()
    except Exception:
        data = {"_raw": resp.text}
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} from {url}: {data}")
    return data  # type: ignore[return-value]


def _start_conversation(
    base_url: str,
    user_id: str,
    project_id: Optional[str],
    timeout: float,
) -> str:
    url = f"{base_url}/api/v1/chat/start"
    payload: Dict[str, Any] = {"user_id": user_id}
    if project_id:
        payload["project_id"] = project_id
    data = _post_json(url, payload, headers={}, timeout=timeout)
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        raise RuntimeError(f"Chat start did not return conversation_id: {data}")
    return str(conversation_id)


def _send_chat_message(
    base_url: str,
    conversation_id: str,
    message: str,
    role: str,
    priority: str,
    timeout_seconds: Optional[int],
    user_id: str,
    project_id: Optional[str],
    headers: Dict[str, str],
    timeout: float,
) -> Dict[str, Any]:
    url = f"{base_url}/api/v1/chat/message"
    payload: Dict[str, Any] = {
        "conversation_id": conversation_id,
        "message": message,
        "role": role,
        "priority": priority,
        "timeout_seconds": timeout_seconds,
        "user_id": user_id,
        "project_id": project_id,
    }
    return _post_json(url, payload, headers=headers, timeout=timeout)


def _invoke_llm(
    base_url: str,
    prompt: str,
    role: str,
    priority: str,
    timeout_seconds: Optional[int],
    user_id: str,
    project_id: Optional[str],
    headers: Dict[str, str],
    timeout: float,
) -> Dict[str, Any]:
    url = f"{base_url}/api/v1/llm/invoke"
    payload: Dict[str, Any] = {
        "prompt": prompt,
        "role": role,
        "priority": priority,
        "timeout_seconds": timeout_seconds,
        "user_id": user_id,
        "project_id": project_id,
    }
    return _post_json(url, payload, headers=headers, timeout=timeout)


def _connect_db(
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str,
) -> Any:
    _require_psycopg()

    def _connect(target_host: str):
        if psycopg is not None:
            return psycopg.connect(  # type: ignore[call-arg]
                host=target_host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
            )
        return psycopg2.connect(  # type: ignore[call-arg]
            host=target_host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
        )

    try:
        conn = _connect(host)
        conn.autocommit = True
        return conn
    except Exception as exc:
        if host == "postgres":
            try:
                conn = _connect("localhost")
                conn.autocommit = True
                return conn
            except Exception:
                pass
        raise RuntimeError(f"Failed to connect to Postgres at {host}:{port} ({exc})") from exc


def _query_tokens_for_trace(conn: Any, trace_id: str) -> Tuple[int, int, int, float]:
    sql = """
    WITH ev AS (
        SELECT (details_json #>> '{}')::jsonb AS dj
        FROM audit_events
        WHERE trace_id = %s
          AND endpoint = 'llm'
          AND action = 'invoke'
          AND status = 'ok'
    )
    SELECT
        COUNT(*) AS calls,
        COALESCE(SUM(NULLIF(dj->>'input_tokens', '')::int), 0) AS input_tokens,
        COALESCE(SUM(NULLIF(dj->>'output_tokens', '')::int), 0) AS output_tokens,
        COALESCE(SUM(NULLIF(dj->>'cost_usd', '')::numeric), 0) AS cost_usd
    FROM ev;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (trace_id,))
        row = cur.fetchone()
    if not row:
        return 0, 0, 0, 0.0
    calls = int(row[0] or 0)
    in_tokens = int(row[1] or 0)
    out_tokens = int(row[2] or 0)
    cost = float(row[3] or 0.0)
    return calls, in_tokens, out_tokens, cost


def _wait_for_tokens(
    conn: Any, trace_id: str, retries: int, delay_s: float
) -> Tuple[int, int, int, float]:
    for _ in range(retries):
        calls, in_tokens, out_tokens, cost = _query_tokens_for_trace(conn, trace_id)
        if calls > 0:
            return calls, in_tokens, out_tokens, cost
        time.sleep(delay_s)
    return _query_tokens_for_trace(conn, trace_id)


def _read_prompt(prompt_arg: Optional[str], prompt_file: Optional[str]) -> str:
    if prompt_arg:
        return prompt_arg
    if prompt_file:
        try:
            return Path(prompt_file).read_text(encoding="utf-8")
        except Exception as exc:
            raise RuntimeError(f"Failed to read prompt file: {prompt_file} ({exc})") from exc
    return DEFAULT_PROMPT


def _summarize(samples: Iterable[TokenSample]) -> Dict[str, float]:
    items = list(samples)
    if not items:
        return {}
    total_calls = sum(s.calls for s in items)
    total_in = sum(s.input_tokens for s in items)
    total_out = sum(s.output_tokens for s in items)
    total_tokens = sum(s.total_tokens for s in items)
    total_cost = sum(s.cost_usd for s in items)
    total_latency = sum(s.latency_s for s in items)
    n = float(len(items))
    return {
        "runs": n,
        "avg_calls": total_calls / n,
        "avg_input_tokens": total_in / n,
        "avg_output_tokens": total_out / n,
        "avg_total_tokens": total_tokens / n,
        "avg_cost_usd": total_cost / n,
        "avg_latency_s": total_latency / n,
        "min_total_tokens": float(min(s.total_tokens for s in items)),
        "max_total_tokens": float(max(s.total_tokens for s in items)),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark average tokens for a complex Janus process."
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--mode", choices=["chat", "llm"], default="chat")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--role", default="orchestrator")
    parser.add_argument("--priority", default="high_quality")
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument("--user-id", default="benchmark_user")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--prompt-file", default=None)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--db-host", default=None)
    parser.add_argument("--db-port", type=int, default=None)
    parser.add_argument("--db-user", default=None)
    parser.add_argument("--db-password", default=None)
    parser.add_argument("--db-name", default=None)
    parser.add_argument("--db-retries", type=int, default=10)
    parser.add_argument("--db-retry-delay", type=float, default=0.5)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.runs < 1:
        raise RuntimeError("--runs must be >= 1")

    env_path = (
        Path(args.env_file)
        if args.env_file
        else (Path(__file__).resolve().parents[1] / "app" / ".env")
    )
    env_values = _load_env_file(env_path)

    base_url = args.base_url.rstrip("/")
    prompt = _read_prompt(args.prompt, args.prompt_file)

    user_id = args.user_id
    project_id = args.project_id

    db_host = args.db_host or _get_setting(env_values, "POSTGRES_HOST", "localhost")
    db_port = args.db_port or int(_get_setting(env_values, "POSTGRES_PORT", "5432") or 5432)
    db_user = args.db_user or _get_setting(env_values, "POSTGRES_USER", "janus")
    db_password = args.db_password or _get_setting(env_values, "POSTGRES_PASSWORD", "janus_pass")
    db_name = args.db_name or _get_setting(env_values, "POSTGRES_DB", "janus_db")

    conn = None
    if args.mode == "chat":
        if not all([db_host, db_user, db_password, db_name]):
            raise RuntimeError("Postgres config missing for chat mode. Use --db-* args.")
        conn = _connect_db(str(db_host), int(db_port), str(db_user), str(db_password), str(db_name))

    samples: list[TokenSample] = []
    for idx in range(args.runs):
        trace_id = uuid4().hex
        headers = {"X-Request-ID": trace_id, "X-User-Id": user_id}
        if project_id:
            headers["X-Project-Id"] = project_id

        start_time = time.perf_counter()
        if args.mode == "chat":
            conversation_id = _start_conversation(base_url, user_id, project_id, args.timeout)
            _send_chat_message(
                base_url=base_url,
                conversation_id=conversation_id,
                message=prompt,
                role=args.role,
                priority=args.priority,
                timeout_seconds=args.timeout_seconds,
                user_id=user_id,
                project_id=project_id,
                headers=headers,
                timeout=args.timeout,
            )
            calls, in_tokens, out_tokens, cost = _wait_for_tokens(
                conn,
                trace_id,
                args.db_retries,
                args.db_retry_delay,  # type: ignore[arg-type]
            )
        else:
            data = _invoke_llm(
                base_url=base_url,
                prompt=prompt,
                role=args.role,
                priority=args.priority,
                timeout_seconds=args.timeout_seconds,
                user_id=user_id,
                project_id=project_id,
                headers=headers,
                timeout=args.timeout,
            )
            calls = 1
            in_tokens = int(data.get("input_tokens") or 0)
            out_tokens = int(data.get("output_tokens") or 0)
            cost = float(data.get("cost_usd") or 0.0)

        latency_s = time.perf_counter() - start_time
        total_tokens = in_tokens + out_tokens
        sample = TokenSample(
            trace_id=trace_id,
            calls=calls,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_s=latency_s,
        )
        samples.append(sample)

        print(
            f"[{idx + 1}/{args.runs}] trace_id={trace_id} calls={calls} "
            f"in={in_tokens} out={out_tokens} total={total_tokens} "
            f"cost=${cost:.6f} latency={latency_s:.2f}s"
        )
        if args.sleep > 0 and idx + 1 < args.runs:
            time.sleep(args.sleep)

    summary = _summarize(samples)
    if summary:
        print("\nSummary")
        print(json.dumps(summary, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
