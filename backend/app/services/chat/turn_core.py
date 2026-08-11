from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from app.core.llm import ModelPriority, ModelRole
from app.services.chat.chat_contracts import (
    build_agent_state,
    build_confirmation_payload,
    normalize_understanding_payload,
)
from app.services.intent_routing_service import IntentRoutingDecision


class TurnStrategy(StrEnum):
    HIGH_RISK_CONFIRMATION = "high_risk_confirmation"
    COMMAND = "command"
    STATIC_DISCOVERY = "static_discovery"
    STATIC_DOCS = "static_docs"
    STATIC_CAPABILITIES = "static_capabilities"
    BLOCKED_TOOL_CREATION = "blocked_tool_creation"
    DOCUMENT_GROUNDING = "document_grounding"
    SECRET_RECALL = "secret_recall"
    LIGHT_LLM = "light_llm"
    AGENT_LOOP = "agent_loop"


STATIC_RESPONSE_STRATEGIES = frozenset(
    {
        TurnStrategy.STATIC_DISCOVERY,
        TurnStrategy.STATIC_DOCS,
        TurnStrategy.STATIC_CAPABILITIES,
    }
)

IMMEDIATE_TURN_STRATEGIES = frozenset(
    {
        TurnStrategy.HIGH_RISK_CONFIRMATION,
        TurnStrategy.COMMAND,
        *STATIC_RESPONSE_STRATEGIES,
        TurnStrategy.BLOCKED_TOOL_CREATION,
    }
)


@dataclass(frozen=True)
class TurnEffectsPolicy:
    """Application effects allowed after a turn has been planned."""

    persist_messages: bool = True
    summarize_conversation: bool = True
    index_user_message: bool = True
    index_assistant_message: bool = True
    consolidate_response: bool = True

    @classmethod
    def for_strategy(cls, strategy: TurnStrategy) -> "TurnEffectsPolicy":
        if strategy is TurnStrategy.COMMAND or strategy in STATIC_RESPONSE_STRATEGIES:
            return cls(
                persist_messages=True,
                summarize_conversation=True,
                index_user_message=False,
                index_assistant_message=False,
                consolidate_response=False,
            )
        return cls()


def infer_turn_strategy(payload: Mapping[str, Any]) -> TurnStrategy:
    raw = payload.get("strategy")
    if raw:
        try:
            return TurnStrategy(str(raw))
        except ValueError:
            pass
    by_model = {
        "discovery": TurnStrategy.STATIC_DISCOVERY,
        "tools_docs": TurnStrategy.STATIC_DOCS,
        "capabilities": TurnStrategy.STATIC_CAPABILITIES,
        "tool_creation": TurnStrategy.BLOCKED_TOOL_CREATION,
        "document_grounding": TurnStrategy.DOCUMENT_GROUNDING,
        "knowledge_space_pending": TurnStrategy.DOCUMENT_GROUNDING,
        "document_processing": TurnStrategy.DOCUMENT_GROUNDING,
        "secret_memory": TurnStrategy.SECRET_RECALL,
        "quick_command": TurnStrategy.COMMAND,
    }
    return by_model.get(str(payload.get("model") or ""), TurnStrategy.AGENT_LOOP)


class TurnBusinessState(StrEnum):
    PLANNED = "planned"
    COMPLETED = "completed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    PENDING_KNOWLEDGE_SPACE = "pending_knowledge_space"
    PENDING_STUDY = "pending_study"
    RUNNING_STUDY = "running_study"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TurnRequest:
    conversation_id: str
    message: str
    role: ModelRole
    priority: ModelPriority
    timeout_seconds: int | None = None
    user_id: str | None = None
    project_id: str | None = None
    knowledge_space_id: str | None = None
    identity_source: str = "unknown"
    requested_role: str | None = None


@dataclass(frozen=True)
class TurnPlanningSignals:
    understanding: Mapping[str, Any] | None
    light_chat_eligible: bool = False
    is_command: bool = False
    is_discovery: bool = False
    is_docs: bool = False
    is_capabilities: bool = False
    is_tool_request: bool = False
    is_explicit_tool_creation: bool = False
    citation_lookup_required: bool = False
    risk_level: str | None = None


@dataclass(frozen=True)
class TurnPlan:
    candidates: tuple[TurnStrategy, ...]
    dynamic_strategy: TurnStrategy
    citation_lookup_required: bool
    requires_confirmation: bool
    confirmation_reason: str | None

    @property
    def primary_strategy(self) -> TurnStrategy:
        return self.candidates[0]


def build_routed_understanding(
    understanding: Mapping[str, Any] | None,
    *,
    routing_decision: IntentRoutingDecision | None,
    requested_role: str | None,
    selected_role: ModelRole,
    route_applied: bool,
    requires_confirmation: bool = False,
    confirmation_reason: str | None = None,
) -> dict[str, Any]:
    """Attach routing and risk confirmation consistently for every transport."""

    resolved = deepcopy(dict(understanding or {}))
    if routing_decision is not None and hasattr(routing_decision, "to_dict"):
        resolved["routing"] = {
            "requested_role": requested_role,
            "selected_role": selected_role.value,
            "route_applied": bool(route_applied),
            **routing_decision.to_dict(),
        }
    if requires_confirmation:
        resolved["requires_confirmation"] = True
        resolved["confirmation_reason"] = confirmation_reason or "high_risk"
    return resolved


def normalize_command_understanding(
    understanding: Mapping[str, Any] | None,
    *,
    command: str,
) -> dict[str, Any]:
    """Mark a recognized quick command as deterministic, not low-confidence intent."""

    resolved = deepcopy(dict(understanding or {}))
    resolved.update(
        {
            "intent": "command",
            "confidence": 1.0,
            "summary": f"Comando Janus reconhecido: {command.strip().split(maxsplit=1)[0]}",
        }
    )
    resolved.pop("clarification_prompt", None)
    return resolved


class ChatTurnPlanner:
    """Pure strategy selection; all I/O is supplied as precomputed signals."""

    def plan(self, request: TurnRequest, signals: TurnPlanningSignals) -> TurnPlan:
        candidates: list[TurnStrategy] = []
        high_risk = str(signals.risk_level or "").strip().lower() == "high"
        if high_risk:
            candidates.append(TurnStrategy.HIGH_RISK_CONFIRMATION)
        if signals.is_command:
            candidates.append(TurnStrategy.COMMAND)
        if signals.is_discovery:
            candidates.append(TurnStrategy.STATIC_DISCOVERY)
        elif signals.is_docs:
            candidates.append(TurnStrategy.STATIC_DOCS)
        elif signals.is_tool_request and signals.is_explicit_tool_creation:
            candidates.append(TurnStrategy.BLOCKED_TOOL_CREATION)

        # Capability questions are conversational requests. Keep the legacy
        # static strategy readable for persisted turns, but never select it for
        # a new turn: the model must answer in the current conversation context.

        if request.knowledge_space_id or signals.citation_lookup_required:
            candidates.append(TurnStrategy.DOCUMENT_GROUNDING)
        candidates.append(TurnStrategy.SECRET_RECALL)

        dynamic_strategy = (
            TurnStrategy.LIGHT_LLM
            if self._should_use_light_chat(request=request, signals=signals)
            else TurnStrategy.AGENT_LOOP
        )
        candidates.append(dynamic_strategy)
        return TurnPlan(
            candidates=tuple(dict.fromkeys(candidates)),
            dynamic_strategy=dynamic_strategy,
            citation_lookup_required=bool(signals.citation_lookup_required),
            requires_confirmation=high_risk,
            confirmation_reason="high_risk" if high_risk else None,
        )

    @staticmethod
    def _should_use_light_chat(
        *,
        request: TurnRequest,
        signals: TurnPlanningSignals,
    ) -> bool:
        if request.role != ModelRole.ORCHESTRATOR:
            return False
        understanding = signals.understanding
        if not understanding or understanding.get("intent") not in {"general", "question"}:
            return False
        # The production adapter computes this compatibility signal using the
        # configured message-length limit before invoking the pure planner.
        return signals.light_chat_eligible


@dataclass(frozen=True)
class StaticChatResponse:
    """Transport-neutral result of a deterministic static chat query."""

    text: str
    model: str


def resolve_static_chat_response(
    *,
    strategy: TurnStrategy,
    prompt_service: Any,
    tool_service: Any | None,
) -> StaticChatResponse:
    """Resolve discovery, documentation, or capability replies in one place.

    The resolver owns only deterministic selection and rendering. Authentication,
    persistence, metrics, citations, and REST/SSE framing remain outside it.
    """

    if strategy is TurnStrategy.STATIC_DISCOVERY:
        response = prompt_service.render_discovery_intro(tool_service)
        model = "discovery"
    elif strategy is TurnStrategy.STATIC_DOCS:
        response = prompt_service.render_tools_documentation(tool_service)
        model = "tools_docs"
    elif strategy is TurnStrategy.STATIC_CAPABILITIES:
        response = prompt_service.render_local_capabilities()
        model = "capabilities"
    else:
        raise ValueError(f"Strategy is not a static chat response: {strategy.value}")
    normalized_response = str(response).strip()
    if not normalized_response:
        raise ValueError(f"Static response is empty: {strategy.value}")
    return StaticChatResponse(text=normalized_response, model=model)


class ChatTurnExecutor:
    """Executes a selected strategy behind the chat-domain boundary."""

    def __init__(
        self,
        *,
        llm_service: Any,
        agent_loop: Any,
        prompt_service: Any,
        tool_service: Any | None,
    ) -> None:
        self._llm = llm_service
        self._agent_loop = agent_loop
        self._prompt = prompt_service
        self._tools = tool_service

    def execute_static(
        self,
        *,
        strategy: TurnStrategy,
        role: ModelRole,
    ) -> "TurnExecutionResult":
        if strategy is TurnStrategy.HIGH_RISK_CONFIRMATION:
            return TurnExecutionResult(
                strategy=strategy,
                response=(
                    "Pedido classificado como alto risco. "
                    "Confirme o objetivo e o escopo antes de seguir."
                ),
                provider="janus",
                model="high_risk_confirmation",
                role=role.value,
            )
        if strategy in STATIC_RESPONSE_STRATEGIES:
            static_response = resolve_static_chat_response(
                strategy=strategy,
                prompt_service=self._prompt,
                tool_service=self._tools,
            )
            response = static_response.text
            model = static_response.model
        elif strategy is TurnStrategy.BLOCKED_TOOL_CREATION:
            from app.core.security.security_alerts import emit_security_alert

            emit_security_alert(
                "autonomous_evolution_attempt_blocked",
                {"capability": "chat_tool_creation"},
            )
            response = "Tool creation and autonomous code evolution are permanently disabled."
            model = "tool_creation"
        else:
            raise ValueError(f"Strategy is not static: {strategy.value}")
        response = str(response).strip()
        return TurnExecutionResult(
            strategy=strategy,
            response=response,
            provider="janus",
            model=model,
            role=role.value,
            citation_status={
                "mode": "optional",
                "status": "not_applicable",
                "count": 0,
                "reason": None,
            },
        )

    async def execute_dynamic(
        self,
        *,
        plan: TurnPlan,
        request: TurnRequest,
        prompt: str,
        persona: str,
    ) -> "TurnExecutionResult":
        if plan.dynamic_strategy is TurnStrategy.LIGHT_LLM:
            light_timeout_seconds = max(
                1,
                int(os.getenv("CHAT_LIGHT_TIMEOUT_SECONDS", str(request.timeout_seconds or 12))),
            )
            payload = await self._llm.invoke_llm(
                prompt=prompt,
                role=request.role,
                priority=request.priority,
                timeout_seconds=light_timeout_seconds,
                task_type="general_task",
                complexity="low",
                policy_overrides={
                    "role": request.role.value,
                    "priority": request.priority.value,
                    "timeout_seconds": light_timeout_seconds,
                },
                user_id=request.user_id,
                project_id=request.project_id,
            )
        else:
            payload = await self._agent_loop.run_loop(
                conversation_id=request.conversation_id,
                initial_prompt=prompt,
                persona=persona,
                message=request.message,
                role=request.role,
                priority=request.priority,
                timeout_seconds=request.timeout_seconds,
                user_id=request.user_id,
                project_id=request.project_id,
            )
        return TurnExecutionResult.from_payload(
            strategy=plan.dynamic_strategy,
            payload=payload,
            default_role=request.role,
        )


@dataclass
class TurnExecutionResult:
    strategy: TurnStrategy
    response: str
    provider: str
    model: str
    role: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    citation_status: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        *,
        strategy: TurnStrategy,
        payload: Mapping[str, Any],
        default_role: ModelRole,
    ) -> "TurnExecutionResult":
        known = {
            "response",
            "provider",
            "model",
            "role",
            "citations",
            "citation_status",
            "understanding",
            "confirmation",
            "agent_state",
            "delivery_status",
            "business_state",
            "failure_classification",
            "strategy",
        }
        citations = payload.get("citations")
        return cls(
            strategy=strategy,
            response=str(payload.get("response") or ""),
            provider=str(payload.get("provider") or "janus"),
            model=str(payload.get("model") or strategy.value),
            role=str(payload.get("role") or default_role.value),
            citations=deepcopy(citations) if isinstance(citations, list) else [],
            citation_status=(
                deepcopy(payload.get("citation_status"))
                if isinstance(payload.get("citation_status"), dict)
                else None
            ),
            metadata={key: deepcopy(value) for key, value in payload.items() if key not in known},
        )

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "response": self.response,
            "provider": self.provider,
            "model": self.model,
            "role": self.role,
            **deepcopy(self.metadata),
        }
        if self.citations or self.citation_status is not None:
            payload["citations"] = deepcopy(self.citations)
        if self.citation_status is not None:
            payload["citation_status"] = deepcopy(self.citation_status)
        payload["strategy"] = self.strategy.value
        return payload


@dataclass
class TurnResult:
    strategy: TurnStrategy
    business_state: TurnBusinessState
    response: str
    provider: str
    model: str
    role: str
    citations: list[dict[str, Any]]
    citation_status: dict[str, Any] | None
    understanding: dict[str, Any] | None
    confirmation: dict[str, Any] | None
    agent_state: dict[str, Any] | None
    delivery_status: str
    failure_classification: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "business_state": self.business_state.value,
            "response": self.response,
            "provider": self.provider,
            "model": self.model,
            "role": self.role,
            "citations": deepcopy(self.citations),
            "citation_status": deepcopy(self.citation_status),
            "understanding": deepcopy(self.understanding),
            "confirmation": deepcopy(self.confirmation),
            "agent_state": deepcopy(self.agent_state),
            "delivery_status": self.delivery_status,
            "failure_classification": self.failure_classification,
            **deepcopy(self.metadata),
        }


class ChatTurnFinalizer:
    """Shared, deterministic normalization of a completed execution."""

    def finalize(
        self,
        *,
        execution: TurnExecutionResult,
        understanding: Mapping[str, Any] | None,
        pending_action_id: int | None = None,
        confirmation_reason: str | None = None,
        business_state: TurnBusinessState = TurnBusinessState.COMPLETED,
        delivery_status: str | None = None,
        failure_classification: str | None = None,
        stream_phase: str | None = "completed",
    ) -> TurnResult:
        confirmation = build_confirmation_payload(
            pending_action_id=pending_action_id,
            reason=confirmation_reason,
        )
        normalized_understanding = normalize_understanding_payload(
            dict(understanding) if understanding is not None else None,
            confirmation=confirmation,
        )
        agent_understanding = normalized_understanding
        if execution.strategy in STATIC_RESPONSE_STRATEGIES and agent_understanding is not None:
            agent_understanding = deepcopy(agent_understanding)
            agent_understanding["low_confidence"] = False
        agent_state = build_agent_state(
            stream_phase=stream_phase,
            understanding=agent_understanding,
            confirmation=confirmation,
        )
        if confirmation and confirmation.get("required"):
            business_state = TurnBusinessState.WAITING_CONFIRMATION
        resolved_delivery = delivery_status or business_state.value
        return TurnResult(
            strategy=execution.strategy,
            business_state=business_state,
            response=execution.response,
            provider=execution.provider,
            model=execution.model,
            role=execution.role,
            citations=deepcopy(execution.citations),
            citation_status=deepcopy(execution.citation_status),
            understanding=normalized_understanding,
            confirmation=confirmation,
            agent_state=agent_state,
            delivery_status=resolved_delivery,
            failure_classification=failure_classification,
            metadata=deepcopy(execution.metadata),
        )
