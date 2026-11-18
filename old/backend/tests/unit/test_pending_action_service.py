import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from app.services.pending_action_service import (
    PendingActionService,
    extract_pending_action_id_from_text,
    get_pending_action_service,
)


class _Repo:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None
        self.status_call: tuple[int, str, str | None] | None = None

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.created = dict(kwargs)
        return SimpleNamespace(id=42)

    def get(self, action_id: int, user_id: str | None = None) -> SimpleNamespace:
        return SimpleNamespace(id=action_id, user_id=user_id)

    def list(self, status: str | None, limit: int, user_id: str | None) -> list[SimpleNamespace]:
        return [SimpleNamespace(status=status, limit=limit, user_id=user_id)]

    def set_status(
        self,
        action_id: int,
        status: str,
        user_id: str | None = None,
    ) -> SimpleNamespace:
        self.status_call = (action_id, status, user_id)
        return SimpleNamespace(id=action_id, status=status, user_id=user_id)


def _service(repo: _Repo) -> PendingActionService:
    return PendingActionService(repository_factory=lambda: repo)


def test_extract_pending_action_id_accepts_only_positive_numeric_formats() -> None:
    assert extract_pending_action_id_from_text("Pending action id: 123") == 123
    assert extract_pending_action_id_from_text("pending_action_id: 456") == 456
    assert extract_pending_action_id_from_text("pending action id=789") == 789
    assert extract_pending_action_id_from_text("pending_action_id: clean_tmp_001") is None
    assert extract_pending_action_id_from_text(None) is None


def test_create_validates_and_serializes_domain_payload() -> None:
    repo = _Repo()
    generated_at = datetime.now(timezone.utc)
    pending_id = _service(repo).create(
        user_id=" user-9 ",
        tool_name=" delete_records ",
        args={"target": "staging"},
        simulation_summary_json="{}",
        simulation_generated_at=generated_at,
        simulation_version="v1",
    )

    assert pending_id == 42
    assert repo.created is not None
    assert repo.created["user_id"] == "user-9"
    assert repo.created["tool_name"] == "delete_records"
    assert json.loads(str(repo.created["args_json"])) == {"target": "staging"}
    assert repo.created["simulation_generated_at"] == generated_at


def test_default_repository_factory_is_used_when_not_injected(monkeypatch) -> None:
    repo = _Repo()
    monkeypatch.setattr(
        "app.repositories.pending_action_repository.PendingActionRepository",
        lambda: repo,
    )

    pending_id = PendingActionService().create(
        user_id="user-1",
        tool_name="tool",
        args={},
    )

    assert pending_id == 42


@pytest.mark.parametrize(
    ("user_id", "tool_name", "error"),
    [(None, "tool", "persisted user_id"), ("user", " ", "tool_name")],
)
def test_create_rejects_invalid_identity_or_tool(
    user_id: str | None,
    tool_name: str,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        _service(_Repo()).create(user_id=user_id, tool_name=tool_name, args={})


def test_create_rejects_repository_result_without_durable_id() -> None:
    class InvalidRepo(_Repo):
        def create(self, **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(id=None)

    with pytest.raises(RuntimeError, match="durable id"):
        _service(InvalidRepo()).create(user_id="user", tool_name="tool", args={})


def test_resolve_chat_confirmation_persists_high_risk_action() -> None:
    repo = _Repo()
    pending_id, reason = _service(repo).resolve_chat_confirmation(
        message="delete production records",
        assistant_response="confirmation required",
        conversation_id="conv-1",
        user_id="user-1",
        understanding={"requires_confirmation": True, "confirmation_reason": "high_risk"},
    )

    assert (pending_id, reason) == (42, "high_risk")
    assert repo.created is not None
    payload = json.loads(str(repo.created["args_json"]))
    assert payload["source"] == "chat_confirmation_fallback"
    assert payload["conversation_id"] == "conv-1"


def test_resolve_chat_confirmation_reuses_existing_and_skips_low_confidence() -> None:
    repo = _Repo()
    service = _service(repo)
    assert service.resolve_chat_confirmation(
        message="delete production records",
        existing_pending_action_id=7,
        user_id="user-1",
        understanding={"confirmation_reason": "high_risk"},
    ) == (7, "high_risk")
    assert service.resolve_chat_confirmation(
        message="explain",
        understanding={"requires_confirmation": True, "confirmation_reason": "low_confidence"},
    ) == (None, "low_confidence")


def test_resolve_chat_confirmation_replaces_unowned_marker_with_owned_action() -> None:
    class MissingRepo(_Repo):
        def get(self, action_id: int, user_id: str | None = None):
            del action_id, user_id
            return None

    repo = MissingRepo()
    pending_id, reason = _service(repo).resolve_chat_confirmation(
        message="delete production records",
        assistant_response="Pending action id: 999",
        existing_pending_action_id=999,
        conversation_id="conv-1",
        user_id="user-1",
        understanding={"requires_confirmation": True, "confirmation_reason": "high_risk"},
    )

    assert (pending_id, reason) == (42, "high_risk")
    assert repo.created is not None


def test_management_methods_enforce_owner_bounds_and_statuses() -> None:
    repo = _Repo()
    service = _service(repo)

    assert service.get(action_id=42, user_id="user-1").user_id == "user-1"
    assert service.get_for_access_review(action_id=42).id == 42
    listed = service.list(user_id="user-1", status="pending", limit=999)
    assert listed[0].limit == 500
    updated = service.update_status(action_id=42, status="APPROVED", user_id="user-1")
    assert updated.status == "approved"
    assert repo.status_call == (42, "approved", "user-1")

    with pytest.raises(ValueError, match="invalid pending action status"):
        service.update_status(action_id=42, status="unknown", user_id="user-1")
    with pytest.raises(ValueError, match="positive integer"):
        service.get(action_id=0, user_id="user-1")
    with pytest.raises(ValueError, match="positive integer"):
        service.get(action_id=True, user_id="user-1")


def test_fastapi_dependency_factory_returns_domain_service() -> None:
    assert isinstance(get_pending_action_service(), PendingActionService)
