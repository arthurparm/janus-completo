from __future__ import annotations

from typing import Any

from app.core.llm import ModelPriority, ModelRole
from app.services.chat.turn_core import (
    ChatTurnExecutor,
    ChatTurnFinalizer,
    ChatTurnPlanner,
    TurnBusinessState,
    TurnExecutionResult,
    TurnPlanningSignals,
    TurnRequest,
    TurnStrategy,
    build_routed_understanding,
)


def _request(**overrides: Any) -> TurnRequest:
    values: dict[str, Any] = {
        "conversation_id": "conv-1",
        "message": "hello",
        "role": ModelRole.ORCHESTRATOR,
        "priority": ModelPriority.FAST_AND_CHEAP,
        "user_id": "user-1",
        "project_id": "project-1",
    }
    values.update(overrides)
    return TurnRequest(**values)


def test_planner_is_pure_and_orders_static_grounding_secret_and_dynamic_candidates() -> None:
    planner = ChatTurnPlanner()
    signals = TurnPlanningSignals(
        understanding={"intent": "question"},
        light_chat_eligible=True,
        is_docs=True,
        citation_lookup_required=True,
    )

    plan = planner.plan(_request(), signals)

    assert plan.candidates == (
        TurnStrategy.STATIC_DOCS,
        TurnStrategy.DOCUMENT_GROUNDING,
        TurnStrategy.SECRET_RECALL,
        TurnStrategy.LIGHT_LLM,
    )
    assert plan.dynamic_strategy is TurnStrategy.LIGHT_LLM
    assert plan.requires_confirmation is False


def test_planner_blocks_tool_creation_and_marks_high_risk_before_execution() -> None:
    plan = ChatTurnPlanner().plan(
        _request(message="create tool"),
        TurnPlanningSignals(
            understanding={"intent": "action_request"},
            is_tool_request=True,
            is_explicit_tool_creation=True,
            risk_level="high",
        ),
    )

    assert plan.primary_strategy is TurnStrategy.HIGH_RISK_CONFIRMATION
    assert TurnStrategy.BLOCKED_TOOL_CREATION in plan.candidates
    assert plan.dynamic_strategy is TurnStrategy.AGENT_LOOP
    assert plan.requires_confirmation is True
    assert plan.confirmation_reason == "high_risk"


def test_static_executor_blocks_high_risk_without_calling_model() -> None:
    executor = ChatTurnExecutor(
        llm_service=object(),
        agent_loop=object(),
        prompt_service=object(),
        tool_service=None,
    )

    result = executor.execute_static(
        strategy=TurnStrategy.HIGH_RISK_CONFIRMATION,
        role=ModelRole.ORCHESTRATOR,
    )

    assert result.model == "high_risk_confirmation"
    assert "alto risco" in result.response


def test_routing_and_high_risk_understanding_are_transport_independent() -> None:
    class RoutingDecision:
        def to_dict(self) -> dict[str, Any]:
            return {"intent": "deployment", "risk_level": "high"}

    result = build_routed_understanding(
        {"intent": "action_request"},
        routing_decision=RoutingDecision(),
        requested_role="auto",
        selected_role=ModelRole.ORCHESTRATOR,
        route_applied=True,
        requires_confirmation=True,
        confirmation_reason="high_risk",
    )

    assert result["routing"] == {
        "requested_role": "auto",
        "selected_role": "orchestrator",
        "route_applied": True,
        "intent": "deployment",
        "risk_level": "high",
    }
    assert result["requires_confirmation"] is True
    assert result["confirmation_reason"] == "high_risk"


def test_typed_execution_round_trip_preserves_extension_metadata() -> None:
    execution = TurnExecutionResult.from_payload(
        strategy=TurnStrategy.DOCUMENT_GROUNDING,
        payload={
            "response": "grounded",
            "provider": "janus",
            "model": "document_grounding",
            "role": "orchestrator",
            "citations": [{"id": "c-1"}],
            "citation_status": {"status": "present", "count": 1},
            "knowledge_space_id": "space-1",
        },
        default_role=ModelRole.ORCHESTRATOR,
    )

    assert execution.to_payload()["knowledge_space_id"] == "space-1"
    assert execution.to_payload()["strategy"] == "document_grounding"


def test_finalizer_builds_one_typed_confirmation_and_agent_state() -> None:
    execution = TurnExecutionResult(
        strategy=TurnStrategy.AGENT_LOOP,
        response="Confirm before proceeding",
        provider="provider",
        model="model",
        role="orchestrator",
    )

    result = ChatTurnFinalizer().finalize(
        execution=execution,
        understanding={
            "intent": "action_request",
            "confidence": 0.91,
            "requires_confirmation": True,
            "confirmation_reason": "high_risk",
        },
        pending_action_id=42,
        confirmation_reason="high_risk",
    )

    assert result.business_state is TurnBusinessState.WAITING_CONFIRMATION
    assert result.delivery_status == "waiting_confirmation"
    assert result.confirmation == {
        "required": True,
        "reason": "high_risk",
        "source": "pending_actions_sql",
        "pending_action_id": 42,
        "approve_endpoint": "/api/v1/pending_actions/action/42/approve",
        "reject_endpoint": "/api/v1/pending_actions/action/42/reject",
    }
    assert result.agent_state == {
        "state": "waiting_confirmation",
        "confidence_band": "high",
        "requires_confirmation": True,
        "reason": "high_risk",
    }
