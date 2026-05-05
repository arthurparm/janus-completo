#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from qa_request_support import (
    DockerLogCorrelator,
    bootstrap_local_auth,
    classify_gate,
    classify_http_status,
    generate_request_id,
    isoformat_utc,
    sanitize_headers,
    save_json,
    utc_now,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPRINT_DIR = ROOT / "backend" / "http" / "sprint"
DEFAULT_REPORT_JSON = ROOT / "outputs" / "qa" / "sprint_http_runs" / "all_sprints_report.json"
DEFAULT_REPORT_DIR = ROOT / "outputs" / "qa" / "sprint_http_runs"

METHOD_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(.+)$", re.IGNORECASE)
VAR_RE = re.compile(r"^@([A-Za-z0-9_]+)\s*=\s*(.*)$")
TPL_RE = re.compile(r"\{\{([^}]+)\}\}")
STATUS_EQ_RE = re.compile(r"response\.status\s*===\s*(\d+)")
STATUS_ARRAY_RE = re.compile(r"\[([0-9,\s]+)\]\.includes\(response\.status\)")
SET_CALL_RE = re.compile(r'client\.global\.set\("([^"]+)"\s*,\s*([^)][^;]*?)\s*\);')
SET_CALL_INLINE_RE = re.compile(r'client\.global\.set\("([^"]+)"\s*,\s*(.+?)\s*\);')


@dataclass
class HttpRequestDef:
    name: str
    method: str
    url: str
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: str = ""
    script: str = ""
    file_path: str = ""
    line_no: int = 0


def interpolate(text: str, vars_map: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        if key == "$timestamp":
            return str(int(time.time()))
        return str(vars_map.get(key, ""))

    return TPL_RE.sub(repl, text)


def parse_http_file(path: Path) -> tuple[dict[str, str], list[HttpRequestDef]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    variables: dict[str, str] = {}
    requests_out: list[HttpRequestDef] = []
    pending_name: str | None = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        mvar = VAR_RE.match(s)
        if mvar:
            variables[mvar.group(1)] = mvar.group(2).strip()
            i += 1
            continue
        if s.startswith("# @name "):
            pending_name = s.split("# @name ", 1)[1].strip()
            i += 1
            continue
        if not s or s.startswith("#") or s == "###":
            i += 1
            continue
        mm = METHOD_RE.match(s)
        if not mm:
            i += 1
            continue

        method = mm.group(1).upper()
        url = mm.group(2).strip()
        headers: list[tuple[str, str]] = []
        body_lines: list[str] = []
        script_lines: list[str] = []
        line_no = i + 1
        i += 1

        # Headers
        while i < len(lines):
            cur = lines[i]
            cur_s = cur.strip()
            if cur_s == "":
                i += 1
                break
            if cur_s.startswith("#") or cur_s == "###":
                break
            if cur_s.startswith("> {%"):
                break
            if METHOD_RE.match(cur_s):
                break
            if ":" in cur:
                k, v = cur.split(":", 1)
                headers.append((k.strip(), v.strip()))
                i += 1
                continue
            break

        # Body + script until next separator/request
        while i < len(lines):
            cur = lines[i]
            cur_s = cur.strip()
            if cur_s == "###":
                break
            if METHOD_RE.match(cur_s):
                break
            if cur_s.startswith("# @name "):
                break
            if cur_s.startswith("> {%"):
                # capture JS block (single or multi-line)
                script_lines.append(cur)
                if "%}" not in cur_s:
                    i += 1
                    while i < len(lines):
                        script_lines.append(lines[i])
                        if "%}" in lines[i]:
                            break
                        i += 1
                i += 1
                continue
            if cur_s.startswith("#"):
                i += 1
                continue
            body_lines.append(cur)
            i += 1

        name = pending_name or f"{path.stem}_{len(requests_out)+1}"
        pending_name = None
        requests_out.append(
            HttpRequestDef(
                name=name,
                method=method,
                url=url,
                headers=headers,
                body="\n".join(body_lines).strip("\n"),
                script="\n".join(script_lines),
                file_path=str(path),
                line_no=line_no,
            )
        )
    return variables, requests_out


def expected_statuses_from_script(script: str) -> list[int]:
    if not script:
        return []
    vals: set[int] = set()
    for m in STATUS_EQ_RE.finditer(script):
        vals.add(int(m.group(1)))
    for m in STATUS_ARRAY_RE.finditer(script):
        for part in m.group(1).split(","):
            part = part.strip()
            if part.isdigit():
                vals.add(int(part))
    return sorted(vals)


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


def _eval_assign_expr(expr: str, payload: Any, status_code: int) -> str | None:
    e = expr.strip()
    while e.startswith("String(") and e.endswith(")"):
        e = e[len("String(") : -1].strip()
    if e == "response.status":
        return str(status_code)
    if (e.startswith('"') and e.endswith('"')) or (e.startswith("'") and e.endswith("'")):
        return e[1:-1]
    if re.fullmatch(r"-?\d+", e):
        return e
    if e.startswith("b."):
        v = extract_json_path(payload, e[2:])
        return None if v is None else str(v)
    if e.startswith("body."):
        v = extract_json_path(payload, e[5:])
        return None if v is None else str(v)
    return None


def apply_script_assignments(script: str, payload: Any, status_code: int, vars_map: dict[str, str]) -> None:
    if not script or payload is None:
        return
    for regex in (SET_CALL_RE, SET_CALL_INLINE_RE):
        for m in regex.finditer(script):
            key = m.group(1)
            expr = m.group(2)
            val = _eval_assign_expr(expr, payload, status_code)
            if val is not None:
                vars_map[key] = val


def summarize_response(resp: requests.Response) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status_code": resp.status_code,
        "content_type": resp.headers.get("content-type"),
        "content_length": len(resp.content or b""),
    }
    try:
        body = resp.json()
        if isinstance(body, dict):
            out["json_keys"] = list(body.keys())[:20]
        elif isinstance(body, list):
            out["json_items"] = len(body)
    except Exception:
        text = (resp.text or "")[:240]
        if text:
            out["text_snippet"] = text
    return out


def execute_request(
    req: HttpRequestDef,
    *,
    session: requests.Session,
    vars_map: dict[str, str],
    phase: str,
    seq: int,
    timeout: float,
    request_id_prefix: str,
    correlator: DockerLogCorrelator | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    request_id = generate_request_id(request_id_prefix, phase, "sprint", seq)
    resolved_url = interpolate(req.url, vars_map)
    header_map: dict[str, str] = {}
    for k, v in req.headers:
        header_map[k] = interpolate(v, vars_map)
    header_map["X-Request-ID"] = request_id
    header_map.setdefault("User-Agent", "Janus-Sprint-HTTP-E2E/1.0")
    if phase == "unauth" or not (header_map.get("Authorization") or "").strip().replace("Bearer", "").strip():
        header_map.pop("Authorization", None)

    body_text = interpolate(req.body, vars_map) if req.body else ""
    req_kwargs: dict[str, Any] = {"headers": header_map, "timeout": timeout}
    ct = (header_map.get("Content-Type") or header_map.get("content-type") or "").lower()
    if body_text:
        if "application/json" in ct:
            try:
                req_kwargs["json"] = json.loads(body_text)
            except Exception:
                req_kwargs["data"] = body_text.encode("utf-8")
        else:
            req_kwargs["data"] = body_text.encode("utf-8")

    t0 = utc_now()
    started = time.perf_counter()
    response_echo_request_id = None
    payload = None
    try:
        resp = session.request(req.method, resolved_url, **req_kwargs)
        duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
        response_echo_request_id = resp.headers.get("X-Request-ID")
        try:
            payload = resp.json()
        except Exception:
            payload = None
        expected_statuses = expected_statuses_from_script(req.script)
        parsed = urlparse(resolved_url)
        http_class = classify_http_status(
            resp.status_code,
            expected_statuses or [200, 201, 202, 204, 400, 401, 403, 404, 409, 422],
            phase=phase,
            path=parsed.path,
            notes=req.name,
        )
        apply_script_assignments(req.script, payload, resp.status_code, vars_map)
        if isinstance(payload, dict):
            # Heuristicas pequenas para encadeamento entre requests
            if "conversation_id" in payload:
                vars_map.setdefault("conversation_id", str(payload["conversation_id"]))
            if "doc_id" in payload:
                vars_map.setdefault("doc_id", str(payload["doc_id"]))
            if "id" in payload and "request" in req.name:
                vars_map.setdefault("request_id", str(payload["id"]))

        log_match = None
        if correlator:
            log_match = correlator.correlate(
                request_id=request_id,
                method=req.method,
                path=parsed.path,
                phase=phase,
                suite="sprint",
                t0=t0,
                response_echo_request_id=response_echo_request_id,
            )
        log_evidence = log_match.match_type if log_match else "not_collected"
        row = {
            "phase": phase,
            "sprint": Path(req.file_path).name,
            "request_name": req.name,
            "method": req.method,
            "url": resolved_url,
            "request_id": request_id,
            "http_status": resp.status_code,
            "duration_ms": duration_ms,
            "assert_expected_statuses": expected_statuses,
            "http_class": http_class,
            "log_evidence": log_evidence,
            "log_error_lines": (log_match.error_lines if log_match else []),
            "gate_class": classify_gate(http_class, log_evidence if correlator else "strong"),
            "response_echo_request_id": response_echo_request_id,
            "response_summary": summarize_response(resp),
            "file_path": req.file_path,
            "line_no": req.line_no,
            "request_headers": sanitize_headers(header_map),
        }
        if resp.status_code >= 500 and payload is not None:
            row["response_body_sample"] = payload if isinstance(payload, (dict, list)) else str(payload)
        evidence_row = None
        if log_match:
            evidence_row = {
                "request_id": log_match.request_id,
                "phase": log_match.phase,
                "suite": log_match.suite,
                "log_source": log_match.log_source,
                "match_type": log_match.match_type,
                "matched_lines": log_match.matched_lines,
                "error_lines": log_match.error_lines,
                "response_echo_request_id": log_match.response_echo_request_id,
            }
        return row, evidence_row
    except requests.RequestException as exc:
        duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
        parsed = urlparse(resolved_url)
        log_match = None
        if correlator:
            log_match = correlator.correlate(
                request_id=request_id,
                method=req.method,
                path=parsed.path,
                phase=phase,
                suite="sprint",
                t0=t0,
                response_echo_request_id=None,
            )
        log_evidence = log_match.match_type if log_match else "not_collected"
        row = {
            "phase": phase,
            "sprint": Path(req.file_path).name,
            "request_name": req.name,
            "method": req.method,
            "url": resolved_url,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "http_class": "fail_transport",
            "gate_class": classify_gate("fail_transport", log_evidence if correlator else "strong"),
            "log_evidence": log_evidence,
            "log_error_lines": (log_match.error_lines if log_match else []),
            "error": str(exc),
            "file_path": req.file_path,
            "line_no": req.line_no,
            "request_headers": sanitize_headers(header_map),
        }
        evidence_row = None
        if log_match:
            evidence_row = {
                "request_id": log_match.request_id,
                "phase": log_match.phase,
                "suite": log_match.suite,
                "log_source": log_match.log_source,
                "match_type": log_match.match_type,
                "matched_lines": log_match.matched_lines,
                "error_lines": log_match.error_lines,
            }
        return row, evidence_row


def _redact_bootstrap_auth(boot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(boot, dict):
        return boot
    redacted = dict(boot)
    for key in ("password", "token", "access_token", "refresh_token"):
        if key in redacted and redacted[key]:
            redacted[key] = "***REDACTED***"
    return redacted


def main() -> int:
    ap = argparse.ArgumentParser(description="Execute active requests from backend/http/sprint/*.http with log correlation.")
    ap.add_argument("--sprint-dir", default=str(DEFAULT_SPRINT_DIR))
    ap.add_argument("--glob", default="Sprint *.http")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--phase", choices=["unauth", "auth"], required=True)
    ap.add_argument("--token", default="")
    ap.add_argument("--user-id", default="")
    ap.add_argument("--bootstrap-auth", action="store_true")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--request-id-prefix", default="qa-sprint")
    ap.add_argument("--with-log-correlation", action="store_true")
    ap.add_argument("--log-service", default="janus-api")
    ap.add_argument("--log-container", default="janus_api")
    ap.add_argument("--grace-log-ms", type=int, default=400)
    ap.add_argument("--log-since-padding-sec", type=int, default=1)
    ap.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    ap.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    ap.add_argument("--limit-requests", type=int, default=0)
    args = ap.parse_args()

    sprint_dir = Path(args.sprint_dir)
    sprint_files = sorted(sprint_dir.glob(args.glob), key=lambda p: p.name)
    if not sprint_files:
        print(f"[error] no sprint files found in {sprint_dir} with pattern {args.glob}", flush=True)
        return 1

    boot = None
    token = args.token.strip()
    user_id = args.user_id.strip()
    if args.phase == "auth" and not token and args.bootstrap_auth:
        boot = bootstrap_local_auth(base_url=args.base_url, timeout=min(args.timeout, 20.0), request_id_prefix=f"{args.request_id_prefix}-bootstrap")
        if boot.get("ok"):
            token = str(boot.get("token") or "")
            user_id = str(boot.get("user_id") or "")
        else:
            print(f"[warn] auth bootstrap failed: {_redact_bootstrap_auth(boot)}", flush=True)

    correlator = None
    if args.with_log_correlation:
        correlator = DockerLogCorrelator(
            service=args.log_service,
            container=args.log_container,
            grace_log_ms=args.grace_log_ms,
            since_padding_sec=args.log_since_padding_sec,
            include_weak_fallback=True,
        )

    session = requests.Session()
    all_rows: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []
    per_sprint_reports: dict[str, Any] = {}
    seq = 0

    for sprint_file in sprint_files:
        base_vars, requests_list = parse_http_file(sprint_file)
        vars_map = dict(base_vars)
        vars_map["host"] = args.base_url
        if "/api/v1" not in vars_map.get("api_v1_prefix", ""):
            vars_map.setdefault("api_v1_prefix", "/api/v1")
        if token:
            vars_map["token"] = token
        elif args.phase == "unauth":
            vars_map["token"] = ""
        if user_id:
            vars_map["actor_user_id"] = user_id
            vars_map["user_id_int"] = user_id
            vars_map["user_id_str"] = user_id
        if args.limit_requests > 0:
            requests_list = requests_list[: args.limit_requests]

        sprint_rows: list[dict[str, Any]] = []
        sprint_log_rows: list[dict[str, Any]] = []
        print(f"[{args.phase}] sprint={sprint_file.name} requests={len(requests_list)}", flush=True)
        for req in requests_list:
            seq += 1
            row, evidence = execute_request(
                req,
                session=session,
                vars_map=vars_map,
                phase=args.phase,
                seq=seq,
                timeout=args.timeout,
                request_id_prefix=args.request_id_prefix,
                correlator=correlator,
            )
            sprint_rows.append(row)
            all_rows.append(row)
            if evidence:
                sprint_log_rows.append(evidence)
                log_rows.append(evidence)

        sprint_summary = {
            "total_requests": len(sprint_rows),
            "pass": sum(1 for r in sprint_rows if r["gate_class"] == "pass"),
            "warn_log_evidence_weak": sum(1 for r in sprint_rows if r["gate_class"] == "warn_log_evidence_weak"),
            "fail_5xx": sum(1 for r in sprint_rows if r["gate_class"] == "fail_5xx"),
            "fail_transport": sum(1 for r in sprint_rows if r["gate_class"] == "fail_transport"),
            "fail_log_evidence_missing": sum(1 for r in sprint_rows if r["gate_class"] == "fail_log_evidence_missing"),
            "blocked_by_env_expected": sum(1 for r in sprint_rows if r["http_class"] == "blocked_by_env_expected"),
        }
        sprint_report = {
            "metadata": {
                "generated_at": isoformat_utc(utc_now()),
                "phase": args.phase,
                "sprint": sprint_file.name,
                "file": str(sprint_file),
            },
            "summary": sprint_summary,
            "results": sprint_rows,
            "log_evidence": sprint_log_rows,
            "bootstrap_auth": boot if args.phase == "auth" else None,
        }
        per_sprint_reports[sprint_file.name] = sprint_report
        save_json(Path(args.report_dir) / f"{sprint_file.stem}.{args.phase}.json", sprint_report)

    failures_reportable = [
        r for r in all_rows if r["gate_class"] in {"fail_5xx", "fail_transport", "fail_log_evidence_missing"}
    ]
    aggregate = {
        "metadata": {
            "generated_at": isoformat_utc(utc_now()),
            "phase": args.phase,
            "sprint_dir": str(sprint_dir),
            "glob": args.glob,
            "base_url": args.base_url,
            "with_log_correlation": bool(args.with_log_correlation),
        },
        "summary": {
            "total_sprints": len(sprint_files),
            "total_requests": len(all_rows),
            "pass": sum(1 for r in all_rows if r["gate_class"] == "pass"),
            "warn_log_evidence_weak": sum(1 for r in all_rows if r["gate_class"] == "warn_log_evidence_weak"),
            "fail_5xx": sum(1 for r in all_rows if r["gate_class"] == "fail_5xx"),
            "fail_transport": sum(1 for r in all_rows if r["gate_class"] == "fail_transport"),
            "fail_log_evidence_missing": sum(1 for r in all_rows if r["gate_class"] == "fail_log_evidence_missing"),
            "blocked_by_env_expected": sum(1 for r in all_rows if r["http_class"] == "blocked_by_env_expected"),
        },
        "results": all_rows,
        "failures_reportable": failures_reportable,
        "log_evidence": log_rows,
        "sprints": per_sprint_reports,
        "bootstrap_auth": _redact_bootstrap_auth(boot),
        "status": "blocked_bootstrap_auth" if (args.phase == "auth" and args.bootstrap_auth and (boot and not boot.get("ok"))) else "ok",
    }
    save_json(args.report_json, aggregate)
    print(f"[summary:{args.phase}] requests={len(all_rows)} failures_reportable={len(failures_reportable)}", flush=True)
    return 1 if failures_reportable else 0


if __name__ == "__main__":
    raise SystemExit(main())

