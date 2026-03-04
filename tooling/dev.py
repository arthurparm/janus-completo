#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    printable = " ".join(cmd)
    print(f"$ {printable}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


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


def npm_install(frontend_dir: Path) -> None:
    lockfile = frontend_dir / "package-lock.json"
    if lockfile.exists():
        run(["npm", "ci"], cwd=frontend_dir)
    else:
        run(["npm", "install"], cwd=frontend_dir)


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
    if shutil.which("npm") is None:
        raise RuntimeError("npm is required but was not found in PATH.")
    run([sys.executable, "-m", "pip", "install", "-r", str(BACKEND_DIR / "requirements.txt")])
    npm_install(FRONTEND_DIR)


def cmd_up() -> None:
    ensure_env_files()
    env_pc2 = resolve_env_file(".env.pc2")
    env_pc1 = resolve_env_file(".env.pc1")
    run(
        [
            "docker",
            "build",
            "-f",
            "backend/docker/Dockerfile",
            "-t",
            "janus-completo-janus-api:latest",
            "backend",
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
            "up",
            "-d",
        ],
        cwd=REPO_ROOT,
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
        ],
        cwd=REPO_ROOT,
    )
    wait_for_health(HEALTH_URLS)


def cmd_qa() -> None:
    run(
        [sys.executable, "-m", "pytest", "-q", *BACKEND_CRITICAL_TESTS],
        cwd=REPO_ROOT,
    )
    run(["npm", "run", "lint"], cwd=FRONTEND_DIR)
    run(["npm", "run", "test"], cwd=FRONTEND_DIR)
    run(["npm", "run", "build", "--", "--configuration", "development"], cwd=FRONTEND_DIR)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unified local developer workflow for janus-completo.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("setup", help="Install backend/frontend dependencies.")
    subparsers.add_parser("up", help="Start docker stack and wait for health checks.")
    subparsers.add_parser("qa", help="Run backend critical tests and frontend quality gates.")
    subparsers.add_parser("down", help="Stop local docker stack.")
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
    else:
        raise RuntimeError(f"Unknown command: {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
