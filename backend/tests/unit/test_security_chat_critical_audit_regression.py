from types import SimpleNamespace

import pytest
from app.config import settings
from app.core.infrastructure.auth import get_actor_user_id
from app.core.security.actor_context import ActorContext
from app.core.security.request_guard import (
    require_authenticated_actor_id,
    require_human_admin_actor_context,
)
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
        require_human_admin_actor_context(_Req(actor_user_id=None))
    assert exc.value.status_code == 401


def test_admin_config_blocks_non_admin():
    with pytest.raises(HTTPException) as exc:
        require_human_admin_actor_context(_Req(actor_user_id=42))
    assert exc.value.status_code == 403


def test_sandbox_execute_requires_authenticated_actor():
    with pytest.raises(HTTPException) as exc:
        require_authenticated_actor_id(_Req(actor_user_id=None))
    assert exc.value.status_code == 401


def test_sandbox_evaluate_requires_authenticated_actor():
    with pytest.raises(HTTPException) as exc:
        require_authenticated_actor_id(_Req(actor_user_id=None))
    assert exc.value.status_code == 401


import app.core.infrastructure.filesystem_manager as _fs


def _use_temp_workspace(monkeypatch, tmp_path):
    """Redireciona APP_DIR/WORKSPACE_DIR do filesystem_manager para um diretório isolado."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(_fs, "APP_DIR", tmp_path)
    monkeypatch.setattr(_fs, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(_fs, "ALLOWED_WRITE_ROOTS", [workspace])
    # O circuit breaker é estado global do módulo; isola cada teste dele.
    monkeypatch.setattr(_fs, "_CB_FAILURES", 0)
    monkeypatch.setattr(_fs, "_CB_OPEN_UNTIL", None)
    return workspace


def test_write_file_blocks_path_traversal(monkeypatch, tmp_path):
    _use_temp_workspace(monkeypatch, tmp_path)
    result = _fs.write_file("../../etc/passwd", "hacker:1000:1000:root")
    assert "path traversal" in result.lower() or "erro" in result.lower()
    assert not (tmp_path / "etc" / "passwd").exists()


def test_write_file_blocks_blocked_extensions(monkeypatch, tmp_path):
    _use_temp_workspace(monkeypatch, tmp_path)
    result = _fs.write_file("evil.sh", "#!/bin/bash\necho hacked")
    assert "bloqueada" in result.lower() or "erro" in result.lower()


def test_write_file_blocks_oversized_content(monkeypatch, tmp_path):
    _use_temp_workspace(monkeypatch, tmp_path)
    result = _fs.write_file("big.txt", "A" * 2_000_000)
    assert "limite" in result.lower() or "erro" in result.lower()


def test_write_file_requires_overwrite_flag_for_existing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(_fs.settings, "DRY_RUN", False)
    _use_temp_workspace(monkeypatch, tmp_path)
    first = _fs.write_file("notes.txt", "v1")
    assert "sucesso" in first.lower()
    second = _fs.write_file("notes.txt", "v2")
    assert "erro" in second.lower()


def test_read_file_blocks_path_outside_app_dir(monkeypatch, tmp_path):
    _use_temp_workspace(monkeypatch, tmp_path)
    result = _fs.read_file("../../../../../../../../../etc/shadow")
    assert "erro" in result.lower()


def test_list_directory_blocks_system_directories(monkeypatch, tmp_path):
    _use_temp_workspace(monkeypatch, tmp_path)
    result = _fs.list_directory("/etc")
    assert "acesso" in result.lower() or "negado" in result.lower() or "erro" in result.lower()


def test_x_user_id_is_never_an_authentication_source(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    req = _Req(headers={"X-User-Id": "99"})
    req.state.actor_user_id = None
    assert get_actor_user_id(req) is None
