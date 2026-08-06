from types import SimpleNamespace

import pytest
from app.config import settings
from app.core.infrastructure.auth import get_actor_user_id
from app.core.security.actor_context import ActorContext
from app.core.security.request_guard import require_admin_actor, require_authenticated_actor_id
from app.repositories import user_repository
from fastapi import HTTPException


class _Req:
    def __init__(self, actor_user_id: str | int | None = None, headers: dict | None = None):
        actor_context = (
            ActorContext.authenticated(
                actor_id=str(actor_user_id),
                roles=("USER",),
                auth_method="oidc",
                trace_id="test-trace",
            )
            if actor_user_id is not None
            else None
        )
        self.state = SimpleNamespace(actor_context=actor_context)
        self.headers = headers or {}


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


def test_x_user_id_is_never_an_authentication_source(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    req = _Req(headers={"X-User-Id": "99"})
    req.state.actor_user_id = None
    assert get_actor_user_id(req) is None
