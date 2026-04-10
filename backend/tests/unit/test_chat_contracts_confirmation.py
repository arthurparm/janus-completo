from app.services.chat.chat_contracts import (
    build_agent_state,
    build_confirmation_payload,
    extract_pending_action_id_from_text,
    maybe_create_fallback_pending_action,
    normalize_understanding_payload,
)


def test_build_confirmation_payload_requires_real_pending_action() -> None:
    assert build_confirmation_payload(pending_action_id=None, reason=None) is None
    assert build_confirmation_payload(pending_action_id=None, reason="None") is None
    assert build_confirmation_payload(pending_action_id=None, reason="high_risk") is None

    payload = build_confirmation_payload(pending_action_id=123, reason="high_risk")
    assert payload is not None
    assert payload["required"] is True
    assert payload["reason"] == "high_risk"
    assert payload["pending_action_id"] == 123


def test_normalize_understanding_clears_false_positive_confirmation() -> None:
    understanding = {
        "intent": "knowledge_query",
        "summary": "Onde está a documentação da API",
        "requires_confirmation": True,
        "confirmation_reason": None,
    }

    normalized = normalize_understanding_payload(understanding, confirmation=None)
    assert normalized is not None
    assert normalized["requires_confirmation"] is False
    assert "confirmation_reason" not in normalized

    agent_state = build_agent_state(understanding=normalized, confirmation=None)
    assert agent_state is None


def test_extract_pending_action_id_accepts_multiple_formats() -> None:
    assert extract_pending_action_id_from_text("Pending action id: 123") == 123
    assert extract_pending_action_id_from_text("pending_action_id: 456") == 456
    assert extract_pending_action_id_from_text("pending action id=789") == 789
    assert extract_pending_action_id_from_text("pending_action_id: clean_tmp_001") is None


def test_maybe_create_fallback_pending_action_from_pending_marker(monkeypatch) -> None:
    class FakePending:
        id = 42

    class FakeRepo:
        def create(self, **kwargs):
            assert kwargs["user_id"] == "9"
            assert kwargs["tool_name"] == "chat_high_risk_request"
            assert "chat_confirmation_fallback" in kwargs["args_json"]
            return FakePending()

    monkeypatch.setattr(
        "app.repositories.pending_action_repository.PendingActionRepository",
        lambda: FakeRepo(),
    )

    pending_id, reason = maybe_create_fallback_pending_action(
        message="gere uma acao pendente",
        assistant_response="pending_action_id: clean_tmp_001",
        conversation_id="conv-123",
        existing_pending_action_id=None,
        understanding={"intent": "action_request"},
    )

    assert pending_id == 42
    assert reason == "high_risk"


def test_maybe_create_fallback_pending_action_does_not_create_for_low_confidence_only() -> None:
    pending_id, reason = maybe_create_fallback_pending_action(
        message="explique a documentação da API",
        assistant_response="",
        conversation_id="conv-123",
        existing_pending_action_id=None,
        understanding={"requires_confirmation": True, "confirmation_reason": "low_confidence"},
    )

    assert pending_id is None
    assert reason == "low_confidence"
