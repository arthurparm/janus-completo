#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.auth-validation.yml"
IMAGE = "janus-api-auth-hardening:local"
OUTPUT = ROOT / "outputs" / "qa" / "auth_docker_validation.json"
LOG_OUTPUT = ROOT / "outputs" / "qa" / "auth_docker_validation.log"


def _run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        list(args),
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=capture,
    )
    return result.stdout.strip() if capture else ""


def _compose(*args: str, capture: bool = False) -> str:
    return _run("docker", "compose", "-f", str(COMPOSE_FILE), *args, capture=capture)


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
    basic: tuple[str, str] | None = None,
    ssl_context: ssl.SSLContext | None = None,
) -> tuple[int, Any]:
    headers: dict[str, str] = {}
    body: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(form).encode()
    if basic:
        credential = base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {credential}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    try:
        return status, json.loads(raw.decode()) if raw else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status, raw.decode(errors="replace")


def _expect(
    results: list[dict[str, Any]],
    name: str,
    method: str,
    url: str,
    expected: int,
    **kwargs: Any,
) -> Any:
    status, body = _request(method, url, **kwargs)
    results.append({"name": name, "method": method, "url": url, "status": status})
    if status != expected:
        raise RuntimeError(
            f"{name}: expected HTTP {expected}, received {status}: {body!r}"
        )
    return body


def _token(
    context: ssl.SSLContext,
    *,
    subject: str,
    admin: bool = False,
    expired: bool = False,
    audience: str = "janus-user-api",
) -> str:
    query = urllib.parse.urlencode(
        {
            "subject": subject,
            "admin": str(admin).lower(),
            "expired": str(expired).lower(),
            "audience": audience,
        }
    )
    status, body = _request(
        "GET", f"https://localhost:18443/test-token?{query}", ssl_context=context
    )
    if status != 200:
        raise RuntimeError(f"test IdP user token failed: {status} {body!r}")
    return str(body["access_token"])


def _service_token(context: ssl.SSLContext, scope: str) -> str:
    status, body = _request(
        "POST",
        "https://localhost:18443/token",
        form={
            "grant_type": "client_credentials",
            "audience": "janus-control-plane",
            "scope": scope,
        },
        basic=("janus-worker", "integration-worker-credential"),
        ssl_context=context,
    )
    if status != 200:
        raise RuntimeError(f"test IdP service token failed: {status} {body!r}")
    return str(body["access_token"])


def validate(*, skip_build: bool, keep: bool) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    started_at = time.time()
    _compose("config", "--quiet")
    _compose("down", "--volumes", "--remove-orphans")
    try:
        if not skip_build:
            _run(
                "docker",
                "build",
                "-f",
                "backend/docker/Dockerfile",
                "--target",
                "final",
                "-t",
                IMAGE,
                "backend",
            )

        # PC2: stateful dependency and the external-identity test boundary.
        _compose(
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "180",
            "auth-postgres",
            "auth-idp",
        )
        _compose("up", "-d", "auth-schema")
        _compose("wait", "auth-schema")

        # PC1: three instances of the exact same immutable application image.
        _compose(
            "up",
            "-d",
            "--no-deps",
            "--wait",
            "--wait-timeout",
            "240",
            "auth-public",
            "auth-user",
            "auth-control",
        )

        with tempfile.TemporaryDirectory(prefix="janus-auth-ca-") as temp_dir:
            ca_file = Path(temp_dir) / "ca.pem"
            _compose("cp", "auth-idp:/fixture/ca.pem", str(ca_file))
            tls = ssl.create_default_context(cafile=str(ca_file))

            user_a = _token(tls, subject="user-a")
            user_b = _token(tls, subject="user-b")
            admin = _token(tls, subject="admin-a", admin=True)
            expired = _token(tls, subject="expired", expired=True)
            wrong_audience = _token(tls, subject="wrong-aud", audience="another-api")
            worker = _service_token(tls, "ops:read")
            worker_without_scope = _service_token(tls, "")

            public = "http://127.0.0.1:18001"
            user = "http://127.0.0.1:18000"
            control = "http://127.0.0.1:18002"

            _expect(results, "public_liveness", "GET", public + "/healthz/public", 200)
            _expect(results, "public_oidc_config", "GET", public + "/api/v1/auth/oidc-config", 200)
            _expect(results, "public_user_route_absent", "GET", public + "/api/v1/users/me", 404)
            _expect(results, "public_legacy_login_absent", "POST", public + "/api/v1/auth/local/login", 404)
            _expect(results, "public_old_rag_alias_absent", "POST", public + "/api/v1/rag/user_chat", 404)
            _expect(results, "runtime_docs_disabled", "GET", public + "/docs", 403)

            own_user = _expect(
                results,
                "user_a_jit_and_self_read",
                "GET",
                user + "/api/v1/users/me",
                200,
                token=user_a,
            )
            if own_user.get("email") is not None or own_user.get("id") is None:
                raise RuntimeError("unexpected JIT user representation")
            _expect(results, "anonymous_user_denied", "GET", user + "/api/v1/users/me", 401)
            _expect(results, "service_on_user_denied", "GET", user + "/api/v1/users/me", 403, token=worker)
            _expect(results, "expired_user_denied", "GET", user + "/api/v1/users/me", 401, token=expired)
            _expect(results, "wrong_audience_denied", "GET", user + "/api/v1/users/me", 401, token=wrong_audience)
            _expect(
                results,
                "client_identity_body_denied",
                "POST",
                user + "/api/v1/profiles/",
                400,
                token=user_a,
                payload={"user_id": 99, "timezone": "UTC"},
            )

            experiment = _expect(
                results,
                "user_a_creates_experiment",
                "POST",
                user + "/api/v1/evaluation/experiments",
                200,
                token=user_a,
                payload={"name": "docker-owner-check"},
            )
            _expect(
                results,
                "user_b_cross_owner_is_404",
                "POST",
                user + f"/api/v1/evaluation/experiments/{experiment['id']}/arms",
                404,
                token=user_b,
                payload={"name": "foreign", "model_spec": "model-b"},
            )
            _expect(
                results,
                "user_cannot_invoke_admin_facade",
                "POST",
                user + "/api/v1/admin-actions",
                403,
                token=user_a,
                payload={
                    "operation_id": "get_user_api_v1_users__target_actor_id__get",
                    "path_params": {"target_actor_id": own_user["id"]},
                    "query_params": {},
                    "payload": {},
                },
            )

            _expect(results, "anonymous_control_denied", "GET", control + "/healthz/control-plane", 401)
            _expect(results, "human_on_control_denied", "GET", control + "/healthz/control-plane", 403, token=user_a)
            _expect(results, "scoped_service_control_allowed", "GET", control + "/healthz/control-plane", 200, token=worker)
            _expect(results, "unscoped_service_control_denied", "GET", control + "/healthz/control-plane", 403, token=worker_without_scope)

            _expect(
                results,
                "admin_facade_delegates_to_control_plane",
                "POST",
                user + "/api/v1/admin-actions",
                200,
                token=admin,
                payload={
                    "operation_id": "get_user_api_v1_users__target_actor_id__get",
                    "path_params": {"target_actor_id": own_user["id"]},
                    "query_params": {},
                    "payload": {},
                },
            )

        completed_delegations = _compose(
            "exec",
            "-T",
            "auth-postgres",
            "psql",
            "-U",
            "janus_auth",
            "-d",
            "janus_auth",
            "-Atc",
            "SELECT COUNT(*) FROM admin_delegations WHERE result_status = 200",
            capture=True,
        )
        if int(completed_delegations) < 1:
            raise RuntimeError("admin delegation was not completed and audited")

        report = {
            "status": "passed",
            "image": IMAGE,
            "order": ["PC2", "PC1"],
            "checks": results,
            "completed_delegations": int(completed_delegations),
            "duration_seconds": round(time.time() - started_at, 3),
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        LOG_OUTPUT.write_text("validation passed; no failure logs\n", encoding="utf-8")
        return report
    except Exception as exc:
        logs = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "logs", "--no-color"],
            cwd=ROOT,
            check=False,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        LOG_OUTPUT.write_text(logs.stdout + logs.stderr, encoding="utf-8")
        OUTPUT.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "checks": results,
                    "duration_seconds": round(time.time() - started_at, 3),
                    "logs": str(LOG_OUTPUT.relative_to(ROOT)),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
    finally:
        if not keep:
            _compose("down", "--volumes", "--remove-orphans")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    report = validate(skip_build=args.skip_build, keep=args.keep)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
