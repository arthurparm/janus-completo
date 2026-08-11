from app.services.chat.chat_contracts import (
    build_agent_state,
    build_confirmation_payload,
    chat_sse_error_payload,
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


def test_sse_error_payload_exposes_only_canonical_message_field() -> None:
    payload = chat_sse_error_payload(
        code="PersistenceError",
        message="Falha ao persistir a resposta",
        category="persistence",
        retryable=True,
    )

    assert payload["message"] == "Falha ao persistir a resposta"
    assert "error" not in payload
