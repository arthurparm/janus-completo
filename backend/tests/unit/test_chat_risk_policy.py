import pytest
from app.services.chat.risk_policy import (
    evaluate_confirmation_risk,
    normalize_confirmation_reason,
    summarize_confirmation_risk,
)


@pytest.mark.parametrize("value", [None, "", "  ", "None", "NULL", "undefined"])
def test_normalize_confirmation_reason_rejects_empty_sentinels(value: object) -> None:
    assert normalize_confirmation_reason(value) is None


def test_normalize_confirmation_reason_preserves_meaningful_value() -> None:
    assert normalize_confirmation_reason(" high_risk ") == "high_risk"


def test_risk_policy_detects_high_risk_message_without_side_effects() -> None:
    result = evaluate_confirmation_risk(
        message="execute deploy in production",
        understanding={"requires_confirmation": True},
    )

    assert result.requires_pending_action is True
    assert result.reason == "high_risk"
    assert result.high_risk_signal is True
    assert result.pending_marker_signal is False


def test_risk_policy_detects_non_numeric_pending_marker() -> None:
    result = evaluate_confirmation_risk(
        message="prepare a ação",
        assistant_response="pending_action_id: clean_tmp_001",
        understanding={"intent": "action_request"},
    )

    assert result.requires_pending_action is True
    assert result.pending_marker_signal is True


def test_risk_policy_does_not_persist_low_confidence_only() -> None:
    result = evaluate_confirmation_risk(
        message="explique a documentação",
        understanding={"requires_confirmation": True, "confirmation_reason": "low_confidence"},
    )

    assert result.requires_pending_action is False
    assert result.reason == "low_confidence"


def test_risk_policy_reuses_existing_pending_action() -> None:
    result = evaluate_confirmation_risk(
        message="delete production data",
        existing_pending_action_id=42,
        understanding={"requires_confirmation": True, "confirmation_reason": "high_risk"},
    )

    assert result.requires_pending_action is False
    assert result.reason == "high_risk"


def test_summarize_confirmation_risk_preserves_explicit_risk() -> None:
    explicit = {"level": "critical", "source": "policy"}
    assert summarize_confirmation_risk(
        understanding={"risk": explicit},
        confirmation=None,
    ) == explicit

    with pytest.raises(TypeError, match="non-string key"):
        summarize_confirmation_risk(
            understanding={"risk": {1: "invalid"}},
            confirmation=None,
        )


@pytest.mark.parametrize(
    ("understanding", "confirmation", "expected_level", "expected_text"),
    [
        (
            {"requires_confirmation": True, "confirmation_reason": "high_risk"},
            {"required": True},
            "high",
            "alto risco",
        ),
        (
            {"requires_confirmation": True, "confirmation_reason": "low_confidence"},
            {"required": True},
            "medium",
            "Baixa confiança",
        ),
        ({}, {"required": True}, "low", "requer confirmação"),
    ],
)
def test_summarize_confirmation_risk_builds_deterministic_summary(
    understanding: dict[str, object],
    confirmation: dict[str, object],
    expected_level: str,
    expected_text: str,
) -> None:
    result = summarize_confirmation_risk(
        understanding=understanding,
        confirmation=confirmation,
    )
    assert result is not None
    assert result["level"] == expected_level
    assert expected_text in result["summary"]


def test_summarize_confirmation_risk_returns_none_without_signals() -> None:
    assert summarize_confirmation_risk(understanding=None, confirmation=None) is None
    assert summarize_confirmation_risk(understanding={}, confirmation=None) is None
