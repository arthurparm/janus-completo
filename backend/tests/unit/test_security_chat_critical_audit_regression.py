import base64
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.infrastructure.auth import create_token, get_actor_user_id
from app.core.infrastructure.python_sandbox import PythonSandbox
from app.core.security.request_guard import require_admin_actor, require_authenticated_actor_id
from app.repositories import user_repository


class _Req:
    def __init__(self, actor_user_id: str | int | None = None, headers: dict | None = None):
        self.state = SimpleNamespace(actor_user_id=str(actor_user_id) if actor_user_id else None)
        self.headers = headers or {}


def test_supabase_jwt_rejects_token_without_signature():
    bad_token = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    bad_token += "." + base64.urlsafe_b64encode(b'{"email":"test@test.com"}').rstrip(b"=").decode()

    from app.api.v1.endpoints.auth import supabase_exchange

    class _FakePayload:
        token: str = bad_token

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "test-secret-123")

    class _NullRepo:
        pass

    repo = _NullRepo()

    try:
        import asyncio
        asyncio.run(supabase_exchange(_FakePayload(), repo))
        assert False, "Expected exception"
    except HTTPException as e:
        assert e.status_code == 400
        assert "Invalid token" in e.detail
    finally:
        monkeypatch.undo()


def test_supabase_jwt_rejects_forged_signature():
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(b'{"email":"hacker@evil.com"}').rstrip(b"=").decode()
    forged_sig = base64.urlsafe_b64encode(b"fake_signature_1234567890").rstrip(b"=").decode()
    forged_token = f"{header}.{payload_b64}.{forged_sig}"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "real-secret")

    from app.api.v1.endpoints.auth import supabase_exchange

    class _FakePayload:
        token: str = forged_token

    try:
        import asyncio
        asyncio.run(supabase_exchange(_FakePayload(), object()))
        assert False, "Expected exception"
    except HTTPException as e:
        assert e.status_code == 400
    finally:
        monkeypatch.undo()


def test_supabase_jwt_returns_503_when_secret_not_configured():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "")

    from app.api.v1.endpoints.auth import supabase_exchange

    class _FakePayload:
        token: str = "header.payload.signature"

    try:
        import asyncio
        asyncio.run(supabase_exchange(_FakePayload(), object()))
        assert False, "Expected exception"
    except HTTPException as e:
        assert e.status_code == 503
    finally:
        monkeypatch.undo()


def test_admin_config_requires_authenticated_actor():
    with pytest.raises(HTTPException) as exc:
        require_admin_actor(_Req(actor_user_id=None))
    assert exc.value.status_code == 401


def test_admin_config_blocks_non_admin(monkeypatch):
    def fake_is_admin(self, user_id: int) -> bool:
        return False

    def fake_has_role(self, user_id: int, role_name: str) -> bool:
        return False

    monkeypatch.setattr(user_repository.UserRepository, "has_role", fake_has_role)
    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    with pytest.raises(HTTPException) as exc:
        require_admin_actor(_Req(actor_user_id=42))
    assert exc.value.status_code == 403


def test_sandbox_execute_requires_authenticated_actor():
    with pytest.raises(HTTPException) as exc:
        require_authenticated_actor_id(_Req(actor_user_id=None))
    assert exc.value.status_code == 401


def test_sandbox_evaluate_requires_authenticated_actor():
    with pytest.raises(HTTPException) as exc:
        require_authenticated_actor_id(_Req(actor_user_id=None))
    assert exc.value.status_code == 401


def test_sandbox_rejects_process_mode_for_code_execution(monkeypatch):
    monkeypatch.setattr(settings, "SANDBOX_MODE", "process")
    sandbox = PythonSandbox()
    result = sandbox.execute("x = 1")
    assert not result.success
    assert "requires Docker" in (result.error or "")


def test_sandbox_allows_expression_in_process_mode(monkeypatch):
    monkeypatch.setattr(settings, "SANDBOX_MODE", "process")
    sandbox = PythonSandbox()
    result = sandbox.execute_expression("2 + 2")
    assert result.success
    assert "4" in result.output


def test_sandbox_docker_mode_code_rejected_without_docker(monkeypatch):
    monkeypatch.setattr(settings, "SANDBOX_MODE", "docker")
    monkeypatch.setattr(settings, "SANDBOX_TIMEOUT_SECONDS", 5)
    sandbox = PythonSandbox()

    def fake_run_in_docker(*args, **kwargs):
        raise RuntimeError("Docker unavailable")

    monkeypatch.setattr(sandbox, "_run_in_docker", fake_run_in_docker)

    result = sandbox.execute("x = 1")
    assert not result.success


_os_tools_available = False
_write_fn = None
_read_fn = None
_list_fn = None
try:
    from app.core.tools import os_tools as _ot
    _write_fn = getattr(getattr(_ot, 'write_system_file', None), 'func', None) or getattr(_ot, 'write_system_file', None)
    _read_fn = getattr(getattr(_ot, 'read_system_file', None), 'func', None) or getattr(_ot, 'read_system_file', None)
    _list_fn = getattr(getattr(_ot, 'list_directory', None), 'func', None) or getattr(_ot, 'list_directory', None)
    _os_tools_available = _write_fn is not None
except ImportError:
    pass


@pytest.mark.skipif(not _os_tools_available, reason="os_tools requires langchain")
def test_write_system_file_blocks_outside_workspace(monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_ROOT", "/app/workspace")
    result = _write_fn("/etc/passwd", "hacker:1000:1000:root")
    assert "Acesso negado" in result or "Erro" in result


@pytest.mark.skipif(not _os_tools_available, reason="os_tools requires langchain")
def test_write_system_file_blocks_blocked_extensions(monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_ROOT", "/app/workspace")
    result = _write_fn("/app/workspace/evil.sh", "#!/bin/bash\necho hacked")
    assert "bloqueada" in result or "Erro" in result


@pytest.mark.skipif(not _os_tools_available, reason="os_tools requires langchain")
def test_write_system_file_blocks_oversized_content(monkeypatch):
    monkeypatch.setattr(settings, "WORKSPACE_ROOT", "/app/workspace")
    result = _write_fn("/app/workspace/big.txt", "A" * 2_000_000)
    assert "1MB" in result or "limite" in result or "Erro" in result


@pytest.mark.skipif(not _os_tools_available, reason="os_tools requires langchain")
def test_read_system_file_blocks_system_directories():
    result = _read_fn("/etc/shadow")
    assert "Acesso negado" in result or "Erro" in result


@pytest.mark.skipif(not _os_tools_available, reason="os_tools requires langchain")
def test_read_system_file_blocks_git_and_env_files():
    result = _read_fn("/app/workspace/.env")
    assert "bloqueado" in result or "Acesso negado" in result or "Erro" in result or ".env" in result.lower()


@pytest.mark.skipif(not _os_tools_available, reason="os_tools requires langchain")
def test_list_directory_blocks_system_directories():
    result = _list_fn("/etc")
    assert "Acesso negado" in result or "Erro" in result


def test_x_user_id_triggers_audit_event_when_accepted(monkeypatch):
    audit_events = []

    def fake_audit(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setattr(settings, "AUTH_TRUST_X_USER_ID_HEADER", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(
        "app.core.infrastructure.auth.record_audit_event_direct", fake_audit
    )

    req = _Req(headers={"X-User-Id": "99"})
    req.state.actor_user_id = None
    result = get_actor_user_id(req)

    assert result == 99
    assert len(audit_events) == 1
    assert audit_events[0]["action"] == "x_user_id_used_for_auth"
    assert audit_events[0]["details_json"]["x_user_id"] == "99"
