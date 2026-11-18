#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests

from qa_request_support import isoformat_utc, save_json, utc_now


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "qa"


def run_cmd(cmd: list[str]) -> dict[str, Any]:
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def load_json_if_exists(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        return {"_parse_error": str(exc), "_path": str(path)}


def health_probe(url: str, timeout: float) -> dict[str, Any]:
    try:
        r = requests.get(url, timeout=timeout)
        sample = None
        try:
            sample = r.json()
        except Exception:
            sample = (r.text or "")[:400]
        return {"ok": 200 <= r.status_code < 400, "status_code": r.status_code, "body_sample": sample}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def render_md(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Full Process Validation Report",
        "",
        "## Resumo Geral",
        "",
        f"- gerado_em: `{report['metadata']['generated_at']}`",
        f"- base_url: `{report['metadata']['base_url']}`",
        f"- api_probes_total: `{s.get('api_total_probes', 0)}`",
        f"- sprint_requests_total: `{s.get('sprint_total_requests', 0)}`",
        f"- failures_reportable: `{s.get('failures_reportable_total', 0)}`",
        f"- blocked_by_env_expected: `{s.get('blocked_by_env_total', 0)}`",
        f"- log_missing: `{s.get('log_missing_total', 0)}`",
        "",
        "## Falhas Reportáveis (5xx/transport/logs)",
        "",
    ]
    failures = report.get("failures_reportable", [])
    if not failures:
        lines.append("- None")
    else:
        for row in failures[:300]:
            lines.append(
                f"- `{row.get('suite','?')} {row.get('phase','?')} {row.get('method','?')} {row.get('path') or row.get('url','?')}` "
                f"-> `{row.get('actual_status', row.get('http_status','transport'))}` [{row.get('gate_class')}]"
            )

    lines.extend(["", "## Bloqueios de Ambiente (esperado)", ""])
    blocked = report.get("blocked_by_env", [])
    if not blocked:
        lines.append("- None")
    else:
        for row in blocked[:200]:
            lines.append(
                f"- `{row.get('suite','?')} {row.get('phase','?')} {row.get('method','?')} {row.get('path') or row.get('url','?')}` "
                f"-> `{row.get('actual_status', row.get('http_status'))}` [{row.get('http_class') or row.get('result_class')}]"
            )

    lines.extend(["", "## Evidência de Logs", ""])
    le = report.get("log_evidence_stats", {})
    lines.append(f"- strong: `{le.get('strong', 0)}`")
    lines.append(f"- weak: `{le.get('weak', 0)}`")
    lines.append(f"- missing: `{le.get('missing', 0)}`")
    lines.append(f"- total: `{le.get('total', 0)}`")

    lines.extend(["", "## Recomendações", ""])
    if failures:
        lines.append("- Priorizar correção dos `fail_5xx` e `fail_transport` antes de endurecer asserts funcionais.")
        lines.append("- Investigar middleware/logging quando houver `fail_log_evidence_missing` com HTTP 2xx/4xx.")
    else:
        lines.append("- Nenhuma falha reportável pelo gate atual (5xx/transport/logs).")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run full Janus process validation (API + Sprint HTTP) with Docker log correlation.")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--report-json", default=str(OUT_DIR / "full_process_validation_report.json"))
    ap.add_argument("--report-md", default=str(OUT_DIR / "full_process_validation_report.md"))
    ap.add_argument("--failures-json", default=str(OUT_DIR / "full_process_validation_failures.json"))
    ap.add_argument("--log-evidence-json", default=str(OUT_DIR / "full_process_validation_log_evidence.json"))
    ap.add_argument("--log-service", default="janus-api")
    ap.add_argument("--log-container", default="janus_api")
    ap.add_argument("--grace-log-ms", type=int, default=400)
    ap.add_argument("--log-since-padding-sec", type=int, default=1)
    ap.add_argument("--api-min-interval-ms", type=float, default=1500.0)
    ap.add_argument("--api-limit", type=int, default=0)
    ap.add_argument("--sprint-limit-requests", type=int, default=0)
    args = ap.parse_args()

    out_dir = Path(args.report_json).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    api_out_dir = OUT_DIR / "api_e2e_dual_mode"
    sprint_out_dir = OUT_DIR / "sprint_http_runs"
    api_out_dir.mkdir(parents=True, exist_ok=True)
    sprint_out_dir.mkdir(parents=True, exist_ok=True)

    docker_ps = run_cmd(["docker", "compose", "ps"])
    health = {
        "/health": health_probe(args.base_url.rstrip("/") + "/health", timeout=args.timeout),
        "/api/v1/system/status": health_probe(args.base_url.rstrip("/") + "/api/v1/system/status", timeout=args.timeout),
    }

    py = sys.executable
    step_results: dict[str, Any] = {}

    api_unauth_json = api_out_dir / "unauth.json"
    api_unauth_md = api_out_dir / "unauth.md"
    api_unauth_fail = api_out_dir / "unauth.failures.json"
    cmd_api_unauth = [
        py,
        str(ROOT / "tooling" / "run_api_e2e_all.py"),
        "--base-url",
        args.base_url,
        "--auth-mode",
        "none",
        "--with-log-correlation",
        "--log-service",
        args.log_service,
        "--log-container",
        args.log_container,
        "--grace-log-ms",
        str(args.grace_log_ms),
        "--log-since-padding-sec",
        str(args.log_since_padding_sec),
        "--request-id-prefix",
        "qa-api",
        "--report-json",
        str(api_unauth_json),
        "--report-md",
        str(api_unauth_md),
        "--failures-json",
        str(api_unauth_fail),
        "--min-interval-ms",
        str(args.api_min_interval_ms),
    ]
    if args.api_limit > 0:
        cmd_api_unauth += ["--limit", str(args.api_limit)]
    step_results["api_unauth"] = run_cmd(cmd_api_unauth)

    sprint_unauth_json = sprint_out_dir / "all_sprints.unauth.json"
    cmd_sprint_unauth = [
        py,
        str(ROOT / "tooling" / "run_sprint_http_e2e.py"),
        "--phase",
        "unauth",
        "--base-url",
        args.base_url,
        "--with-log-correlation",
        "--log-service",
        args.log_service,
        "--log-container",
        args.log_container,
        "--grace-log-ms",
        str(args.grace_log_ms),
        "--log-since-padding-sec",
        str(args.log_since_padding_sec),
        "--request-id-prefix",
        "qa-sprint",
        "--report-json",
        str(sprint_unauth_json),
        "--report-dir",
        str(sprint_out_dir),
        "--timeout",
        str(args.timeout),
    ]
    if args.sprint_limit_requests > 0:
        cmd_sprint_unauth += ["--limit-requests", str(args.sprint_limit_requests)]
    step_results["sprint_unauth"] = run_cmd(cmd_sprint_unauth)

    api_auth_json = api_out_dir / "auth.json"
    api_auth_md = api_out_dir / "auth.md"
    api_auth_fail = api_out_dir / "auth.failures.json"
    cmd_api_auth = [
        py,
        str(ROOT / "tooling" / "run_api_e2e_all.py"),
        "--base-url",
        args.base_url,
        "--auth-mode",
        "bootstrap",
        "--with-log-correlation",
        "--log-service",
        args.log_service,
        "--log-container",
        args.log_container,
        "--grace-log-ms",
        str(args.grace_log_ms),
        "--log-since-padding-sec",
        str(args.log_since_padding_sec),
        "--request-id-prefix",
        "qa-api",
        "--report-json",
        str(api_auth_json),
        "--report-md",
        str(api_auth_md),
        "--failures-json",
        str(api_auth_fail),
        "--min-interval-ms",
        str(args.api_min_interval_ms),
    ]
    if args.api_limit > 0:
        cmd_api_auth += ["--limit", str(args.api_limit)]
    step_results["api_auth"] = run_cmd(cmd_api_auth)

    sprint_auth_json = sprint_out_dir / "all_sprints.auth.json"
    cmd_sprint_auth = [
        py,
        str(ROOT / "tooling" / "run_sprint_http_e2e.py"),
        "--phase",
        "auth",
        "--bootstrap-auth",
        "--base-url",
        args.base_url,
        "--with-log-correlation",
        "--log-service",
        args.log_service,
        "--log-container",
        args.log_container,
        "--grace-log-ms",
        str(args.grace_log_ms),
        "--log-since-padding-sec",
        str(args.log_since_padding_sec),
        "--request-id-prefix",
        "qa-sprint",
        "--report-json",
        str(sprint_auth_json),
        "--report-dir",
        str(sprint_out_dir),
        "--timeout",
        str(args.timeout),
    ]
    if args.sprint_limit_requests > 0:
        cmd_sprint_auth += ["--limit-requests", str(args.sprint_limit_requests)]
    step_results["sprint_auth"] = run_cmd(cmd_sprint_auth)

    api_unauth = load_json_if_exists(api_unauth_json) or {}
    api_auth = load_json_if_exists(api_auth_json) or {}
    sprint_unauth = load_json_if_exists(sprint_unauth_json) or {}
    sprint_auth = load_json_if_exists(sprint_auth_json) or {}

    def tag_suite(rows: list[dict[str, Any]], suite: str, phase: str, api: bool) -> list[dict[str, Any]]:
        out = []
        for row in rows or []:
            tagged = dict(row)
            tagged.setdefault("suite", suite)
            tagged.setdefault("phase", phase)
            if api:
                tagged.setdefault("actual_status", tagged.get("actual_status"))
            else:
                tagged.setdefault("http_status", tagged.get("http_status"))
            out.append(tagged)
        return out

    all_failures_reportable = []
    all_failures_reportable += tag_suite(api_unauth.get("failures_reportable", []), "api", "unauth", True)
    all_failures_reportable += tag_suite(api_auth.get("failures_reportable", []), "api", "auth", True)
    all_failures_reportable += tag_suite(sprint_unauth.get("failures_reportable", []), "sprint", "unauth", False)
    all_failures_reportable += tag_suite(sprint_auth.get("failures_reportable", []), "sprint", "auth", False)

    blocked_by_env = []
    blocked_by_env += tag_suite([r for r in api_unauth.get("results", []) if r.get("result_class") == "blocked_by_env_expected"], "api", "unauth", True)
    blocked_by_env += tag_suite([r for r in api_auth.get("results", []) if r.get("result_class") == "blocked_by_env_expected"], "api", "auth", True)
    blocked_by_env += tag_suite([r for r in sprint_unauth.get("results", []) if r.get("http_class") == "blocked_by_env_expected"], "sprint", "unauth", False)
    blocked_by_env += tag_suite([r for r in sprint_auth.get("results", []) if r.get("http_class") == "blocked_by_env_expected"], "sprint", "auth", False)

    log_evidence = []
    for payload, suite, phase in (
        (api_unauth, "api", "unauth"),
        (api_auth, "api", "auth"),
        (sprint_unauth, "sprint", "unauth"),
        (sprint_auth, "sprint", "auth"),
    ):
        for row in payload.get("log_evidence", []) or []:
            tagged = dict(row)
            tagged.setdefault("suite", suite)
            tagged.setdefault("phase", phase)
            log_evidence.append(tagged)

    log_evidence_stats = {
        "strong": sum(1 for r in log_evidence if r.get("match_type") == "strong"),
        "weak": sum(1 for r in log_evidence if r.get("match_type") == "weak"),
        "missing": sum(1 for r in log_evidence if r.get("match_type") == "missing"),
        "total": len(log_evidence),
    }

    report = {
        "metadata": {
            "generated_at": isoformat_utc(utc_now()),
            "base_url": args.base_url,
            "gate_mode": "server5xx_or_logs",
        },
        "environment": {
            "python": sys.executable,
        },
        "docker_status": {
            "compose_ps": docker_ps,
            "health": health,
        },
        "phases": {
            "unauth": {
                "api": api_unauth,
                "sprints": sprint_unauth,
            },
            "auth": {
                "api": api_auth,
                "sprints": sprint_auth,
            },
        },
        "step_results": step_results,
        "summary": {
            "api_total_probes": (api_unauth.get("summary", {}).get("total_probes", 0) + api_auth.get("summary", {}).get("total_probes", 0)),
            "sprint_total_requests": (sprint_unauth.get("summary", {}).get("total_requests", 0) + sprint_auth.get("summary", {}).get("total_requests", 0)),
            "failures_reportable_total": len(all_failures_reportable),
            "blocked_by_env_total": len(blocked_by_env),
            "log_missing_total": log_evidence_stats["missing"],
        },
        "api_results": {
            "unauth": api_unauth,
            "auth": api_auth,
        },
        "sprint_results": {
            "unauth": sprint_unauth,
            "auth": sprint_auth,
        },
        "failures_reportable": all_failures_reportable,
        "blocked_by_env": blocked_by_env,
        "log_evidence_stats": log_evidence_stats,
    }

    save_json(args.report_json, report)
    save_json(args.failures_json, all_failures_reportable)
    save_json(args.log_evidence_json, log_evidence)
    Path(args.report_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report_md).write_text(render_md(report), encoding="utf-8")

    print(
        f"[full-process] api_probes={report['summary']['api_total_probes']} "
        f"sprint_requests={report['summary']['sprint_total_requests']} "
        f"failures_reportable={report['summary']['failures_reportable_total']} "
        f"log_missing={report['summary']['log_missing_total']}",
        flush=True,
    )
    return 1 if all_failures_reportable else 0


if __name__ == "__main__":
    raise SystemExit(main())

