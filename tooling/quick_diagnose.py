#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://100.89.17.105:8000"

HEALTH_ENDPOINTS = [
    "/health",
    "/healthz",
    "/api/v1/system/status",
    "/api/v1/workers/status",
]

DEPENDENCY_COMMANDS: dict[str, list[str]] = {
    "python3": [sys.executable, "--version"],
    "docker": ["docker", "--version"],
    "docker_compose": ["docker", "compose", "version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
}

CONFIG_KEYS: dict[str, list[str]] = {
    "backend_required": [
        "OPENAI_API_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "SECRET_KEY",
    ],
    "frontend_required": [
        "VITE_API_BASE_URL",
    ],
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def merge_env_sources() -> dict[str, str]:
    merged: dict[str, str] = {}
    merged.update(load_env_file(ROOT / "backend" / "app" / ".env"))
    merged.update(load_env_file(ROOT / "frontend" / ".env"))
    merged.update(load_env_file(ROOT / "frontend" / ".env.production"))
    for key, value in os.environ.items():
        merged[key] = value
    return merged


def health_probe(url: str, timeout: float) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = int(response.getcode())
            body = response.read(600).decode("utf-8", errors="replace")
            return {
                "ok": 200 <= status < 400,
                "status_code": status,
                "body_sample": body,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(600).decode("utf-8", errors="replace")
        return {"ok": False, "status_code": int(exc.code), "error": str(exc), "body_sample": body}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_health_checks(base_url: str, timeout: float) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for path in HEALTH_ENDPOINTS:
        report[path] = health_probe(f"{base_url.rstrip('/')}{path}", timeout=timeout)
    ok = all(item.get("ok", False) for item in report.values())
    return {"ok": ok, "endpoints": report}


def dependency_version(command: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
        text = (proc.stdout or proc.stderr or "").strip()
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "version": text}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_dependency_checks() -> dict[str, Any]:
    report: dict[str, Any] = {}
    for name, command in DEPENDENCY_COMMANDS.items():
        tool_name = command[0]
        if shutil.which(tool_name) is None:
            report[name] = {"ok": False, "error": f"{tool_name} not found in PATH"}
            continue
        report[name] = dependency_version(command)
    ok = all(item.get("ok", False) for item in report.values())
    return {"ok": ok, "dependencies": report}


def run_config_checks() -> dict[str, Any]:
    env = merge_env_sources()
    groups: dict[str, Any] = {}
    global_ok = True

    for group, keys in CONFIG_KEYS.items():
        entries: dict[str, Any] = {}
        missing: list[str] = []
        for key in keys:
            present = key in env and bool(str(env[key]).strip())
            entries[key] = {"present": present}
            if not present:
                missing.append(key)
        ok = len(missing) == 0
        groups[group] = {"ok": ok, "missing": missing, "keys": entries}
        global_ok = global_ok and ok

    return {"ok": global_ok, "groups": groups}


def build_summary(report: dict[str, Any]) -> str:
    lines = [
        "== Janus Quick Diagnose ==",
        f"generated_at: {report['metadata']['generated_at']}",
        f"base_url: {report['metadata']['base_url']}",
        "",
    ]
    checks = report["checks"]
    if "health" in checks:
        lines.append(f"health: {'OK' if checks['health']['ok'] else 'FAIL'}")
    if "deps" in checks:
        lines.append(f"deps: {'OK' if checks['deps']['ok'] else 'FAIL'}")
    if "config" in checks:
        lines.append(f"config: {'OK' if checks['config']['ok'] else 'FAIL'}")
    lines.append(f"overall: {'OK' if report['ok'] else 'FAIL'}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CLI de diagnóstico rápido para health, dependências e configuração do Janus.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--checks",
        default="health,deps,config",
        help="Lista separada por vírgula: health,deps,config",
    )
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    enabled = {item.strip().lower() for item in str(args.checks).split(",") if item.strip()}
    allowed = {"health", "deps", "config"}
    unknown = enabled - allowed
    if unknown:
        raise SystemExit(f"Unknown checks: {sorted(unknown)}")

    checks: dict[str, Any] = {}
    if "health" in enabled:
        checks["health"] = run_health_checks(base_url=str(args.base_url), timeout=float(args.timeout))
    if "deps" in enabled:
        checks["deps"] = run_dependency_checks()
    if "config" in enabled:
        checks["config"] = run_config_checks()

    ok = all(item.get("ok", False) for item in checks.values()) if checks else False
    report = {
        "ok": ok,
        "metadata": {
            "generated_at": now_iso(),
            "base_url": str(args.base_url),
            "repo_root": str(ROOT),
        },
        "checks": checks,
    }

    if args.output_json:
        path = Path(str(args.output_json))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(build_summary(report))
    print("")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
