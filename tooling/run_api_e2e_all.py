#!/usr/bin/env python3
"""
Execute one runtime probe for every /api/v1 endpoint in the live OpenAPI spec.

Goals:
- 100% endpoint invocation coverage (method+path)
- Contract-aware pass/fail classification
- Minimal explicit fixtures; OpenAPI-driven auto probes for the rest
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests
from qa_request_support import (
    DockerLogCorrelator,
    bootstrap_local_auth,
    classify_gate,
    classify_http_status,
    generate_request_id,
    isoformat_utc,
    save_json as save_json_shared,
    utc_now,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "tooling" / "api_e2e_fixtures.json"
DEFAULT_REPORT_JSON = ROOT / "outputs" / "qa" / "all_api_e2e_report.json"
DEFAULT_REPORT_MD = ROOT / "outputs" / "qa" / "all_api_e2e_report.md"
DEFAULT_FAILURES_JSON = ROOT / "outputs" / "qa" / "all_api_e2e_failures.json"
DEFAULT_OPENAPI_SNAPSHOT = ROOT / "outputs" / "qa" / "openapi_snapshot.json"
DEFAULT_DUAL_OUTPUT_DIR = ROOT / "outputs" / "qa" / "api_e2e_dual_mode"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
RE_TEMPLATE = re.compile(r"\{\{([^}]+)\}\}")


@dataclass
class Endpoint:
    method: str
    path: str
    operation_id: str
    module: str
    details: dict[str, Any]


class ContextStore:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.set("runtime.unique", f"e2e-{int(time.time())}")
        self.set("runtime.ts_epoch", int(time.time()))

    def get(self, path: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def set(self, path: str, value: Any) -> None:
        cur = self.data
        parts = path.split(".")
        for part in parts[:-1]:
            nxt = cur.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt
            cur = nxt
        cur[parts[-1]] = value


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    out = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            out[k] = "<redacted>"
        else:
            out[k] = v
    return out


def fetch_openapi(openapi_url: str, timeout: float) -> dict[str, Any]:
    resp = requests.get(openapi_url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def load_fixtures(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    if isinstance(raw, dict) and "fixtures" in raw:
        items = raw["fixtures"]
    else:
        items = raw
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        op_id = item["operation_id"]
        out[op_id] = item
    return out


def iter_endpoints(openapi: dict[str, Any]) -> list[Endpoint]:
    rows: list[Endpoint] = []
    for path, methods in openapi.get("paths", {}).items():
        if not path.startswith("/api/v1/"):
            continue
        for method, details in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue
            rows.append(
                Endpoint(
                    method=method.upper(),
                    path=path,
                    operation_id=details.get("operationId") or f"{method}_{path}",
                    module=(details.get("tags") or ["unknown"])[0],
                    details=details,
                )
            )
    return rows


def build_endpoint_index(endpoints: Iterable[Endpoint]) -> dict[tuple[str, str], Endpoint]:
    return {(e.method, e.path): e for e in endpoints}


def resolve_ref(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return {}
        cur: Any = openapi
        for part in ref[2:].split("/"):
            cur = cur.get(part, {})
        if isinstance(cur, dict):
            merged = copy.deepcopy(cur)
            overlay = {k: v for k, v in schema.items() if k != "$ref"}
            if overlay:
                merged.update(overlay)
            return merged
        return {}
    return schema


def choose_non_null_schema(openapi: dict[str, Any], options: list[Any]) -> dict[str, Any]:
    for opt in options:
        resolved = resolve_ref(openapi, opt if isinstance(opt, dict) else {})
        if resolved.get("type") != "null":
            return resolved
    if options:
        return resolve_ref(openapi, options[0] if isinstance(options[0], dict) else {})
    return {}


def sample_string(name: str, schema: dict[str, Any], ctx: ContextStore) -> str:
    if "enum" in schema and schema["enum"]:
        return str(schema["enum"][0])
    fmt = schema.get("format")
    min_len = int(schema.get("minLength", 0) or 0)
    lower_name = (name or "").lower()
    if "email" in lower_name or fmt == "email":
        return f"{ctx.get('runtime.unique')}@example.com"
    if "password" in lower_name:
        return "JanusE2E123!"
    if lower_name in {"username", "user_name"}:
        return f"user-{ctx.get('runtime.unique')}"[: max(3, schema.get("maxLength", 50))]
    if "full_name" in lower_name or lower_name == "name":
        return "Janus E2E"
    if "cpf" in lower_name:
        return "12345678901"
    if "phone" in lower_name:
        return "+5511999999999"
    if "url" in lower_name or fmt == "uri":
        return "https://example.com"
    if "timestamp" in lower_name:
        return str(int(time.time()))
    if lower_name in {"provider"}:
        return "deepseek"
    if lower_name in {"model"}:
        return "deepseek-chat"
    if lower_name in {"outcome"}:
        return "success"
    if lower_name in {"role"}:
        return "auto"
    if lower_name in {"priority"}:
        return "fast_and_cheap"
    if lower_name in {"format"}:
        return "json"
    if "message" in lower_name:
        return "E2E runtime probe message"
    if "title" in lower_name:
        return "E2E Title"
    if "query" in lower_name or "question" in lower_name:
        return "What does this endpoint return?"
    if "path" in lower_name:
        return "/app/workspace"
    if "tool" in lower_name:
        return "list_directory"
    if "status" in lower_name:
        return "pending"
    if "id" in lower_name:
        return str(uuid.uuid4())
    base = "x"
    if min_len > 1:
        base = "x" * min_len
    return base


def sample_value(openapi: dict[str, Any], name: str, schema: dict[str, Any], ctx: ContextStore) -> Any:
    schema = resolve_ref(openapi, schema)
    if not schema:
        return "x"
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if "anyOf" in schema:
        return sample_value(openapi, name, choose_non_null_schema(openapi, schema["anyOf"]), ctx)
    if "oneOf" in schema:
        return sample_value(openapi, name, choose_non_null_schema(openapi, schema["oneOf"]), ctx)
    t = schema.get("type")
    if t == "object" or ("properties" in schema and t is None):
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        out: dict[str, Any] = {}
        for prop_name, prop_schema in props.items():
            if prop_name in required:
                out[prop_name] = sample_value(openapi, prop_name, prop_schema, ctx)
        return out
    if t == "array":
        item_schema = schema.get("items", {})
        return [sample_value(openapi, name, item_schema, ctx)]
    if t == "integer":
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)):
            return int(minimum)
        if "timestamp" in name.lower():
            return int(time.time())
        return 1
    if t == "number":
        if "latency" in name.lower() or "ttft" in name.lower():
            return 123.4
        if "timestamp" in name.lower():
            return time.time()
        return 1.0
    if t == "boolean":
        if name.lower() == "terms":
            return True
        return False
    return sample_string(name, schema, ctx)


def interpolate_templates(obj: Any, ctx: ContextStore) -> Any:
    if isinstance(obj, str):
        def repl(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            val = ctx.get(key)
            return "" if val is None else str(val)
        return RE_TEMPLATE.sub(repl, obj)
    if isinstance(obj, list):
        return [interpolate_templates(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: interpolate_templates(v, ctx) for k, v in obj.items()}
    return obj


def path_param_sample(name: str, schema: dict[str, Any], ctx: ContextStore) -> Any:
    lname = name.lower()
    if lname == "conversation_id":
        return ctx.get("chat.conversation_id", "missing-conversation")
    if lname == "request_id":
        return ctx.get("observability.request_id", "missing-request-id")
    if lname == "tool_name":
        return ctx.get("tools.tool_name", "list_directory")
    if lname == "entity_name":
        return "TestEntity"
    return sample_value({}, name, schema, ctx) if schema.get("type") in {"integer", "number"} else sample_string(name, schema, ctx)


def query_param_sample(name: str, schema: dict[str, Any], ctx: ContextStore) -> Any:
    lname = name.lower()
    if lname == "user_id":
        return ctx.get("auth.local.user_id", "seed-admin")
    if lname == "project_id":
        return "e2e-project"
    if lname == "limit":
        return 5
    if lname == "offset":
        return 0
    if lname == "window_minutes":
        return 15
    if lname == "min_events":
        return 1
    if lname == "window_hours":
        return 6
    if lname == "bucket_minutes":
        return 15
    if lname == "include_details":
        return False
    if lname == "format":
        return "json"
    if lname == "status":
        return "pending"
    if lname == "tool":
        return "list_directory"
    if lname == "queue":
        return "default"
    if lname == "message":
        return "E2E stream probe"
    if lname == "role":
        return "auto"
    if lname == "priority":
        return "fast_and_cheap"
    if lname == "timeout_seconds":
        return 5
    return sample_value({}, name, schema, ctx)


def collect_expected_statuses(endpoint: Endpoint, fixture: dict[str, Any] | None) -> list[int]:
    if fixture and fixture.get("expected_statuses"):
        return sorted({int(x) for x in fixture["expected_statuses"]})
    documented = []
    for code in (endpoint.details.get("responses") or {}).keys():
        if str(code).isdigit():
            documented.append(int(code))
    defaults = {
        "GET": [200, 204, 400, 401, 403, 404, 405, 422],
        "POST": [200, 201, 202, 204, 400, 401, 403, 404, 405, 409, 415, 422],
        "PUT": [200, 204, 400, 401, 403, 404, 405, 409, 415, 422],
        "PATCH": [200, 204, 400, 401, 403, 404, 405, 409, 415, 422],
        "DELETE": [200, 202, 204, 400, 401, 403, 404, 405, 409, 422],
    }
    return sorted(set(documented + defaults.get(endpoint.method, [200, 422])))


def endpoint_is_streaming(endpoint: Endpoint) -> bool:
    if "stream" in endpoint.path.lower() or "stream" in endpoint.operation_id.lower():
        return True
    responses = endpoint.details.get("responses") or {}
    for resp_meta in responses.values():
        if not isinstance(resp_meta, dict):
            continue
        content = resp_meta.get("content") or {}
        if "text/event-stream" in content:
            return True
    return False


def classify_status(actual: int, expected: list[int]) -> str:
    if actual in expected:
        if 200 <= actual < 400:
            return "pass_success"
        return "pass_contract_rejection"
    if 500 <= actual <= 599:
        return "fail_server_5xx"
    return "fail_unexpected_status"


def retry_after_seconds(resp: requests.Response, attempt: int) -> float:
    header = (resp.headers.get("Retry-After") or "").strip()
    if header.isdigit():
        return max(0.25, float(header))
    # Conservative exponential backoff for API-wide rate limits.
    return min(8.0, 0.5 * (2 ** max(0, attempt - 1)))


def extract_json_path(payload: Any, path: str) -> Any:
    cur = payload
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
            continue
        if isinstance(cur, list) and part.isdigit():
            idx = int(part)
            if 0 <= idx < len(cur):
                cur = cur[idx]
                continue
        return None
    return cur


def infer_context_from_response(endpoint: Endpoint, body: Any, ctx: ContextStore) -> None:
    if not isinstance(body, dict):
        return
    if endpoint.operation_id == "local_login_api_v1_auth_local_login_post":
        token = body.get("access_token") or body.get("token")
        if token:
            ctx.set("auth.local.access_token", token)
    if endpoint.operation_id == "local_register_api_v1_auth_local_register_post":
        for k in ("user_id", "id"):
            if k in body and isinstance(body[k], (str, int)):
                ctx.set("auth.local.user_id", str(body[k]))
                break
    if endpoint.operation_id == "start_chat_api_v1_chat_start_post":
        conv = body.get("conversation_id") or body.get("id")
        if conv:
            ctx.set("chat.conversation_id", str(conv))
    # Generic heuristic for request dashboard
    for key in ("request_id",):
        val = body.get(key)
        if isinstance(val, (str, int)):
            ctx.set(f"observability.{key}", str(val))


def build_request(
    endpoint: Endpoint,
    openapi: dict[str, Any],
    ctx: ContextStore,
    fixture: dict[str, Any] | None,
    *,
    allow_auto_auth: bool = True,
) -> tuple[str, dict[str, Any], dict[str, str], Any, str | None]:
    path = endpoint.path
    query: dict[str, Any] = {}
    headers: dict[str, str] = {}
    json_body: Any = None
    data_body: Any = None
    content_type: str | None = None

    if fixture:
        fixture = interpolate_templates(fixture, ctx)

    # Path/query params
    params_meta = endpoint.details.get("parameters") or []
    for p in params_meta:
        name = p.get("name")
        where = p.get("in")
        required = bool(p.get("required"))
        schema = p.get("schema") or {}
        if where == "path":
            value = None
            if fixture and name in (fixture.get("path_params") or {}):
                value = fixture["path_params"][name]
            elif required:
                value = path_param_sample(name, schema, ctx)
            if value is None:
                value = path_param_sample(name, schema, ctx)
            path = path.replace(f"{{{name}}}", str(value))
        elif where == "query":
            if fixture and name in (fixture.get("query") or {}):
                query[name] = fixture["query"][name]
            elif required:
                query[name] = query_param_sample(name, schema, ctx)

    if fixture and fixture.get("query"):
        for k, v in fixture["query"].items():
            query[k] = v

    if fixture and fixture.get("headers"):
        headers.update({str(k): str(v) for k, v in fixture["headers"].items()})

    # Default bearer token after login (unless auth endpoints)
    token = ctx.get("auth.local.access_token")
    if allow_auto_auth and token and "authorization" not in {k.lower() for k in headers}:
        if not endpoint.path.startswith("/api/v1/auth/"):
            headers["Authorization"] = f"Bearer {token}"

    # Request body
    request_body = endpoint.details.get("requestBody") or {}
    content = request_body.get("content") or {}
    selected_ct = None
    for candidate in ("application/json", "application/x-www-form-urlencoded", "multipart/form-data"):
        if candidate in content:
            selected_ct = candidate
            break
    if selected_ct:
        content_type = selected_ct
        schema = content[selected_ct].get("schema") or {}
        generated = sample_value(openapi, endpoint.operation_id, schema, ctx)
        if fixture and "json_body" in fixture and selected_ct == "application/json":
            generated = fixture["json_body"]
        if fixture and "form_body" in fixture and selected_ct != "application/json":
            generated = fixture["form_body"]
        # Auto probes favor contract validation (422) over deep execution to minimize 5xx.
        if not fixture:
            if selected_ct == "application/json":
                generated = {}
            else:
                generated = {}

        if selected_ct == "application/json":
            json_body = generated
        elif selected_ct == "application/x-www-form-urlencoded":
            data_body = generated if isinstance(generated, dict) else {}
        else:
            # Multipart not auto-generated with files in first iteration.
            # Use simple form fields if any; otherwise let contract reject.
            data_body = generated if isinstance(generated, dict) else {}

    return path, query, headers, json_body if json_body is not None else data_body, content_type


def summarize_response(resp: requests.Response) -> dict[str, Any]:
    info: dict[str, Any] = {
        "status_code": resp.status_code,
        "content_type": resp.headers.get("content-type"),
        "content_length": len(resp.content or b""),
    }
    ct = (resp.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        try:
            payload = resp.json()
            info["json_type"] = type(payload).__name__
            if isinstance(payload, dict):
                info["json_keys"] = list(payload.keys())[:20]
            elif isinstance(payload, list):
                info["json_items"] = len(payload)
            return info
        except Exception:
            info["json_parse_error"] = True
    snippet = (resp.text or "")[:240]
    if snippet:
        info["text_snippet"] = snippet
    return info


def module_priority(name: str) -> int:
    order = [
        "Auth",
        "System",
        "Workers",
        "Observability",
        "Chat",
        "Tools",
        "Knowledge",
        "LLM",
        "Learning",
        "Agent",
        "Assistant",
        "Autonomy",
        "Tasks",
        "Collaboration",
        "Productivity",
        "Admin",
    ]
    try:
        return order.index(name)
    except ValueError:
        return 999


def fixture_order(fixture: dict[str, Any] | None) -> int:
    if not fixture:
        return 500
    try:
        return int(fixture.get("order", 500))
    except Exception:
        return 500


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# API E2E All Endpoints Report",
        "",
        f"- OpenAPI total endpoints: `{s['openapi_total_endpoints']}`",
        f"- Executed unique endpoints: `{s['executed_unique_endpoints']}`",
        f"- Total probes: `{s['total_probes']}`",
        f"- pass_success: `{s['pass_success']}`",
        f"- pass_contract_rejection: `{s['pass_contract_rejection']}`",
        f"- fail_unexpected_status: `{s['fail_unexpected_status']}`",
        f"- fail_server_5xx: `{s['fail_server_5xx']}`",
        f"- fail_transport: `{s['fail_transport']}`",
        "",
        "## Failures",
    ]
    failures = report["failures"]
    if not failures:
        lines.append("- None")
    else:
        for row in failures[:200]:
            lines.append(
                f"- `{row['method']} {row['path']}` (`{row['operation_id']}`) -> "
                f"`{row.get('actual_status', 'transport')}` [{row['result_class']}]"
            )
    return "\n".join(lines) + "\n"


def _new_summary_bucket() -> dict[str, int]:
    return {
        "pass_success": 0,
        "pass_contract_rejection": 0,
        "pass_expected_auth_rejection": 0,
        "pass_expected_contract_rejection": 0,
        "blocked_by_env_expected": 0,
        "fail_unexpected_status": 0,
        "fail_server_5xx": 0,
        "fail_transport": 0,
    }


def _run_phase(
    args: argparse.Namespace,
    *,
    phase: str,
    boot: dict[str, Any] | None = None,
    request_id_seq_start: int = 0,
) -> tuple[dict[str, Any], int]:
    ctx = ContextStore()
    ctx.set("auth.local.user_id", args.seed_user_id)
    allow_auto_auth = phase != "unauth"
    if boot and boot.get("ok"):
        if boot.get("token"):
            ctx.set("auth.local.access_token", boot["token"])
        if boot.get("user_id"):
            ctx.set("auth.local.user_id", boot["user_id"])

    session = requests.Session()
    openapi = fetch_openapi(args.openapi_url, args.timeout)
    endpoints = iter_endpoints(openapi)
    fixtures = load_fixtures(Path(args.fixtures))
    rows = list({(e.method, e.path, e.operation_id): e for e in endpoints}.values())
    rows.sort(key=lambda e: (fixture_order(fixtures.get(e.operation_id)), module_priority(e.module), e.module, e.path, e.method))
    if args.limit > 0:
        rows = rows[: args.limit]

    correlator = None
    if args.with_log_correlation:
        correlator = DockerLogCorrelator(
            service=args.log_service,
            container=args.log_container,
            grace_log_ms=args.grace_log_ms,
            since_padding_sec=args.log_since_padding_sec,
            include_weak_fallback=True,
        )

    probe_results: list[dict[str, Any]] = []
    log_evidence_rows: list[dict[str, Any]] = []
    executed_unique = set()
    last_request_started_at = 0.0
    total_429_retries = 0
    seq = request_id_seq_start

    total_rows = len(rows)
    for idx, endpoint in enumerate(rows, start=1):
        seq += 1
        fixture = fixtures.get(endpoint.operation_id)
        expected_statuses = collect_expected_statuses(endpoint, fixture)
        if args.progress_every > 0 and (idx == 1 or idx % args.progress_every == 0 or idx == total_rows):
            print(f"[{phase}] {idx}/{total_rows} {endpoint.method} {endpoint.path} ({endpoint.operation_id})", flush=True)

        now = time.perf_counter()
        min_gap_seconds = max(0.0, args.min_interval_ms / 1000.0)
        if last_request_started_at > 0 and min_gap_seconds > 0:
            remaining = min_gap_seconds - (now - last_request_started_at)
            if remaining > 0:
                time.sleep(remaining)

        started = time.perf_counter()
        last_request_started_at = started
        t0_dt = utc_now()
        request_meta: dict[str, Any] = {}
        request_id = generate_request_id(args.request_id_prefix, phase, "api", seq)
        try:
            path, query, headers, body, content_type = build_request(
                endpoint,
                openapi,
                ctx,
                fixture,
                allow_auto_auth=allow_auto_auth,
            )
            url = args.base_url.rstrip("/") + path
            headers = dict(headers)
            headers["X-Request-ID"] = request_id
            headers.setdefault("User-Agent", f"Janus-API-E2E-All/{getattr(args, 'client_version', '2.1.0')}")
            if phase == "unauth":
                headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}

            request_meta = {
                "phase": phase,
                "request_id": request_id,
                "query": query,
                "headers": sanitize_headers(headers),
                "has_body": body is not None,
                "content_type": content_type,
            }
            if isinstance(body, dict):
                request_meta["body_keys"] = list(body.keys())[:30]
            if fixture and fixture.get("destructive") is True:
                request_meta["destructive"] = True

            per_request_timeout = float((fixture or {}).get("timeout_seconds", args.timeout))
            req_kwargs: dict[str, Any] = {"params": query, "headers": headers, "timeout": per_request_timeout}
            if content_type == "application/json":
                req_kwargs["json"] = body
            elif content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
                req_kwargs["data"] = body if isinstance(body, dict) else {}
            is_streaming = endpoint_is_streaming(endpoint)
            if is_streaming:
                req_kwargs["stream"] = True

            retry_count = 0
            resp = session.request(endpoint.method, url, **req_kwargs)
            while resp.status_code == 429 and retry_count < args.max_429_retries:
                retry_count += 1
                total_429_retries += 1
                backoff = retry_after_seconds(resp, retry_count)
                print(f"[retry429:{phase}] {endpoint.method} {endpoint.path} attempt={retry_count} backoff={backoff:.2f}s", flush=True)
                time.sleep(backoff)
                try:
                    resp.close()
                except Exception:
                    pass
                last_request_started_at = time.perf_counter()
                t0_dt = utc_now()
                resp = session.request(endpoint.method, url, **req_kwargs)

            duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
            note_text = str((fixture or {}).get("notes", ""))
            result_class = classify_http_status(
                resp.status_code,
                expected_statuses,
                phase=phase,
                path=endpoint.path,
                notes=note_text,
            )
            if is_streaming:
                summary = {
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("content-type"),
                    "streaming": True,
                }
            else:
                summary = summarize_response(resp)

            payload = None
            if not is_streaming:
                if fixture and isinstance(fixture.get("extract"), dict):
                    try:
                        payload = resp.json()
                    except Exception:
                        payload = None
                    if payload is not None:
                        for ctx_key, json_path in fixture["extract"].items():
                            val = extract_json_path(payload, str(json_path))
                            if val is not None:
                                ctx.set(ctx_key, val)
                if payload is None:
                    try:
                        payload = resp.json()
                    except Exception:
                        payload = None
                if payload is not None:
                    infer_context_from_response(endpoint, payload, ctx)

            response_echo_request_id = resp.headers.get("X-Request-ID")
            log_match = None
            if correlator:
                log_match = correlator.correlate(
                    request_id=request_id,
                    method=endpoint.method,
                    path=path,
                    phase=phase,
                    suite="api",
                    t0=t0_dt,
                    response_echo_request_id=response_echo_request_id,
                )
                log_evidence_rows.append(
                    {
                        "request_id": log_match.request_id,
                        "phase": log_match.phase,
                        "suite": log_match.suite,
                        "log_source": log_match.log_source,
                        "match_type": log_match.match_type,
                        "matched_lines": log_match.matched_lines,
                        "error_lines": log_match.error_lines,
                        "response_echo_request_id": log_match.response_echo_request_id,
                    }
                )

            try:
                resp.close()
            except Exception:
                pass

            log_evidence = log_match.match_type if log_match else "not_collected"
            row = {
                "phase": phase,
                "operation_id": endpoint.operation_id,
                "module": endpoint.module,
                "method": endpoint.method,
                "path": endpoint.path,
                "scenario_name": (fixture or {}).get("scenario_name", "auto_contract_probe"),
                "expected_statuses": expected_statuses,
                "actual_status": resp.status_code,
                "result_class": result_class,
                "duration_ms": duration_ms,
                "request": request_meta,
                "response_summary": summary,
                "response_echo_request_id": response_echo_request_id,
                "log_evidence": log_evidence,
                "log_error_lines": (log_match.error_lines if log_match else []),
                "gate_class": classify_gate(result_class, log_evidence if args.with_log_correlation else "strong"),
            }
            if retry_count:
                row["request"]["retry_429_count"] = retry_count
        except requests.RequestException as exc:
            duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
            log_match = None
            if correlator:
                log_match = correlator.correlate(
                    request_id=request_id,
                    method=endpoint.method,
                    path=endpoint.path,
                    phase=phase,
                    suite="api",
                    t0=t0_dt,
                    response_echo_request_id=None,
                )
                log_evidence_rows.append(
                    {
                        "request_id": log_match.request_id,
                        "phase": log_match.phase,
                        "suite": log_match.suite,
                        "log_source": log_match.log_source,
                        "match_type": log_match.match_type,
                        "matched_lines": log_match.matched_lines,
                        "error_lines": log_match.error_lines,
                        "response_echo_request_id": None,
                    }
                )
            row = {
                "phase": phase,
                "operation_id": endpoint.operation_id,
                "module": endpoint.module,
                "method": endpoint.method,
                "path": endpoint.path,
                "scenario_name": (fixture or {}).get("scenario_name", "auto_contract_probe"),
                "expected_statuses": expected_statuses,
                "result_class": "fail_transport",
                "duration_ms": duration_ms,
                "request": {**request_meta, "request_id": request_id},
                "error": str(exc),
                "log_evidence": log_match.match_type if log_match else "not_collected",
                "log_error_lines": (log_match.error_lines if log_match else []),
                "gate_class": classify_gate("fail_transport", (log_match.match_type if log_match else "strong")),
            }

        probe_results.append(row)
        executed_unique.add((endpoint.method, endpoint.path))
        if args.stop_on_first_failure and str(row["result_class"]).startswith("fail_"):
            break

    summary_counts = _new_summary_bucket()
    gate_summary = {"pass": 0, "fail_5xx": 0, "fail_transport": 0, "fail_log_evidence_missing": 0, "warn_log_evidence_weak": 0}
    for row in probe_results:
        rc = row["result_class"]
        summary_counts[rc] = summary_counts.get(rc, 0) + 1
        gc = row.get("gate_class", "pass")
        gate_summary[gc] = gate_summary.get(gc, 0) + 1
    failures = [r for r in probe_results if str(r["result_class"]).startswith("fail_")]
    reportable_failures = [
        r for r in probe_results if r.get("gate_class") in {"fail_5xx", "fail_transport", "fail_log_evidence_missing"}
    ]

    report = {
        "metadata": {
            "generated_at": isoformat_utc(utc_now()),
            "phase": phase,
            "base_url": args.base_url,
            "openapi_url": args.openapi_url,
            "fixtures": str(Path(args.fixtures)),
            "timeout_seconds": args.timeout,
            "with_log_correlation": bool(args.with_log_correlation),
        },
        "summary": {
            "openapi_total_endpoints": len(endpoints),
            "executed_unique_endpoints": len(executed_unique),
            "total_probes": len(probe_results),
            "total_429_retries": total_429_retries,
            **summary_counts,
            **{f"gate_{k}": v for k, v in gate_summary.items()},
        },
        "results": probe_results,
        "failures": failures,
        "failures_reportable": reportable_failures,
        "log_evidence": log_evidence_rows,
        "bootstrap_auth": boot,
        "context_keys": sorted(_flatten_keys(ctx.data)),
    }
    return report, seq


def _render_markdown_dual(report: dict[str, Any]) -> str:
    lines = ["# API E2E All Endpoints Report (Dual Mode)", ""]
    for phase_name, phase in (report.get("phases") or {}).items():
        s = phase["summary"]
        lines.extend(
            [
                f"## {phase_name}",
                "",
                f"- total_probes: `{s.get('total_probes', 0)}`",
                f"- pass_success: `{s.get('pass_success', 0)}`",
                f"- blocked_by_env_expected: `{s.get('blocked_by_env_expected', 0)}`",
                f"- fail_server_5xx: `{s.get('fail_server_5xx', 0)}`",
                f"- fail_transport: `{s.get('fail_transport', 0)}`",
                f"- gate_fail_log_evidence_missing: `{s.get('gate_fail_log_evidence_missing', 0)}`",
                "",
            ]
        )
    lines.append("## Failures Reportable")
    rows = report.get("failures_reportable", [])
    if not rows:
        lines.append("- None")
    else:
        for row in rows[:250]:
            lines.append(
                f"- `{row.get('phase')} {row['method']} {row['path']}` -> "
                f"`{row.get('actual_status', 'transport')}` [{row.get('gate_class')}]"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one runtime probe for every /api/v1 endpoint in OpenAPI.")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--openapi-url", default="http://localhost:8000/openapi.json")
    ap.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    ap.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    ap.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    ap.add_argument("--failures-json", default=str(DEFAULT_FAILURES_JSON))
    ap.add_argument("--openapi-snapshot", default=str(DEFAULT_OPENAPI_SNAPSHOT))
    ap.add_argument("--dual-output-dir", default=str(DEFAULT_DUAL_OUTPUT_DIR))
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--stop-on-first-failure", action="store_true")
    ap.add_argument("--seed-user-id", default="seed-admin")
    ap.add_argument("--limit", type=int, default=0, help="Debug: limit number of probes (0 = all)")
    ap.add_argument("--max-429-retries", type=int, default=4)
    ap.add_argument(
        "--min-interval-ms",
        type=float,
        default=1500.0,
        help="Minimum gap between requests in milliseconds (safe default for 60 req/min per-IP limiter with background traffic).",
    )
    ap.add_argument("--progress-every", type=int, default=25)
    ap.add_argument("--fail-on-429", action="store_true", help="Return non-zero if any request required a 429 retry.")
    ap.add_argument("--auth-mode", choices=["none", "bootstrap", "dual"], default="dual")
    ap.add_argument("--with-log-correlation", action="store_true")
    ap.add_argument("--log-service", default="janus-api")
    ap.add_argument("--log-container", default="janus_api")
    ap.add_argument("--log-evidence-required", action="store_true", default=False)
    ap.add_argument("--gate-mode", choices=["server5xx_or_logs"], default="server5xx_or_logs")
    ap.add_argument("--request-id-prefix", default="qa-api")
    ap.add_argument("--serial", action="store_true", default=True)
    ap.add_argument("--grace-log-ms", type=int, default=400)
    ap.add_argument("--log-since-padding-sec", type=int, default=1)
    ap.add_argument("--client-version", default="2.1.0")
    args = ap.parse_args()

    # Keep snapshot behavior
    try:
        openapi = fetch_openapi(args.openapi_url, args.timeout)
        save_json(Path(args.openapi_snapshot), openapi)
    except Exception as exc:
        print(f"[openapi] failed to fetch snapshot: {exc}", flush=True)
        return 1

    reports_by_phase: dict[str, Any] = {}
    seq = 0
    boot = None

    if args.auth_mode in {"none", "dual"}:
        phase_report, seq = _run_phase(args, phase="unauth", boot=None, request_id_seq_start=seq)
        reports_by_phase["unauth"] = phase_report

    if args.auth_mode in {"bootstrap", "dual"}:
        boot = bootstrap_local_auth(
            base_url=args.base_url,
            timeout=min(args.timeout, 20.0),
            request_id_prefix=f"{args.request_id_prefix}-bootstrap",
        )
        if args.auth_mode == "bootstrap":
            phase_report, seq = _run_phase(args, phase="auth", boot=boot, request_id_seq_start=seq)
            reports_by_phase["auth"] = phase_report
        else:
            if boot.get("ok"):
                phase_report, seq = _run_phase(args, phase="auth", boot=boot, request_id_seq_start=seq)
            else:
                phase_report = {
                    "metadata": {"generated_at": isoformat_utc(utc_now()), "phase": "auth", "base_url": args.base_url},
                    "summary": {"openapi_total_endpoints": 0, "executed_unique_endpoints": 0, "total_probes": 0, **_new_summary_bucket()},
                    "results": [],
                    "failures": [],
                    "failures_reportable": [],
                    "log_evidence": [],
                    "bootstrap_auth": boot,
                    "status": "blocked_bootstrap_auth",
                }
            reports_by_phase["auth"] = phase_report

    if len(reports_by_phase) == 1:
        phase_name = next(iter(reports_by_phase))
        report = reports_by_phase[phase_name]
        save_json(Path(args.report_json), report)
        save_json(Path(args.failures_json), report.get("failures_reportable") or report.get("failures") or [])
        Path(args.report_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_md).write_text(render_markdown(report))
        dual_dir = Path(args.dual_output_dir)
        dual_dir.mkdir(parents=True, exist_ok=True)
        save_json_shared(dual_dir / f"{phase_name}.json", report)
        if report.get("failures_reportable"):
            return 1
        if args.fail_on_429 and report.get("summary", {}).get("total_429_retries", 0) > 0:
            return 2
        return 0

    merged_results: list[dict[str, Any]] = []
    merged_failures: list[dict[str, Any]] = []
    merged_reportable: list[dict[str, Any]] = []
    merged_logs: list[dict[str, Any]] = []
    combined_summary = {"openapi_total_endpoints": 0, "executed_unique_endpoints": 0, "total_probes": 0, "total_429_retries": 0, **_new_summary_bucket()}
    for phase_name, phase_report in reports_by_phase.items():
        s = phase_report.get("summary", {})
        for k, v in s.items():
            if isinstance(v, int):
                combined_summary[k] = combined_summary.get(k, 0) + v
        combined_summary["openapi_total_endpoints"] = max(combined_summary.get("openapi_total_endpoints", 0), s.get("openapi_total_endpoints", 0))
        combined_summary["executed_unique_endpoints"] = max(combined_summary.get("executed_unique_endpoints", 0), s.get("executed_unique_endpoints", 0))
        merged_results.extend(phase_report.get("results", []))
        merged_failures.extend(phase_report.get("failures", []))
        merged_reportable.extend(phase_report.get("failures_reportable", []))
        merged_logs.extend(phase_report.get("log_evidence", []))

    final_report = {
        "metadata": {
            "generated_at": isoformat_utc(utc_now()),
            "base_url": args.base_url,
            "openapi_url": args.openapi_url,
            "fixtures": str(Path(args.fixtures)),
            "auth_mode": args.auth_mode,
            "with_log_correlation": bool(args.with_log_correlation),
        },
        "summary": combined_summary,
        "phases": reports_by_phase,
        "results": merged_results,
        "failures": merged_failures,
        "failures_reportable": merged_reportable,
        "log_evidence": merged_logs,
        "bootstrap_auth": boot,
    }

    dual_dir = Path(args.dual_output_dir)
    dual_dir.mkdir(parents=True, exist_ok=True)
    for phase_name, phase_report in reports_by_phase.items():
        save_json_shared(dual_dir / f"{phase_name}.json", phase_report)
    save_json(Path(args.report_json), final_report)
    save_json(Path(args.failures_json), merged_reportable)
    Path(args.report_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_md).write_text(_render_markdown_dual(final_report))

    s = final_report["summary"]
    print(
        "[summary:dual] probes={total_probes} success={pass_success} blocked_env={blocked_by_env_expected} "
        "server5xx={fail_server_5xx} transport={fail_transport} gate_log_missing={gate_fail_log_evidence_missing}".format(**s)
    )
    if merged_reportable:
        return 1
    if args.fail_on_429 and s.get("total_429_retries", 0) > 0:
        return 2
    return 0


def _flatten_keys(obj: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            keys.append(p)
            keys.extend(_flatten_keys(v, p))
    return keys


if __name__ == "__main__":
    raise SystemExit(main())
