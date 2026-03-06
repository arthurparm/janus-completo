#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]


def _http_probe(url: str, timeout: float, insecure_tls: bool) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    context = None
    if url.startswith("https://") and insecure_tls:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            sample = response.read(400).decode("utf-8", errors="replace")
            return {
                "ok": 200 <= response.status < 400,
                "status_code": response.status,
                "sample": sample,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status_code": int(exc.code),
            "sample": exc.read(400).decode("utf-8", errors="replace"),
            "error": str(exc),
        }
    except Exception as exc:  # pragma: no cover - exception branch validated via tests using fake probe
        return {"ok": False, "error": str(exc)}


def _tcp_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _config_checks(config_paths: list[str] | None = None) -> list[dict[str, Any]]:
    paths = config_paths or [
        ".env.pc1",
        ".env.pc2",
        "docker-compose.pc1.yml",
        "docker-compose.pc2.yml",
        "backend/app/config.py",
    ]
    results: list[dict[str, Any]] = []
    for rel in paths:
        absolute = REPO_ROOT / rel
        exists = absolute.exists()
        results.append({"file": rel, "ok": exists, "absolute_path": str(absolute)})
    return results


def build_report(
    host: str,
    backend_port: int,
    frontend_port: int,
    timeout: float,
    insecure_tls: bool,
    config_paths: list[str] | None = None,
    http_probe: Callable[[str, float, bool], dict[str, Any]] = _http_probe,
    tcp_probe: Callable[[str, int, float], dict[str, Any]] = _tcp_probe,
) -> dict[str, Any]:
    backend_base = f"http://{host}:{backend_port}"
    frontend_url = f"http://{host}:{frontend_port}"

    health_targets = {
        "backend_health": f"{backend_base}/health",
        "backend_healthz": f"{backend_base}/healthz",
        "backend_system_status": f"{backend_base}/api/v1/system/status",
        "backend_workers_status": f"{backend_base}/api/v1/workers/status",
        "frontend_root": frontend_url,
    }
    dependency_targets = {
        "neo4j_browser": "http://100.88.71.49:7474/browser/",
        "qdrant_gateway": f"https://{host}:9443",
        "ollama_tags": f"http://{host}:11434/api/tags",
    }
    dependency_tcp_targets = {
        "backend_port_open": (host, backend_port),
        "frontend_port_open": (host, frontend_port),
    }

    health_checks = {
        name: {"url": url, **http_probe(url, timeout, insecure_tls)} for name, url in health_targets.items()
    }
    dependency_checks = {
        name: {"url": url, **http_probe(url, timeout, insecure_tls)} for name, url in dependency_targets.items()
    }
    dependency_tcp_checks = {
        name: {"target": f"{host_name}:{port}", **tcp_probe(host_name, port, timeout)}
        for name, (host_name, port) in dependency_tcp_targets.items()
    }
    config_checks = _config_checks(config_paths=config_paths)

    summary = {
        "health_ok": all(item.get("ok", False) for item in health_checks.values()),
        "deps_http_ok": all(item.get("ok", False) for item in dependency_checks.values()),
        "deps_tcp_ok": all(item.get("ok", False) for item in dependency_tcp_checks.values()),
        "config_ok": all(item.get("ok", False) for item in config_checks),
    }
    summary["overall_ok"] = all(summary.values())

    return {
        "target": {"host": host, "backend_port": backend_port, "frontend_port": frontend_port},
        "summary": summary,
        "health_checks": health_checks,
        "dependency_checks": dependency_checks,
        "dependency_tcp_checks": dependency_tcp_checks,
        "config_checks": config_checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DX-007 quick diagnostics (health + deps + config).")
    parser.add_argument("--host", default="100.89.17.105")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=4300)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--json-out", default="")
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="Enable TLS certificate verification (disabled by default for self-signed envs).",
    )
    return parser.parse_args()


def _print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("Quick diagnostics summary")
    print(f"- target: {report['target']['host']}:{report['target']['backend_port']} (frontend {report['target']['frontend_port']})")
    print(f"- health_ok: {summary['health_ok']}")
    print(f"- deps_http_ok: {summary['deps_http_ok']}")
    print(f"- deps_tcp_ok: {summary['deps_tcp_ok']}")
    print(f"- config_ok: {summary['config_ok']}")
    print(f"- overall_ok: {summary['overall_ok']}")


def main() -> int:
    args = parse_args()
    report = build_report(
        host=args.host,
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        timeout=args.timeout,
        insecure_tls=not args.verify_tls,
    )
    _print_summary(report)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"- json_out: {out_path}")
    return 0 if report["summary"]["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
