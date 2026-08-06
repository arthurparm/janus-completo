#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

ERROR_PATTERNS = ("\"level\":\"error\"", " ERROR ", "Traceback", "Exception", "ERROR:")
ENV_BLOCK_HINTS = (
    "/firebase/",
    "/supabase/",
    "/oauth/",
    "/deployment/",
    "/llm/",
    "/documents/link-url",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_request_id(prefix: str, phase: str, suite: str, seq: int) -> str:
    return f"{prefix}-{phase}-{suite}-{seq:04d}-{uuid.uuid4().hex[:8]}"


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            out[k] = "<redacted>"
        else:
            out[k] = v
    return out


def classify_gate(result_class: str, log_evidence: str) -> str:
    if result_class == "fail_transport":
        return "fail_transport"
    if result_class == "fail_server_5xx":
        return "fail_5xx"
    if log_evidence == "missing":
        return "fail_log_evidence_missing"
    if log_evidence == "weak":
        return "warn_log_evidence_weak"
    return "pass"


def classify_http_status(
    status: int,
    expected_statuses: list[int] | None = None,
    *,
    phase: str = "auth",
    path: str = "",
    notes: str = "",
) -> str:
    expected = set(expected_statuses or [])
    if status in expected:
        if 200 <= status < 400:
            return "pass_success"
        if phase == "unauth" and status in {401, 403}:
            return "pass_expected_auth_rejection"
        if is_env_blocked_expected(path=path, status=status, notes=notes):
            return "blocked_by_env_expected"
        return "pass_contract_rejection"
    if 500 <= status <= 599:
        return "fail_server_5xx"
    if phase == "unauth" and status in {401, 403}:
        return "pass_expected_auth_rejection"
    if status == 422:
        return "pass_expected_contract_rejection" if phase == "unauth" else "pass_contract_rejection"
    if is_env_blocked_expected(path=path, status=status, notes=notes):
        return "blocked_by_env_expected"
    return "fail_unexpected_status"


def is_env_blocked_expected(*, path: str, status: int, notes: str = "") -> bool:
    if status not in {400, 401, 403, 404, 409, 422, 429, 500, 501, 502, 503, 504}:
        return False
    p = (path or "").lower()
    n = (notes or "").lower()
    if any(h in p for h in ENV_BLOCK_HINTS):
        return True
    if any(w in n for w in ("external", "oauth", "firebase", "supabase", "provider", "deploy", "credencial")):
        return True
    return False


@dataclass
class DockerLogEvidence:
    request_id: str
    suite: str
    phase: str
    match_type: str
    log_source: str
    matched_lines: list[str]
    error_lines: list[str]
    response_echo_request_id: str | None = None


class DockerLogCorrelator:
    def __init__(
        self,
        *,
        service: str = "janus-api",
        container: str = "janus_api",
        grace_log_ms: int = 400,
        since_padding_sec: int = 1,
        include_weak_fallback: bool = True,
    ) -> None:
        self.service = service
        self.container = container
        self.grace_log_ms = grace_log_ms
        self.since_padding_sec = since_padding_sec
        self.include_weak_fallback = include_weak_fallback

    def _run(self, cmd: list[str]) -> tuple[int, str]:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, check=False)
            out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
            return p.returncode, out
        except Exception as exc:
            return 1, str(exc)

    def _fetch_logs_since(self, since_dt: datetime) -> tuple[str, str]:
        since = isoformat_utc(since_dt)
        compose_cmd = ["docker", "compose", "logs", "--no-color", "--since", since, self.service]
        rc, out = self._run(compose_cmd)
        if rc == 0:
            return "docker-compose", out
        docker_cmd = ["docker", "logs", "--since", since, self.container]
        rc2, out2 = self._run(docker_cmd)
        return ("docker", out2) if rc2 == 0 else ("unavailable", (out + "\n" + out2).strip())

    def correlate(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        phase: str,
        suite: str,
        t0: datetime,
        response_echo_request_id: str | None = None,
    ) -> DockerLogEvidence:
        if self.grace_log_ms > 0:
            time.sleep(self.grace_log_ms / 1000.0)
        source, text = self._fetch_logs_since(t0 - timedelta(seconds=self.since_padding_sec))
        lines = [ln for ln in text.splitlines() if ln.strip()]
        strong = [ln for ln in lines if request_id in ln and ("trace_id" in ln or "request_id" in ln)]
        matched_lines = strong[:12]
        match_type = "strong" if strong else "missing"
        if not strong and self.include_weak_fallback:
            path_hint = path.split("?")[0]
            weak = [ln for ln in lines if method in ln and path_hint in ln]
            if weak:
                matched_lines = weak[:8]
                match_type = "weak"
        error_lines = [ln for ln in matched_lines if any(p in ln for p in ERROR_PATTERNS)]
        if not error_lines:
            error_lines = [ln for ln in lines if request_id in ln and any(p in ln for p in ERROR_PATTERNS)][:8]
        return DockerLogEvidence(
            request_id=request_id,
            suite=suite,
            phase=phase,
            match_type=match_type,
            log_source=source,
            matched_lines=matched_lines,
            error_lines=error_lines,
            response_echo_request_id=response_echo_request_id,
        )


def load_oidc_test_auth(
    *, access_token: str | None = None, user_id: str | None = None
) -> dict[str, Any]:
    token = (access_token or os.getenv("JANUS_USER_ACCESS_TOKEN") or "").strip()
    resolved_user_id = (user_id or os.getenv("JANUS_USER_ID") or "").strip()
    if not token:
        return {
            "ok": False,
            "stage": "oidc_token_required",
            "message": "Set JANUS_USER_ACCESS_TOKEN to a valid external OIDC access token.",
        }
    return {
        "ok": True,
        "token": token,
        "user_id": resolved_user_id or None,
        "source": "external_oidc",
    }

def _redact_sensitive(payload: Any) -> Any:
    sensitive_key_fragments = (
        "password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "secret",
        "api_key",
        "apikey",
        "auth",
    )

    if isinstance(payload, dict):
        redacted: dict[Any, Any] = {}
        for k, v in payload.items():
            key_lower = str(k).lower()
            if any(fragment in key_lower for fragment in sensitive_key_fragments):
                redacted[k] = "<redacted>"
            else:
                redacted[k] = _redact_sensitive(v)
        return redacted
    if isinstance(payload, list):
        return [_redact_sensitive(v) for v in payload]
    return payload


def save_json(path: str | Any, payload: Any) -> None:
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sanitized_payload = _redact_sensitive(payload)
    p.write_text(json.dumps(sanitized_payload, indent=2, ensure_ascii=False))

