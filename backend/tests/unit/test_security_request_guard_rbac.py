from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.security.request_guard import require_admin_actor, require_same_user_or_admin
from app.repositories import user_repository


class _Req:
    def __init__(self, actor_user_id: str | int | None):
        self.state = SimpleNamespace(actor_user_id=actor_user_id)
        self.headers: dict[str, str] = {}


def test_require_admin_actor_allows_admin(monkeypatch):
    def fake_has_role(self, user_id: int, role_name: str) -> bool:
        return False

    def fake_is_admin(self, user_id: int) -> bool:
        assert user_id == 42
        return True

    monkeypatch.setattr(user_repository.UserRepository, "has_role", fake_has_role)
    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    assert require_admin_actor(_Req(actor_user_id=42)) == "42"


def test_require_admin_actor_blocks_non_admin(monkeypatch):
    def fake_has_role(self, user_id: int, role_name: str) -> bool:
        return False

    def fake_is_admin(self, user_id: int) -> bool:
        return False

    monkeypatch.setattr(user_repository.UserRepository, "has_role", fake_has_role)
    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    with pytest.raises(HTTPException) as exc:
        require_admin_actor(_Req(actor_user_id=42))

    assert exc.value.status_code == 403


def test_require_same_user_or_admin_allows_same_user(monkeypatch):
    def fake_is_admin(self, user_id: int) -> bool:
        raise AssertionError("is_admin should not be called")

    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    assert require_same_user_or_admin(_Req(actor_user_id=42), target_user_id=42) == "42"


def test_require_same_user_or_admin_allows_admin(monkeypatch):
    def fake_is_admin(self, user_id: int) -> bool:
        return True

    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    assert require_same_user_or_admin(_Req(actor_user_id=1), target_user_id=42) == "1"


def test_require_same_user_or_admin_blocks_non_admin(monkeypatch):
    def fake_is_admin(self, user_id: int) -> bool:
        return False

    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    with pytest.raises(HTTPException) as exc:
        require_same_user_or_admin(_Req(actor_user_id=1), target_user_id=42)

    assert exc.value.status_code == 403


def test_require_admin_actor_blocks_system_actor(monkeypatch):
    def fake_has_role(self, user_id: int, role_name: str) -> bool:
        return role_name == "SYSTEM"

    def fake_is_admin(self, user_id: int) -> bool:
        return True

    monkeypatch.setattr(user_repository.UserRepository, "has_role", fake_has_role)
    monkeypatch.setattr(user_repository.UserRepository, "is_admin", fake_is_admin)

    with pytest.raises(HTTPException) as exc:
        require_admin_actor(_Req(actor_user_id=42))

    assert exc.value.status_code == 403
