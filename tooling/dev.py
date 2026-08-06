#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_DIR = REPO_ROOT / "backend"
ENV_FILES = (
    (".env.pc1", ".env.pc1.example"),
    (".env.pc2", ".env.pc2.example"),
)

BACKEND_CRITICAL_TESTS = [
    "qa/test_api_visibility_endpoints.py",
    "qa/test_tool_executor_policy_guards.py",
    "qa/test_chat_agent_loop_content_safety.py",
    "qa/test_memory_quota_enforcement.py",
    "qa/test_generative_memory_llm_role_priority.py",
    "qa/test_chat_endpoint_contract.py",
    "qa/test_observability_request_dashboard.py",
    "qa/test_db_migration_service_contract.py",
    "qa/test_knowledge_code_query_contract.py",
]

HEALTH_URLS = [
    "http://localhost:8000/health",
    "http://localhost:8000/healthz",
    "http://localhost:8000/api/v1/system/status",
]

MIN_BACKEND_PYTHON = (3, 11)
MAX_BACKEND_PYTHON_EXCLUSIVE = (3, 13)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    printable = " ".join(cmd)
    print(f"$ {printable}")
    process_env = None
    if env is not None:
        process_env = {**os.environ, **env}
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=process_env, check=True)


def resolve_required_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError(f"{name} is required but was not found in PATH.")
    return executable


def is_supported_backend_python(version_info: tuple[int, int] | None = None) -> bool:
    version = version_info or sys.version_info[:2]
    return MIN_BACKEND_PYTHON <= tuple(version[:2]) < MAX_BACKEND_PYTHON_EXCLUSIVE


def ensure_supported_backend_python() -> None:
    if is_supported_backend_python():
        return
    current = ".".join(str(part) for part in sys.version_info[:3])
    supported = (
        f"{MIN_BACKEND_PYTHON[0]}.{MIN_BACKEND_PYTHON[1]} <= Python < "
        f"{MAX_BACKEND_PYTHON_EXCLUSIVE[0]}.{MAX_BACKEND_PYTHON_EXCLUSIVE[1]}"
    )
    raise RuntimeError(
        f"Unsupported Python runtime for Janus backend: {current}. "
        f"Use {supported}. The backend requirements use environment markers in this range; "
        "running setup or qa outside it can skip required packages and produce misleading import failures."
    )


def ensure_env_files() -> None:
    for target_name, source_name in ENV_FILES:
        target = REPO_ROOT / target_name
        if target.exists():
            continue
        source = REPO_ROOT / source_name
        if not source.exists():
            raise RuntimeError(f"Missing required env template: {source_name}")
        shutil.copyfile(source, target)
        print(f"Created {target_name} from {source_name}")


def resolve_env_file(name: str) -> str:
    preferred = REPO_ROOT / name
    if preferred.exists():
        return name
    fallback = REPO_ROOT / f"{name}.example"
    if fallback.exists():
        return f"{name}.example"
    raise RuntimeError(f"Could not find {name} or {name}.example")


def local_pc2_host_overrides() -> dict[str, str]:
    return {
        "NEO4J_URI": "bolt://host.docker.internal:7687",
        "QDRANT_HOST": "host.docker.internal",
        "OLLAMA_HOST": "http://host.docker.internal:11434",
    }


def local_pc2_resource_overrides() -> dict[str, str]:
    return {
        "NEO4J_HEAP_INITIAL": "512M",
        "NEO4J_HEAP_MAX": "2G",
        "NEO4J_PAGECACHE": "512M",
        "NEO4J_MEM_LIMIT": "4g",
        "NEO4J_MEMSWAP_LIMIT": "5g",
    }


def npm_install(frontend_dir: Path) -> None:
    npm = resolve_required_executable("npm")
    lockfile = frontend_dir / "package-lock.json"
    if lockfile.exists():
        run([npm, "ci"], cwd=frontend_dir)
    else:
        run([npm, "install"], cwd=frontend_dir)


def wait_for_health(urls: list[str], retries: int = 90, sleep_seconds: float = 2.0) -> None:
    for _ in range(retries):
        all_ok = True
        for url in urls:
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status < 200 or response.status >= 300:
                        all_ok = False
                        break
            except (urllib.error.URLError, TimeoutError, ValueError):
                all_ok = False
                break
        if all_ok:
            print("Health checks passed.")
            return
        time.sleep(sleep_seconds)
    raise RuntimeError("Health checks did not pass in the expected time window.")


def cmd_setup() -> None:
    ensure_supported_backend_python()
    run([sys.executable, "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt")])
    npm_install(FRONTEND_DIR)


def cmd_up() -> None:
    ensure_env_files()
    env_pc2 = resolve_env_file(".env.pc2")
    env_pc1 = resolve_env_file(".env.pc1")
    run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.pc2.yml",
            "--env-file",
            env_pc2,
            "up",
            "-d",
        ],
        cwd=REPO_ROOT,
        env=local_pc2_resource_overrides(),
    )
    run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.pc1.yml",
            "--env-file",
            env_pc1,
            "up",
            "-d",
            "--build",
        ],
        cwd=REPO_ROOT,
        env=local_pc2_host_overrides(),
    )
    wait_for_health(HEALTH_URLS)


def cmd_qa() -> None:
    ensure_supported_backend_python()
    npm = resolve_required_executable("npm")
    run(
        [sys.executable, "-m", "pytest", "-q", *BACKEND_CRITICAL_TESTS],
        cwd=REPO_ROOT,
    )
    run([npm, "run", "lint"], cwd=FRONTEND_DIR)
    run([npm, "run", "test"], cwd=FRONTEND_DIR)
    run([npm, "run", "build", "--", "--configuration", "development"], cwd=FRONTEND_DIR)


def cmd_down() -> None:
    env_pc1 = resolve_env_file(".env.pc1")
    env_pc2 = resolve_env_file(".env.pc2")
    run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.pc1.yml",
            "--env-file",
            env_pc1,
            "down",
        ],
        cwd=REPO_ROOT,
    )
    run(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.pc2.yml",
            "--env-file",
            env_pc2,
            "down",
        ],
        cwd=REPO_ROOT,
    )


def cmd_doctor(args: argparse.Namespace) -> None:
    quick_diag_script = REPO_ROOT / "tooling" / "quick_diagnostics.py"
    cmd = [
        sys.executable,
        str(quick_diag_script),
        "--host",
        str(args.host),
        "--backend-port",
        str(args.backend_port),
        "--frontend-port",
        str(args.frontend_port),
        "--timeout",
        str(args.timeout),
    ]
    if args.json_out:
        cmd.extend(["--json-out", str(args.json_out)])
    if args.verify_tls:
        cmd.append("--verify-tls")
    run(cmd, cwd=REPO_ROOT)


def cmd_checklist(args: argparse.Namespace) -> None:
    checklist_script = REPO_ROOT / "tooling" / "exit_checklist.py"
    cmd = [
        sys.executable,
        str(checklist_script),
        "--type",
        str(args.task_type),
        "--format",
        str(args.format),
    ]
    if args.out:
        cmd.extend(["--out", str(args.out)])
    run(cmd, cwd=REPO_ROOT)


def cmd_readiness(args: argparse.Namespace) -> None:
    readiness_script = REPO_ROOT / "tooling" / "production_readiness.py"
    cmd = [
        sys.executable,
        str(readiness_script),
        "--baseline",
        str(args.baseline),
        "--format",
        str(args.format),
    ]
    for env_file in args.env_files:
        cmd.extend(["--env-file", str(env_file)])
    if args.out:
        cmd.extend(["--out", str(args.out)])
    run(cmd, cwd=REPO_ROOT)


def cmd_backfill_gate(args: argparse.Namespace) -> None:
    backfill_gate_script = REPO_ROOT / "tooling" / "backfill_quarantine_gate.py"
    cmd = [
        sys.executable,
        str(backfill_gate_script),
        "--mode",
        str(args.mode),
    ]
    if args.apply_constraints:
        cmd.append("--apply-constraints")
    if args.neo4j_backfill_limit is not None:
        cmd.extend(["--neo4j-backfill-limit", str(args.neo4j_backfill_limit)])
    if args.neo4j_audit_output:
        cmd.extend(["--neo4j-audit-output", str(args.neo4j_audit_output)])
    if args.report:
        cmd.extend(["--report", str(args.report)])
    run(cmd, cwd=REPO_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified local developer workflow for janus-completo.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("setup", help="Install backend/frontend dependencies.")
    subparsers.add_parser("up", help="Start docker stack and wait for health checks.")
    subparsers.add_parser("qa", help="Run backend critical tests and frontend quality gates.")
    subparsers.add_parser("down", help="Stop local docker stack.")
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run DX-007 quick diagnostics against a target host (health + deps + config).",
    )
    doctor_parser.add_argument("--host", default="100.89.17.105")
    doctor_parser.add_argument("--backend-port", type=int, default=8000)
    doctor_parser.add_argument("--frontend-port", type=int, default=4300)
    doctor_parser.add_argument("--timeout", type=float, default=5.0)
    doctor_parser.add_argument("--json-out", default="")
    doctor_parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="Enable TLS certificate verification (disabled by default for self-signed envs).",
    )
    checklist_parser = subparsers.add_parser(
        "checklist",
        help="Generate AG-007 output checklist by task type (codigo/docs/deploy).",
    )
    checklist_parser.add_argument("--type", dest="task_type", choices=("codigo", "docs", "deploy"), required=True)
    checklist_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    checklist_parser.add_argument("--out", default="")
    readiness_parser = subparsers.add_parser(
        "readiness",
        help="Validate the production-readiness baseline and optional env files.",
    )
    readiness_parser.add_argument(
        "--baseline",
        default=str(REPO_ROOT / "documentation" / "operations" / "production-readiness.baseline.json"),
    )
    readiness_parser.add_argument("--env-file", dest="env_files", action="append", default=[])
    readiness_parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    readiness_parser.add_argument("--out", default="")
    backfill_gate_parser = subparsers.add_parser(
        "backfill-gate",
        help="Run the operational backfill/quarantine gate before applying constraints.",
    )
    backfill_gate_parser.add_argument("--mode", choices=("full", "sql-only", "neo4j-only"), default="full")
    backfill_gate_parser.add_argument("--apply-constraints", action="store_true")
    backfill_gate_parser.add_argument("--neo4j-backfill-limit", type=int, default=None)
    backfill_gate_parser.add_argument("--neo4j-audit-output", default="")
    backfill_gate_parser.add_argument("--report", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = str(args.command)
    if command == "setup":
        cmd_setup()
    elif command == "up":
        cmd_up()
    elif command == "qa":
        cmd_qa()
    elif command == "down":
        cmd_down()
    elif command == "doctor":
        cmd_doctor(args)
    elif command == "checklist":
        cmd_checklist(args)
    elif command == "readiness":
        cmd_readiness(args)
    elif command == "backfill-gate":
        cmd_backfill_gate(args)
    else:
        raise RuntimeError(f"Unknown command: {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
