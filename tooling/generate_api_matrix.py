#!/usr/bin/env python3
"""
Generate live API endpoint matrix and governance artifacts.

Inputs:
- OpenAPI from running backend (preferred) or outputs/qa/api_inventory.json fallback
- outputs/qa/api_test_results.json (smoke/scenario execution results)
- endpoint references found in qa/*.py and backend/tests/*.py

Outputs:
- documentation/qa/api-endpoint-matrix.json
- documentation/qa/api-endpoint-matrix.md
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_URL = "http://localhost:8000/openapi.json"
INVENTORY_FALLBACK = ROOT / "outputs" / "qa" / "api_inventory.json"
SMOKE_RESULTS = ROOT / "outputs" / "qa" / "api_test_results.json"
OUT_JSON = ROOT / "documentation" / "qa" / "api-endpoint-matrix.json"
OUT_MD = ROOT / "documentation" / "qa" / "api-endpoint-matrix.md"


@dataclass(frozen=True)
class EndpointKey:
    method: str
    path: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_path(path: str) -> str:
    if not path:
        return path
    p = path.strip()
    if p.startswith("/api/v1/"):
        return p
    if p.startswith("/"):
        return "/api/v1" + p
    return "/api/v1/" + p


def fetch_openapi() -> dict[str, Any] | None:
    try:
        response = requests.get(OPENAPI_URL, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def extract_endpoints_from_openapi(spec: dict[str, Any]) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    for path, methods in (spec.get("paths") or {}).items():
        if not str(path).startswith("/api/v1/"):
            continue
        for method, details in (methods or {}).items():
            method_u = str(method).upper()
            if method_u not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            tags = details.get("tags") or []
            endpoints.append(
                {
                    "method": method_u,
                    "path": path,
                    "summary": details.get("summary") or "",
                    "module": tags[0] if tags else "unknown",
                    "operation_id": details.get("operationId") or "",
                }
            )
    return endpoints


def load_endpoints() -> tuple[list[dict[str, Any]], str]:
    spec = fetch_openapi()
    if spec:
        return extract_endpoints_from_openapi(spec), "openapi_live"

    if not INVENTORY_FALLBACK.exists():
        raise FileNotFoundError(
            "No openapi live response and outputs/qa/api_inventory.json not found."
        )

    payload = json.loads(INVENTORY_FALLBACK.read_text(encoding="utf-8"))
    endpoints = payload.get("endpoints") or []
    normalized = []
    for ep in endpoints:
        normalized.append(
            {
                "method": str(ep.get("method") or "").upper(),
                "path": normalize_path(str(ep.get("path") or "")),
                "summary": ep.get("summary") or "",
                "module": ep.get("module") or "unknown",
                "operation_id": ep.get("operation_id") or "",
            }
        )
    return normalized, "api_inventory_fallback"


def load_smoke_results() -> dict[EndpointKey, dict[str, Any]]:
    if not SMOKE_RESULTS.exists():
        return {}
    raw = json.loads(SMOKE_RESULTS.read_text(encoding="utf-8"))
    mapped: dict[EndpointKey, dict[str, Any]] = {}
    for item in raw:
        method = str(item.get("method") or "GET").upper()
        path = normalize_path(str(item.get("endpoint") or item.get("path") or ""))
        if not path:
            continue
        mapped[EndpointKey(method=method, path=path)] = item
    return mapped


def discover_test_endpoint_refs() -> set[str]:
    refs: set[str] = set()
    files = list((ROOT / "qa").rglob("*.py")) + list((ROOT / "backend" / "tests").rglob("*.py"))
    p_api = re.compile(r"['\"](/api/v1/[^'\"\s]+)['\"]")
    p_rel = re.compile(
        r"['\"]/(system|knowledge|chat|auth|workers|observability|llm|autonomy|tools|tasks|documents|rag|context|profiles|users|feedback|pending_actions|consents|deployment|evaluation|productivity|collaboration|assistant|resources|learning|meta-agent|meta_agent)[^'\"\s]*['\"]"
    )
    for f in files:
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in p_api.finditer(txt):
            refs.add(normalize_path(m.group(1)))
        for m in p_rel.finditer(txt):
            refs.add(normalize_path(m.group(0).strip("'\"")))
    return refs


def build_matrix() -> dict[str, Any]:
    endpoints, source = load_endpoints()
    smoke = load_smoke_results()
    test_refs = discover_test_endpoint_refs()

    rows: list[dict[str, Any]] = []
    module_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "smoke_pass": 0, "smoke_fail": 0, "in_tests": 0}
    )
    method_stats: dict[str, int] = defaultdict(int)

    for ep in sorted(endpoints, key=lambda x: (x["module"], x["path"], x["method"])):
        method = str(ep["method"]).upper()
        path = normalize_path(str(ep["path"]))
        key = EndpointKey(method=method, path=path)
        smoke_data = smoke.get(key)
        smoke_success = None
        smoke_status_code = None
        smoke_error = None
        if smoke_data:
            smoke_success = bool(smoke_data.get("success"))
            smoke_status_code = smoke_data.get("status_code")
            smoke_error = smoke_data.get("error")

        in_tests = path in test_refs

        row = {
            "method": method,
            "path": path,
            "module": ep.get("module") or "unknown",
            "summary": ep.get("summary") or "",
            "operation_id": ep.get("operation_id") or "",
            "smoke_success": smoke_success,
            "smoke_status_code": smoke_status_code,
            "smoke_error": smoke_error,
            "referenced_in_tests": in_tests,
        }
        rows.append(row)

        module = row["module"]
        module_stats[module]["total"] += 1
        if smoke_success is True:
            module_stats[module]["smoke_pass"] += 1
        elif smoke_success is False:
            module_stats[module]["smoke_fail"] += 1
        if in_tests:
            module_stats[module]["in_tests"] += 1

        method_stats[method] += 1

    stats = {
        "total_endpoints": len(rows),
        "by_method": dict(sorted(method_stats.items())),
        "by_module": dict(sorted(module_stats.items(), key=lambda x: x[0].lower())),
        "smoke_results_loaded": len(smoke),
        "test_path_refs": len(test_refs),
    }
    return {
        "metadata": {
            "generated_at": now_iso(),
            "source": source,
            "openapi_url": OPENAPI_URL,
            "inputs": {
                "inventory_fallback": str(INVENTORY_FALLBACK.relative_to(ROOT)),
                "smoke_results": str(SMOKE_RESULTS.relative_to(ROOT)),
            },
        },
        "statistics": stats,
        "endpoints": rows,
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    md: list[str] = []
    meta = matrix["metadata"]
    stats = matrix["statistics"]
    rows = matrix["endpoints"]

    md.append("# API Endpoint Matrix (Live)")
    md.append("")
    md.append(f"- Generated at: `{meta['generated_at']}`")
    md.append(f"- Source: `{meta['source']}`")
    md.append("- Regenerate command: `python tooling/generate_api_matrix.py`")
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append(f"- Total endpoints: `{stats['total_endpoints']}`")
    md.append(f"- Smoke results loaded: `{stats['smoke_results_loaded']}`")
    md.append(f"- Test path references: `{stats['test_path_refs']}`")
    md.append("")
    md.append("### By Method")
    md.append("")
    md.append("| Method | Count |")
    md.append("|---|---:|")
    for method, count in stats["by_method"].items():
        md.append(f"| {method} | {count} |")
    md.append("")
    md.append("### By Module")
    md.append("")
    md.append("| Module | Total | Smoke Pass | Smoke Fail | Referenced In Tests |")
    md.append("|---|---:|---:|---:|---:|")
    for module, values in stats["by_module"].items():
        md.append(
            f"| {module} | {values['total']} | {values['smoke_pass']} | {values['smoke_fail']} | {values['in_tests']} |"
        )
    md.append("")
    md.append("## Endpoint Matrix")
    md.append("")
    md.append("| Method | Path | Module | Smoke | In Tests |")
    md.append("|---|---|---|---|---|")
    for r in rows:
        smoke = "N/A"
        if r["smoke_success"] is True:
            code = r["smoke_status_code"] if r["smoke_status_code"] is not None else "-"
            smoke = f"PASS ({code})"
        elif r["smoke_success"] is False:
            code = r["smoke_status_code"] if r["smoke_status_code"] is not None else "-"
            smoke = f"FAIL ({code})"
        in_tests = "yes" if r["referenced_in_tests"] else "no"
        md.append(f"| {r['method']} | `{r['path']}` | {r['module']} | {smoke} | {in_tests} |")
    md.append("")
    return "\n".join(md)


def main() -> None:
    matrix = build_matrix()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(render_markdown(matrix), encoding="utf-8")
    print(f"[ok] wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"[ok] wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
