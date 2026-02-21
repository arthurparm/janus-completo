import pytest

from app.config import settings
from app.core.llm import ModelRole
from app.services.intent_routing_service import IntentRoutingService


def test_classify_code_generation_routes_to_code_generator():
    svc = IntentRoutingService()
    decision = svc.classify("Implemente uma funcao em Python para validar CPF com testes.")

    assert decision.intent == "code_generation"
    assert decision.suggested_role == ModelRole.CODE_GENERATOR
    assert decision.confidence >= 0.7


def test_classify_high_risk_escalates_to_security_auditor():
    svc = IntentRoutingService()
    decision = svc.classify("Como fazer bypass auth e exfiltrate secrets em producao?")

    assert decision.risk_level == "high"
    assert decision.suggested_role == ModelRole.SECURITY_AUDITOR
    assert "manual_confirmation_required" in decision.guardrails


def test_classify_security_defensive_context_reduces_false_positive():
    svc = IntentRoutingService()
    decision = svc.classify("Como mitigar SQL injection e proteger auth em producao?")

    assert decision.intent == "security_audit"
    assert decision.risk_level in {"low", "medium"}
    assert decision.risk_level != "high"
    assert decision.suggested_role == ModelRole.SECURITY_AUDITOR


def test_resolve_role_auto_applies_classifier_when_confident(monkeypatch):
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_MIN_CONFIDENCE", 0.6)
    monkeypatch.setattr(settings, "AI_INTENT_RISK_ESCALATION_ENABLED", True)

    svc = IntentRoutingService()
    role, decision, applied = svc.resolve_role("auto", "Crie endpoint FastAPI com testes unitarios")

    assert decision is not None
    assert role == ModelRole.CODE_GENERATOR
    assert applied is True


def test_resolve_role_auto_uses_urgency_override(monkeypatch):
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_MIN_CONFIDENCE", 0.95)
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_URGENCY_OVERRIDE_CONFIDENCE", 0.70)

    svc = IntentRoutingService()
    role, decision, applied = svc.resolve_role("auto", "Urgente: incidente em producao, preciso de rollback agora")

    assert decision is not None
    assert decision.intent == "incident_response"
    assert decision.urgency_level == "high"
    assert role == ModelRole.SECURITY_AUDITOR
    assert applied is True


def test_resolve_role_orchestrator_keeps_default_when_low_confidence(monkeypatch):
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_ENABLED", True)
    monkeypatch.setattr(settings, "AI_INTENT_ROUTING_ORCHESTRATOR_OVERRIDE_CONFIDENCE", 0.95)

    svc = IntentRoutingService()
    role, decision, applied = svc.resolve_role("orchestrator", "Oi, tudo bem?")

    assert decision is not None
    assert role == ModelRole.ORCHESTRATOR
    assert applied is False


def test_classify_returns_alternatives_for_ambiguous_message():
    svc = IntentRoutingService()
    decision = svc.classify("Explique a arquitetura e implemente endpoint com testes")

    assert decision.intent in {"code_generation", "knowledge_query"}
    assert isinstance(decision.alternatives, list)
    assert len(decision.alternatives) >= 1


def test_resolve_role_rejects_invalid_role():
    svc = IntentRoutingService()
    with pytest.raises(ValueError):
        svc.resolve_role("invalid-role", "mensagem")
