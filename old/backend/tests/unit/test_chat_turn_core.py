from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from app.core.llm import ModelPriority, ModelRole
from app.services.chat.turn_core import (
    IMMEDIATE_TURN_STRATEGIES,
    ChatTurnExecutor,
    ChatTurnFinalizer,
    ChatTurnPlanner,
    TurnBusinessState,
    TurnEffectsPolicy,
    TurnExecutionResult,
    TurnPlanningSignals,
    TurnRequest,
    TurnStrategy,
    build_routed_understanding,
    normalize_command_understanding,
    resolve_static_chat_response,
)
from app.services.prompt_builder_service import PromptBuilderService
from app.services.tool_service import ToolService


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


def test_command_is_an_immediate_non_indexed_turn() -> None:
    plan = ChatTurnPlanner().plan(
        _request(message="/about"),
        TurnPlanningSignals(
            understanding={"intent": "general"},
            is_command=True,
        ),
    )

    assert plan.primary_strategy is TurnStrategy.COMMAND
    assert TurnStrategy.COMMAND in IMMEDIATE_TURN_STRATEGIES
    assert TurnEffectsPolicy.for_strategy(TurnStrategy.COMMAND).index_user_message is False

    understanding = normalize_command_understanding(
        {"intent": "general", "confidence": 0.6, "clarification_prompt": "Explain"},
        command="/about",
    )
    assert understanding == {
        "intent": "command",
        "confidence": 1.0,
        "summary": "Comando Janus reconhecido: /about",
    }


@pytest.mark.asyncio
async def test_static_executor_blocks_high_risk_without_calling_model() -> None:
    executor = ChatTurnExecutor(
        llm_service=object(),
        agent_loop=object(),
        prompt_service=object(),
        tool_service=None,
    )

    result = await executor.execute_static(
        strategy=TurnStrategy.HIGH_RISK_CONFIRMATION,
        role=ModelRole.ORCHESTRATOR,
    )

    assert result.model == "high_risk_confirmation"
    assert "alto risco" in result.response


@pytest.mark.parametrize(
    ("strategy", "expected_text", "expected_model"),
    [
        (TurnStrategy.STATIC_DISCOVERY, "discovery", "discovery"),
        (TurnStrategy.STATIC_DOCS, "docs", "tools_docs"),
        (TurnStrategy.STATIC_CAPABILITIES, "capabilities", "capabilities"),
    ],
)
def test_resolve_static_chat_response_is_the_shared_deterministic_resolver(
    strategy: TurnStrategy,
    expected_text: str,
    expected_model: str,
) -> None:
    class Prompt:
        def render_discovery_intro(self, tools: object) -> str:
            assert tools is tool_service
            return " discovery "

        def render_tools_documentation(self, tools: object) -> str:
            assert tools is tool_service
            return " docs "

        def render_local_capabilities(self) -> str:
            return " capabilities "

    tool_service = object()
    resolved = resolve_static_chat_response(
        strategy=strategy,
        prompt_service=Prompt(),
        tool_service=tool_service,
    )

    assert resolved.text == expected_text
    assert resolved.model == expected_model


def test_resolve_static_chat_response_rejects_invalid_or_empty_rendering() -> None:
    class EmptyPrompt:
        def render_discovery_intro(self, tools: object) -> str:
            return " "

    with pytest.raises(ValueError, match="not a static chat response"):
        resolve_static_chat_response(
            strategy=TurnStrategy.AGENT_LOOP,
            prompt_service=EmptyPrompt(),
            tool_service=None,
        )
    with pytest.raises(ValueError, match="Static response is empty"):
        resolve_static_chat_response(
            strategy=TurnStrategy.STATIC_DISCOVERY,
            prompt_service=EmptyPrompt(),
            tool_service=None,
        )


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


@pytest.mark.parametrize(
    ("signals", "expected"),
    [
        (
            {"is_discovery": True, "is_docs": True, "is_capabilities": True},
            TurnStrategy.STATIC_DISCOVERY,
        ),
        (
            {"is_docs": True, "is_capabilities": True},
            TurnStrategy.STATIC_DOCS,
        ),
        ({"is_capabilities": True}, TurnStrategy.SECRET_RECALL),
        ({}, TurnStrategy.SECRET_RECALL),
    ],
)
def test_planner_preserves_discovery_and_docs_precedence_without_canned_capabilities(
    signals: dict[str, bool],
    expected: TurnStrategy,
) -> None:
    plan = ChatTurnPlanner().plan(
        _request(message="ambiguous request"),
        TurnPlanningSignals(
            understanding={"intent": "question"},
            light_chat_eligible=True,
            **signals,
        ),
    )

    assert plan.primary_strategy is expected
    if not signals or signals == {"is_capabilities": True}:
        assert plan.dynamic_strategy is TurnStrategy.LIGHT_LLM


class _ToolCatalog:
    def __init__(self, *, tools: list[Any] | None = None, docs: str = "tool docs") -> None:
        self.tools = tools or []
        self.docs = docs
        self.documentation_calls = 0

    def list_tools(self, *, category, permission_level, tags):
        return list(self.tools)

    def generate_documentation(self) -> str:
        self.documentation_calls += 1
        return self.docs


def _static_executor(catalog: Any) -> ChatTurnExecutor:
    return ChatTurnExecutor(
        llm_service=object(),
        agent_loop=object(),
        prompt_service=PromptBuilderService(),
        tool_service=catalog,
    )


@pytest.mark.parametrize(
    ("method_name", "message"),
    [
        ("is_capabilities_query", "what can you do"),
        ("is_tool_request", "create a tool"),
        ("is_script_request", "write a script"),
    ],
)
def test_prompt_builder_classifies_directly_from_canonical_intent(
    method_name: str,
    message: str,
) -> None:
    prompt_builder = PromptBuilderService()

    assert getattr(prompt_builder, method_name)(message) is True


def test_discovery_and_capabilities_detection_are_mutually_exclusive() -> None:
    prompt_builder = PromptBuilderService()

    assert prompt_builder.is_discovery_query("Quais ferramentas estão disponíveis?") is True
    assert prompt_builder.is_capabilities_query("Quais ferramentas estão disponíveis?") is False
    assert prompt_builder.is_discovery_query("O que você pode fazer?") is False
    assert prompt_builder.is_capabilities_query("O que você pode fazer?") is True
    assert prompt_builder.is_capabilities_query("Quais são suas capacidades?") is True
    assert prompt_builder.is_tool_request("Quais são suas capacidades?") is False


@pytest.mark.asyncio
async def test_prompt_builder_rejects_invalid_compiled_prompt(monkeypatch) -> None:
    class InvalidComposer:
        async def compose(self, intent, context):
            return SimpleNamespace(text="", modules_used=[], token_count=-1)

    monkeypatch.setattr(
        "app.services.prompt_composer_service.get_prompt_composer",
        lambda prompt_service: InvalidComposer(),
    )

    with pytest.raises(TypeError, match="text must be a non-empty string"):
        await PromptBuilderService().build_prompt(
            persona="assistant",
            history=[],
            new_user_message="hello",
            summary=None,
        )


@pytest.mark.parametrize(
    ("strategy", "model", "expected_text"),
    [
        (TurnStrategy.STATIC_DISCOVERY, "discovery", "alpha"),
        (TurnStrategy.STATIC_DOCS, "tools_docs", "canonical docs"),
        (TurnStrategy.STATIC_CAPABILITIES, "capabilities", "analisar código"),
    ],
)
@pytest.mark.asyncio
async def test_group2_static_execution_has_canonical_completed_shape(
    strategy: TurnStrategy,
    model: str,
    expected_text: str,
) -> None:
    catalog = _ToolCatalog(
        tools=[SimpleNamespace(name="alpha")],
        docs="canonical docs",
    )

    execution = await _static_executor(catalog).execute_static(
        strategy=strategy,
        role=ModelRole.ORCHESTRATOR,
    )
    finalized = ChatTurnFinalizer().finalize(
        execution=execution,
        understanding={"intent": "question", "confidence": 0.8},
    )

    assert expected_text in execution.response
    assert execution.provider == "janus"
    assert execution.model == model
    assert execution.role == ModelRole.ORCHESTRATOR.value
    assert execution.citations == []
    assert execution.citation_status == {
        "mode": "optional",
        "status": "not_applicable",
        "count": 0,
        "reason": None,
    }
    assert finalized.delivery_status == "completed"
    assert finalized.confirmation is None
    assert finalized.agent_state == {
        "state": "completed",
        "confidence_band": "high",
    }


@pytest.mark.asyncio
async def test_docs_delegates_once_without_placeholder_and_preserves_empty_catalog_text() -> None:
    catalog = _ToolCatalog(docs="# Homologated production tools\n\nNo tools registered.")

    result = await _static_executor(catalog).execute_static(
        strategy=TurnStrategy.STATIC_DOCS,
        role=ModelRole.ORCHESTRATOR,
    )

    assert catalog.documentation_calls == 1
    assert result.response == "# Homologated production tools\n\nNo tools registered."
    assert "Documentação detalhada das ferramentas: ..." not in result.response


@pytest.mark.parametrize("documentation", [None, "", "   "])
@pytest.mark.asyncio
async def test_docs_rejects_missing_or_empty_canonical_documentation(documentation: Any) -> None:
    catalog = _ToolCatalog(docs=documentation)

    with pytest.raises(RuntimeError, match="documentation is empty"):
        await _static_executor(catalog).execute_static(
            strategy=TurnStrategy.STATIC_DOCS,
            role=ModelRole.ORCHESTRATOR,
        )

    assert catalog.documentation_calls == 1


class _ToolRepository:
    def __init__(self, tools: list[Any]) -> None:
        self.tools = tools
        self.find_all_calls = 0

    def find_all(self, category, permission_level, tags):
        self.find_all_calls += 1
        return list(self.tools)

    def get_all_statistics(self) -> dict[str, int]:
        return {"total_tools_registered": len(self.tools)}

    def find_by_name(self, tool_name: str) -> Any | None:
        return next(
            (tool for tool in self.tools if getattr(tool, "name", None) == tool_name),
            None,
        )

    def get_all_categories(self) -> list[str]:
        return []

    def get_all_permissions(self) -> list[str]:
        return []


def test_tool_service_rejects_incomplete_repository_contract() -> None:
    with pytest.raises(TypeError, match="catalog contract"):
        ToolService(SimpleNamespace())


def test_canonical_tool_documentation_renders_valid_metadata_and_empty_catalog() -> None:
    metadata = SimpleNamespace(
        name="alpha",
        description="Alpha description",
        permission_level=SimpleNamespace(value="read"),
        namespace="janus",
    )
    populated_repo = _ToolRepository([metadata])
    empty_repo = _ToolRepository([])

    populated = ToolService(populated_repo).generate_documentation()
    empty = ToolService(empty_repo).generate_documentation()

    assert "## alpha" in populated
    assert "Alpha description" in populated
    assert "Permission: `read`" in populated
    assert "Namespace: `janus`" in populated
    assert populated_repo.find_all_calls == 1
    assert "No homologated tools are currently registered." in empty
    assert empty_repo.find_all_calls == 1


def test_canonical_tool_documentation_propagates_repository_failure() -> None:
    class FailingRepository(_ToolRepository):
        def find_all(self, category, permission_level, tags):
            raise RuntimeError("repository unavailable")

    with pytest.raises(RuntimeError, match="repository unavailable"):
        ToolService(FailingRepository([])).generate_documentation()


@pytest.mark.asyncio
async def test_discovery_skips_invalid_metadata_without_losing_valid_catalog_items() -> None:
    catalog = _ToolCatalog(
        tools=[SimpleNamespace(description="missing name"), SimpleNamespace(name="alpha")]
    )

    result = await _static_executor(catalog).execute_static(
        strategy=TurnStrategy.STATIC_DISCOVERY,
        role=ModelRole.ORCHESTRATOR,
    )

    assert "alpha" in result.response


@pytest.mark.asyncio
async def test_discovery_distinguishes_empty_catalog_from_repository_failure() -> None:
    empty = await _static_executor(_ToolCatalog()).execute_static(
        strategy=TurnStrategy.STATIC_DISCOVERY,
        role=ModelRole.ORCHESTRATOR,
    )

    class FailingCatalog(_ToolCatalog):
        def list_tools(self, *, category, permission_level, tags):
            raise RuntimeError("repository unavailable")

    assert "catálogo homologado de ferramentas está vazio" in empty.response
    with pytest.raises(RuntimeError, match="repository unavailable"):
        await _static_executor(FailingCatalog()).execute_static(
            strategy=TurnStrategy.STATIC_DISCOVERY,
            role=ModelRole.ORCHESTRATOR,
        )


@pytest.mark.asyncio
async def test_static_finalizer_reports_completion_even_when_understanding_is_low_confidence() -> None:
    execution = await _static_executor(_ToolCatalog()).execute_static(
        strategy=TurnStrategy.STATIC_CAPABILITIES,
        role=ModelRole.ORCHESTRATOR,
    )

    result = ChatTurnFinalizer().finalize(
        execution=execution,
        understanding={"intent": "general", "confidence": 0.6},
    )

    assert result.understanding["low_confidence"] is True
    assert result.agent_state["state"] == "completed"


@pytest.mark.parametrize("strategy", tuple(TurnStrategy))
def test_effect_policy_changes_only_group2_static_strategies(strategy: TurnStrategy) -> None:
    policy = TurnEffectsPolicy.for_strategy(strategy)

    assert policy.persist_messages is True
    assert policy.summarize_conversation is True
    if strategy in {
        TurnStrategy.COMMAND,
        TurnStrategy.STATIC_DISCOVERY,
        TurnStrategy.STATIC_DOCS,
        TurnStrategy.STATIC_CAPABILITIES,
    }:
        assert policy.index_user_message is False
        assert policy.index_assistant_message is False
        assert policy.consolidate_response is False
    else:
        assert policy.index_user_message is True
        assert policy.index_assistant_message is True
        assert policy.consolidate_response is True
