#!/usr/bin/env python3
"""
Generate OQ-011 API coverage report from the live endpoint matrix.

Inputs:
- documentation/qa/api-endpoint-matrix.json

Outputs:
- outputs/qa/api_coverage_report.json
- outputs/qa/api_coverage_report.md
- Optional Docker evidence files:
  - outputs/qa/docker_evidence.json
  - outputs/qa/janus_api_log_tail.txt
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX_JSON = ROOT / "documentation" / "qa" / "api-endpoint-matrix.json"
DEFAULT_REPORT_JSON = ROOT / "outputs" / "qa" / "api_coverage_report.json"
DEFAULT_REPORT_MD = ROOT / "outputs" / "qa" / "api_coverage_report.md"
DEFAULT_DOCKER_EVIDENCE_JSON = ROOT / "outputs" / "qa" / "docker_evidence.json"
DEFAULT_DOCKER_LOG_TAIL = ROOT / "outputs" / "qa" / "janus_api_log_tail.txt"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_path(path: str) -> str:
    value = (path or "").strip()
    if not value:
        return value
    if value.startswith("/api/v1/"):
        return value
    if value.startswith("/"):
        return "/api/v1" + value
    return "/api/v1/" + value


def endpoint_status(endpoint: dict[str, Any]) -> str:
    smoke = endpoint.get("smoke_success")
    in_tests = bool(endpoint.get("referenced_in_tests"))

    if smoke is True:
        return "runtime_validated"
    if smoke is False:
        return "runtime_failed"
    if in_tests:
        return "test_referenced"
    return "not_covered"


def parse_docker_ps_output(raw: str) -> list[dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except Exception:
        pass

    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def load_matrix(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Endpoint matrix not found: {path}. Run `python tooling/generate_api_matrix.py` first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, list):
        raise ValueError(f"Invalid matrix format in {path}: expected `endpoints` list.")
    return payload


def build_coverage_report(matrix: dict[str, Any], expected_endpoints: int) -> dict[str, Any]:
    metadata = matrix.get("metadata") or {}
    endpoints = matrix.get("endpoints") or []

    module_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "covered": 0,
            "not_covered": 0,
            "runtime_validated": 0,
            "runtime_failed": 0,
            "test_referenced": 0,
        }
    )

    normalized_rows: list[dict[str, Any]] = []
    total = 0
    covered = 0
    runtime_validated = 0
    runtime_failed = 0
    test_referenced = 0

    for endpoint in sorted(
        endpoints,
        key=lambda item: (
            str(item.get("module") or "unknown").lower(),
            normalize_path(str(item.get("path") or "")),
            str(item.get("method") or "").upper(),
        ),
    ):
        method = str(endpoint.get("method") or "").upper()
        path = normalize_path(str(endpoint.get("path") or ""))
        module = str(endpoint.get("module") or "unknown")
        status = endpoint_status(endpoint)
        is_covered = status != "not_covered"

        row = {
            "method": method,
            "path": path,
            "module": module,
            "operation_id": endpoint.get("operation_id") or "",
            "summary": endpoint.get("summary") or "",
            "coverage_status": status,
            "covered": is_covered,
            "referenced_in_tests": bool(endpoint.get("referenced_in_tests")),
            "smoke_success": endpoint.get("smoke_success"),
            "smoke_status_code": endpoint.get("smoke_status_code"),
            "smoke_error": endpoint.get("smoke_error"),
        }
        normalized_rows.append(row)

        total += 1
        module_stats[module]["total"] += 1

        if is_covered:
            covered += 1
            module_stats[module]["covered"] += 1
        else:
            module_stats[module]["not_covered"] += 1

        if status == "runtime_validated":
            runtime_validated += 1
            module_stats[module]["runtime_validated"] += 1
        elif status == "runtime_failed":
            runtime_failed += 1
            module_stats[module]["runtime_failed"] += 1
        elif status == "test_referenced":
            test_referenced += 1
            module_stats[module]["test_referenced"] += 1

    uncovered = [row for row in normalized_rows if not row["covered"]]
    runtime_failures = [row for row in normalized_rows if row["coverage_status"] == "runtime_failed"]
    coverage_percent = round((covered / total) * 100.0, 2) if total else 0.0

    expected = max(0, int(expected_endpoints))
    gap = max(0, expected - total)

    module_rows: list[dict[str, Any]] = []
    for module, stats in sorted(module_stats.items(), key=lambda item: item[0].lower()):
        module_total = stats["total"]
        module_cov = stats["covered"]
        module_rows.append(
            {
                "module": module,
                **stats,
                "coverage_percent": round((module_cov / module_total) * 100.0, 2) if module_total else 0.0,
            }
        )

    return {
        "metadata": {
            "generated_at": now_iso(),
            "source_matrix_generated_at": metadata.get("generated_at"),
            "source_matrix_mode": metadata.get("source"),
            "issue_id": "OQ-011",
        },
        "target": {
            "expected_endpoints": expected,
            "observed_endpoints": total,
            "target_met": total >= expected if expected > 0 else True,
            "endpoint_gap": gap,
        },
        "summary": {
            "total_endpoints": total,
            "covered_endpoints": covered,
            "uncovered_endpoints": len(uncovered),
            "coverage_percent": coverage_percent,
            "runtime_validated_endpoints": runtime_validated,
            "runtime_failed_endpoints": runtime_failed,
            "test_referenced_endpoints": test_referenced,
        },
        "by_module": module_rows,
        "uncovered_endpoints": uncovered,
        "runtime_failed_endpoints": runtime_failures,
        "endpoints": normalized_rows,
    }


def render_markdown(report: dict[str, Any], max_uncovered_rows: int = 150) -> str:
    meta = report["metadata"]
    target = report["target"]
    summary = report["summary"]
    modules = report["by_module"]
    uncovered = report["uncovered_endpoints"]
    runtime_failed = report["runtime_failed_endpoints"]

    lines: list[str] = []
    lines.append("# API Coverage Report (OQ-011)")
    lines.append("")
    lines.append(f"- Generated at: `{meta['generated_at']}`")
    lines.append(f"- Source matrix mode: `{meta.get('source_matrix_mode') or 'unknown'}`")
    lines.append(f"- Source matrix generated at: `{meta.get('source_matrix_generated_at') or 'unknown'}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total endpoints: `{summary['total_endpoints']}`")
    lines.append(f"- Covered endpoints: `{summary['covered_endpoints']}`")
    lines.append(f"- Uncovered endpoints: `{summary['uncovered_endpoints']}`")
    lines.append(f"- Coverage percent: `{summary['coverage_percent']}%`")
    lines.append(f"- Runtime validated endpoints: `{summary['runtime_validated_endpoints']}`")
    lines.append(f"- Runtime failed endpoints: `{summary['runtime_failed_endpoints']}`")
    lines.append(f"- Test referenced endpoints (no runtime smoke): `{summary['test_referenced_endpoints']}`")
    lines.append("")
    lines.append("## Target Tracking")
    lines.append("")
    lines.append(f"- Expected endpoints (target): `{target['expected_endpoints']}`")
    lines.append(f"- Observed endpoints: `{target['observed_endpoints']}`")
    lines.append(f"- Target met: `{target['target_met']}`")
    lines.append(f"- Endpoint gap: `{target['endpoint_gap']}`")
    lines.append("")
    lines.append("## Coverage By Module")
    lines.append("")
    lines.append("| Module | Total | Covered | Uncovered | Runtime PASS | Runtime FAIL | Test Ref | Coverage % |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for module in modules:
        lines.append(
            "| {module} | {total} | {covered} | {not_covered} | {runtime_validated} | {runtime_failed} | {test_referenced} | {coverage_percent}% |".format(
                **module
            )
        )
    lines.append("")

    lines.append("## Runtime Failures")
    lines.append("")
    if not runtime_failed:
        lines.append("- No runtime failures captured in smoke data.")
    else:
        lines.append("| Method | Path | Module | Status Code | Error |")
        lines.append("|---|---|---|---:|---|")
        for row in runtime_failed:
            status_code = row["smoke_status_code"] if row["smoke_status_code"] is not None else "-"
            error_text = str(row["smoke_error"] or "").replace("|", "\\|")
            lines.append(
                f"| {row['method']} | `{row['path']}` | {row['module']} | {status_code} | {error_text} |"
            )
    lines.append("")

    lines.append(f"## Uncovered Endpoints (top {max_uncovered_rows})")
    lines.append("")
    if not uncovered:
        lines.append("- No uncovered endpoints.")
    else:
        lines.append("| Method | Path | Module | Operation Id |")
        lines.append("|---|---|---|---|")
        for row in uncovered[:max_uncovered_rows]:
            lines.append(
                f"| {row['method']} | `{row['path']}` | {row['module']} | {row.get('operation_id') or ''} |"
            )
        if len(uncovered) > max_uncovered_rows:
            lines.append("")
            lines.append(
                f"_Truncated: {len(uncovered) - max_uncovered_rows} additional uncovered endpoints not shown._"
            )
    lines.append("")
    return "\n".join(lines)


def _clip(text: str, max_chars: int = 20000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]..."


def _run(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return {
        "command": " ".join(cmd),
        "returncode": completed.returncode,
        "stdout": _clip(stdout),
        "stderr": _clip(stderr),
        "stdout_full": stdout,
    }


def collect_docker_evidence(log_tail_lines: int) -> tuple[dict[str, Any], str]:
    base_cmd = ["docker", "compose"]
    ps_json = _run(base_cmd + ["ps", "--format", "json"])
    ps_plain = _run(base_cmd + ["ps"])
    images = _run(base_cmd + ["images"])
    logs_api = _run(base_cmd + ["logs", "--no-color", "--tail", str(log_tail_lines), "janus-api"])

    if logs_api["returncode"] != 0:
        logs_fallback = _run(base_cmd + ["logs", "--no-color", "--tail", str(log_tail_lines)])
    else:
        logs_fallback = None

    ps_rows = parse_docker_ps_output(str(ps_json.get("stdout_full") or ""))
    api_logs_text = str(logs_api.get("stdout_full") or "")
    if not api_logs_text and logs_fallback:
        api_logs_text = str(logs_fallback.get("stdout_full") or "")

    pattern_counts = {
        "error": len(re.findall(r"\berror\b", api_logs_text, flags=re.IGNORECASE)),
        "exception": len(re.findall(r"\bexception\b", api_logs_text, flags=re.IGNORECASE)),
        "traceback": len(re.findall(r"traceback", api_logs_text, flags=re.IGNORECASE)),
        "critical": len(re.findall(r"\bcritical\b", api_logs_text, flags=re.IGNORECASE)),
    }

    evidence = {
        "generated_at": now_iso(),
        "docker_available": ps_plain["returncode"] == 0 or ps_json["returncode"] == 0,
        "commands": {
            "compose_ps_json": {
                "command": ps_json["command"],
                "returncode": ps_json["returncode"],
                "stdout": ps_json["stdout"],
                "stderr": ps_json["stderr"],
            },
            "compose_ps": {
                "command": ps_plain["command"],
                "returncode": ps_plain["returncode"],
                "stdout": ps_plain["stdout"],
                "stderr": ps_plain["stderr"],
            },
            "compose_images": {
                "command": images["command"],
                "returncode": images["returncode"],
                "stdout": images["stdout"],
                "stderr": images["stderr"],
            },
            "compose_logs_api": {
                "command": logs_api["command"],
                "returncode": logs_api["returncode"],
                "stdout": logs_api["stdout"],
                "stderr": logs_api["stderr"],
            },
        },
        "services": ps_rows,
        "api_log_signal_counts": pattern_counts,
    }
    if logs_fallback:
        evidence["commands"]["compose_logs_fallback"] = {
            "command": logs_fallback["command"],
            "returncode": logs_fallback["returncode"],
            "stdout": logs_fallback["stdout"],
            "stderr": logs_fallback["stderr"],
        }

    return evidence, api_logs_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate API coverage report for OQ-011.")
    parser.add_argument("--matrix-json", default=str(DEFAULT_MATRIX_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument(
        "--expected-endpoints",
        type=int,
        default=229,
        help="Target endpoint count tracked by OQ-011.",
    )
    parser.add_argument(
        "--collect-docker-evidence",
        action="store_true",
        help="Collect docker compose evidence and API log tail.",
    )
    parser.add_argument("--docker-evidence-json", default=str(DEFAULT_DOCKER_EVIDENCE_JSON))
    parser.add_argument("--docker-log-tail-file", default=str(DEFAULT_DOCKER_LOG_TAIL))
    parser.add_argument("--docker-log-tail-lines", type=int, default=200)
    parser.add_argument(
        "--fail-on-target-gap",
        action="store_true",
        help="Exit with code 1 when observed endpoints are below expected-endpoints.",
    )
    parser.add_argument(
        "--fail-on-uncovered",
        action="store_true",
        help="Exit with code 1 when uncovered endpoints > 0.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    matrix_path = Path(args.matrix_json)
    report_json_path = Path(args.output_json)
    report_md_path = Path(args.output_md)

    matrix = load_matrix(matrix_path)
    report = build_coverage_report(matrix, expected_endpoints=args.expected_endpoints)

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)

    report_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report_md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"[ok] wrote {report_json_path}")
    print(f"[ok] wrote {report_md_path}")
    print(
        f"[summary] endpoints={report['summary']['total_endpoints']} coverage={report['summary']['coverage_percent']}% uncovered={report['summary']['uncovered_endpoints']}"
    )

    if args.collect_docker_evidence:
        evidence, log_tail = collect_docker_evidence(log_tail_lines=max(1, args.docker_log_tail_lines))
        docker_evidence_path = Path(args.docker_evidence_json)
        docker_log_tail_path = Path(args.docker_log_tail_file)
        docker_evidence_path.parent.mkdir(parents=True, exist_ok=True)
        docker_log_tail_path.parent.mkdir(parents=True, exist_ok=True)
        docker_evidence_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        docker_log_tail_path.write_text(log_tail, encoding="utf-8")
        print(f"[ok] wrote {docker_evidence_path}")
        print(f"[ok] wrote {docker_log_tail_path}")

    if args.fail_on_target_gap and not report["target"]["target_met"]:
        print("[fail] target endpoint count not met.")
        return 1
    if args.fail_on_uncovered and report["summary"]["uncovered_endpoints"] > 0:
        print("[fail] uncovered endpoints detected.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
