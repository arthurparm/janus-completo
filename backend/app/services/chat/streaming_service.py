from __future__ import annotations

import asyncio
import json
import os
import time as _time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog
from app.core.exceptions.chat_exceptions import ChatServiceError
from app.core.llm import ModelPriority, ModelRole
from app.core.llm.pricing import _provider_pricing
from app.core.monitoring.chat_metrics import (
    CHAT_ERRORS_TOTAL,
    CHAT_LATENCY_SECONDS,
    CHAT_MESSAGES_TOTAL,
    CHAT_SPEND_USD_TOTAL,
    CHAT_TOKENS_TOTAL,
    CHAT_TTFT_SECONDS,
)
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.services.chat.chat_citation_service import (
    build_citation_status,
    build_missing_citation_resolution,
    collect_chat_citations,
    collect_chat_citations_with_deadline,
)
from app.services.chat.chat_contracts import (
    build_confirmation_payload,
    chat_sse_error_payload,
    extract_pending_action_id_from_text,
    maybe_create_fallback_pending_action,
    normalize_understanding_payload,
)
from app.services.chat.conversation_service import ConversationService
from app.services.chat.message_helpers import (
    build_understanding_payload,
    split_ui,
)
from app.services.chat.repository_port import AsyncChatRepositoryPort
from app.services.chat.turn_core import (
    IMMEDIATE_TURN_STRATEGIES,
    STATIC_RESPONSE_STRATEGIES,
    TurnBusinessState,
    TurnEffectsPolicy,
    TurnExecutionResult,
    TurnRequest,
    TurnStrategy,
    build_routed_understanding,
)
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService

if TYPE_CHECKING:
    from app.services.chat.message_orchestration_service import MessageOrchestrationService

logger = structlog.get_logger(__name__)


class StreamingService:
    def __init__(
        self,
        *,
        repo: ChatRepository,
        llm_service: Any,
        tool_service: Any | None,
        prompt_service: PromptBuilderService,
        rag_service: RAGService | None,
        conversation_service: ConversationService,
        message_orchestration_service: MessageOrchestrationService,
        study_job_service: Any | None = None,
    ):
        self._repo = repo
        self._repo_io = AsyncChatRepositoryPort(repo)
        self._llm = llm_service
        self._tools = tool_service
        self._prompt_service = prompt_service
        self._rag_service = rag_service
        self._conversation_service = conversation_service
        self._message_orchestration_service = message_orchestration_service
        self._study_jobs = study_job_service

    async def stream_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole | None = None,
        priority: ModelPriority | None = None,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        knowledge_space_id: str | None = None,
        identity_source: str = "unknown",
        requested_role: str | None = None,
        routing_decision: Any | None = None,
        route_applied: bool | None = None,
    ) -> AsyncIterator[str]:
        role = role or ModelRole.ORCHESTRATOR
        priority = priority or ModelPriority.HIGH_QUALITY

        max_bytes = int(os.getenv("CHAT_MAX_MESSAGE_BYTES", str(10 * 1024)))
        heartbeat_interval = int(os.getenv("CHAT_HEARTBEAT_INTERVAL_SECONDS", "30"))
        protocol_version = os.getenv("CHAT_SSE_PROTOCOL_VERSION", "2025-11.v1")
        deprecate_partial_at = os.getenv("CHAT_SSE_PARTIAL_DEPRECATE_AT", "2026-03-01")

        try:
            if message and len(message.encode("utf-8")) > max_bytes:
                err = json.dumps(
                    chat_sse_error_payload(
                        code="CHAT_MESSAGE_TOO_LARGE",
                        message="Message too large",
                        category="validation",
                        retryable=False,
                        http_status=413,
                    ),
                    ensure_ascii=False,
                )
                yield f"event: error\ndata: {err}\n\n"
                return
        except Exception:
            pass

        understanding = build_understanding_payload(message)
        turn_request = TurnRequest(
            conversation_id=conversation_id,
            message=message,
            role=role,
            priority=priority,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            knowledge_space_id=knowledge_space_id,
            identity_source=identity_source,
            requested_role=requested_role,
        )
        turn_plan = self._message_orchestration_service.build_turn_plan(
            request=turn_request,
            understanding=understanding,
            routing_decision=routing_decision,
        )
        use_light_chat = turn_plan.dynamic_strategy is TurnStrategy.LIGHT_LLM
        citation_lookup_required = turn_plan.citation_lookup_required
        try:
            conv = await self._repo_io.get_conversation(conversation_id)
            self._conversation_service.validate_conversation_access(
                conversation_id, conv, user_id, project_id
            )
        except ChatRepositoryError:
            err = json.dumps(
                chat_sse_error_payload(
                    code="CHAT_CONVERSATION_NOT_FOUND",
                    message="Conversation not found",
                    category="not_found",
                    retryable=False,
                    http_status=404,
                ),
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {err}\n\n"
            return
        except ChatServiceError as e:
            err = json.dumps(
                chat_sse_error_payload(
                    code="CHAT_ACCESS_DENIED",
                    message=str(e),
                    category="authz",
                    retryable=False,
                    http_status=403,
                ),
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {err}\n\n"
            return

        start_t_overall = _time.time()
        start_t = start_t_overall
        trace_id = uuid4().hex
        try:
            logger.info(
                "chat.stream", stage="start", conversation_id=conversation_id, trace_id=trace_id
            )
        except Exception:
            pass

        yield "event: start\n\n"
        proto = json.dumps(
            {
                "version": protocol_version,
                "supports_partial": True,
                "deprecate_partial_at": deprecate_partial_at,
            },
            ensure_ascii=False,
        )
        yield f"event: protocol\ndata: {proto}\n\n"

        await self._repo_io.add_message(conversation_id, role="user", text=message)
        CHAT_MESSAGES_TOTAL.labels(role="user", outcome="accepted").inc()
        self._message_orchestration_service.schedule_active_memory_capture(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
        )
        ack = json.dumps({"conversation_id": conversation_id}, ensure_ascii=False)
        yield f"event: ack\ndata: {ack}\n\n"
        yield (
            "event: cognitive_status\ndata: "
            + json.dumps(
                {"state": "thinking", "timestamp": int(_time.time() * 1000)},
                ensure_ascii=False,
            )
            + "\n\n"
        )

        if turn_plan.primary_strategy in IMMEDIATE_TURN_STRATEGIES:
            immediate_strategy = turn_plan.primary_strategy
            effects = TurnEffectsPolicy.for_strategy(immediate_strategy)

            if immediate_strategy in STATIC_RESPONSE_STRATEGIES:
                async def _complete_static_turn() -> tuple[
                    TurnExecutionResult,
                    Any,
                    dict[str, Any],
                ]:
                    execution = await self._message_orchestration_service.execute_static_turn(
                        strategy=immediate_strategy,
                        role=role,
                    )
                    result_understanding = build_routed_understanding(
                        understanding,
                        routing_decision=routing_decision,
                        requested_role=requested_role,
                        selected_role=role,
                        route_applied=bool(route_applied),
                    )
                    finalized = self._message_orchestration_service.finalize_turn(
                        execution=execution,
                        understanding=result_understanding,
                        delivery_status="completed",
                    )
                    finalized_payload = finalized.to_payload()
                    saved_message = (
                        await self._message_orchestration_service.persist_finalized_turn(
                            conversation_id=conversation_id,
                            user_message=message,
                            result=finalized_payload,
                            user_id=user_id,
                            project_id=project_id,
                            identity_source=identity_source,
                            role=role,
                            priority=priority,
                        )
                    )
                    return execution, finalized, saved_message

                try:
                    if not effects.persist_messages:
                        raise RuntimeError("Static response persistence is disabled")
                    static_task = asyncio.create_task(_complete_static_turn())
                    if heartbeat_interval and heartbeat_interval > 0:
                        while True:
                            static_completed_tasks, _ = await asyncio.wait(
                                {static_task},
                                timeout=max(1, heartbeat_interval),
                            )
                            if static_completed_tasks:
                                break
                            heartbeat = json.dumps(
                                {"timestamp": int(_time.time() * 1000)},
                                ensure_ascii=False,
                            )
                            yield f"event: heartbeat\ndata: {heartbeat}\n\n"
                    execution, finalized, saved_message = await static_task
                except Exception as exc:
                    CHAT_MESSAGES_TOTAL.labels(role="assistant", outcome="error").inc()
                    CHAT_ERRORS_TOTAL.labels(code="InvocationError").inc()
                    logger.error(
                        "chat_static_stream_failed",
                        conversation_id=conversation_id,
                        strategy=immediate_strategy.value,
                        error_type=type(exc).__name__,
                    )
                    error_payload = json.dumps(
                        chat_sse_error_payload(
                            code="CHAT_INVOCATION_ERROR",
                            message="Static response unavailable",
                            category="internal",
                            retryable=True,
                        ),
                        ensure_ascii=False,
                    )
                    yield f"event: error\ndata: {error_payload}\n\n"
                    return

                assistant_text = finalized.response
                first_token = True
                for i in range(0, len(assistant_text), 256):
                    token_payload = json.dumps(
                        {
                            "text": assistant_text[i : i + 256],
                            "timestamp": int(_time.time() * 1000),
                        },
                        ensure_ascii=False,
                    )
                    if first_token:
                        CHAT_TTFT_SECONDS.labels(
                            provider=finalized.provider,
                            model=finalized.model,
                        ).observe(max(0.0, _time.time() - start_t_overall))
                        first_token = False
                    yield f"event: token\ndata: {token_payload}\n\n"
                    yield f"event: partial\ndata: {token_payload}\n\n"

                static_done_payload: dict[str, Any] = {
                    "conversation_id": conversation_id,
                    "message_id": (
                        str(saved_message.get("id"))
                        if isinstance(saved_message, dict)
                        else None
                    ),
                    "provider": finalized.provider,
                    "model": finalized.model,
                    "citations": finalized.citations,
                    "citation_status": finalized.citation_status,
                    "understanding": finalized.understanding,
                    "confirmation": finalized.confirmation,
                    "agent_state": finalized.agent_state,
                    "delivery_status": finalized.delivery_status,
                }
                yield (
                    "event: done\ndata: "
                    + json.dumps(static_done_payload, ensure_ascii=False)
                    + "\n\n"
                )
                return

            execution = await self._message_orchestration_service.execute_static_turn(
                strategy=immediate_strategy,
                role=role,
            )
            result_understanding = build_routed_understanding(
                understanding,
                routing_decision=routing_decision,
                requested_role=requested_role,
                selected_role=role,
                route_applied=bool(route_applied),
                requires_confirmation=turn_plan.requires_confirmation,
                confirmation_reason=turn_plan.confirmation_reason,
            )
            pending_action_id, fallback_reason = maybe_create_fallback_pending_action(
                message=message,
                assistant_response=execution.response,
                conversation_id=conversation_id,
                user_id=str(user_id) if user_id is not None else None,
                existing_pending_action_id=None,
                understanding=result_understanding,
            )
            confirmation_reason = (
                result_understanding.get("confirmation_reason") or fallback_reason
            )
            confirmation_payload = build_confirmation_payload(
                pending_action_id=pending_action_id,
                reason=str(confirmation_reason) if confirmation_reason else None,
            )
            delivery_status = (
                "waiting_confirmation"
                if confirmation_payload and confirmation_payload.get("required")
                else "completed"
            )
            if execution.citation_status is None:
                execution.citation_status = build_citation_status(
                    message=message,
                    citations=[],
                )
            finalized = self._message_orchestration_service.finalize_turn(
                execution=execution,
                understanding=result_understanding,
                pending_action_id=pending_action_id,
                confirmation_reason=(
                    str(confirmation_reason) if confirmation_reason else None
                ),
                delivery_status=delivery_status,
            )
            assistant_text = execution.response
            for i in range(0, len(assistant_text), 256):
                token_payload = json.dumps(
                    {
                        "text": assistant_text[i : i + 256],
                        "timestamp": int(_time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                yield f"event: token\ndata: {token_payload}\n\n"
                yield f"event: partial\ndata: {token_payload}\n\n"
            saved_message = await self._repo_io.add_message(
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "citations": finalized.citations,
                    "citation_status": finalized.citation_status,
                    "understanding": finalized.understanding,
                    "confirmation": finalized.confirmation,
                    "agent_state": finalized.agent_state,
                    "delivery_status": finalized.delivery_status,
                    "provider": finalized.provider,
                    "model": finalized.model,
                },
            )
            immediate_done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "message_id": (
                    str(saved_message.get("id")) if isinstance(saved_message, dict) else None
                ),
                "provider": finalized.provider,
                "model": finalized.model,
                "citations": finalized.citations,
                "citation_status": finalized.citation_status,
                "understanding": finalized.understanding,
                "confirmation": finalized.confirmation,
                "agent_state": finalized.agent_state,
                "delivery_status": finalized.delivery_status,
            }
            if (finalized.agent_state or {}).get("state") == "waiting_confirmation":
                yield (
                    "event: cognitive_status\ndata: "
                    + json.dumps(
                        {
                            "state": "waiting_confirmation",
                            "requires_confirmation": True,
                            "reason": (finalized.confirmation or {}).get("reason"),
                            "timestamp": int(_time.time() * 1000),
                        },
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )
            yield (
                "event: done\ndata: "
                + json.dumps(immediate_done_payload, ensure_ascii=False)
                + "\n\n"
            )
            return

        try:
            runtime_notice = self._message_orchestration_service.build_knowledge_space_runtime_notice(
                conversation_id=conversation_id,
                message=message,
                user_id=user_id,
                requested_knowledge_space_id=knowledge_space_id,
            )
        except Exception:
            runtime_notice = None
        if runtime_notice and runtime_notice.get("processing_notice"):
            yield (
                "event: cognitive_status\ndata: "
                + json.dumps(
                    {
                        "state": "knowledge_wait_estimate",
                        "reason": str(runtime_notice.get("processing_notice") or ""),
                        "timestamp": int(_time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )

        grounded_result = None
        if knowledge_space_id or citation_lookup_required:
            grounded_result = await self._message_orchestration_service.generate_document_grounded_reply(
                conversation_id=conversation_id,
                message=message,
                role=role,
                priority=priority,
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                project_id=project_id,
                requested_knowledge_space_id=knowledge_space_id,
                understanding=understanding,
            )
        if grounded_result is not None:
            assistant_text = str(grounded_result.get("response") or "")
            grounded_citations = grounded_result.get("citations") or []
            citation_status = grounded_result.get("citation_status") or build_citation_status(
                message=message,
                citations=grounded_citations,
            )
            if citation_status.get("status") == "missing_required":
                grounded_result.update(
                    build_missing_citation_resolution(
                        active_knowledge_space_id=(
                            grounded_result.get("knowledge_space_id")
                            or knowledge_space_id
                        ),
                        retrieval_reason=citation_status.get("reason"),
                    )
                )
                assistant_text = str(grounded_result["response"])
            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)},
                    ensure_ascii=False,
                )
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        CHAT_TTFT_SECONDS.labels(
                            provider=str(grounded_result.get("provider") or "janus"),
                            model=str(grounded_result.get("model") or "document_grounding"),
                        ).observe(ttft_ms / 1000.0)
                    except Exception:
                        pass

            grounded_execution = TurnExecutionResult.from_payload(
                strategy=TurnStrategy.DOCUMENT_GROUNDING,
                payload=grounded_result,
                default_role=role,
            )
            grounded_delivery = str(
                grounded_result.get("delivery_status") or "completed"
            )
            grounded_business_state = (
                TurnBusinessState.PENDING_KNOWLEDGE_SPACE
                if grounded_delivery == "pending_knowledge_space"
                else TurnBusinessState.COMPLETED
            )
            grounded_final = self._message_orchestration_service.finalize_turn(
                execution=grounded_execution,
                understanding=understanding,
                business_state=grounded_business_state,
                delivery_status=grounded_delivery,
                failure_classification=grounded_result.get("failure_classification"),
            )
            normalized_understanding = grounded_final.understanding
            saved_message = await self._repo_io.add_message(
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "knowledge_space_id": grounded_result.get("knowledge_space_id"),
                    "mode_used": grounded_result.get("mode_used"),
                    "base_used": grounded_result.get("base_used"),
                    "answer_strategy": grounded_result.get("answer_strategy"),
                    "estimated_wait_seconds": grounded_result.get("estimated_wait_seconds"),
                    "estimated_wait_range_seconds": grounded_result.get("estimated_wait_range_seconds"),
                    "processing_profile": grounded_result.get("processing_profile"),
                    "processing_notice": grounded_result.get("processing_notice"),
                    "evidence_count": grounded_result.get("evidence_count"),
                    "source_roles_used": grounded_result.get("source_roles_used"),
                    "source_scope": grounded_result.get("source_scope"),
                    "gaps_or_conflicts": grounded_result.get("gaps_or_conflicts"),
                    "citations": grounded_final.citations,
                    "citation_status": grounded_final.citation_status,
                    "understanding": normalized_understanding,
                    "confirmation": grounded_final.confirmation,
                    "agent_state": grounded_final.agent_state,
                    "delivery_status": grounded_final.delivery_status,
                    "failure_classification": grounded_final.failure_classification,
                    "provider": grounded_final.provider,
                    "model": grounded_final.model,
                },
            )
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)
            try:
                self._message_orchestration_service.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=grounded_result,
                    project_id=project_id,
                )
            except Exception:
                pass

            grounded_done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "message_id": str(saved_message.get("id")) if isinstance(saved_message, dict) else None,
                "provider": grounded_final.provider,
                "model": grounded_final.model,
                "citations": grounded_final.citations,
                "citation_status": grounded_final.citation_status,
                "confirmation": grounded_final.confirmation,
                "delivery_status": grounded_final.delivery_status,
                "failure_classification": grounded_final.failure_classification,
                "knowledge_space_id": grounded_result.get("knowledge_space_id"),
                "mode_used": grounded_result.get("mode_used"),
                "base_used": grounded_result.get("base_used"),
                "answer_strategy": grounded_result.get("answer_strategy"),
                "estimated_wait_seconds": grounded_result.get("estimated_wait_seconds"),
                "estimated_wait_range_seconds": grounded_result.get("estimated_wait_range_seconds"),
                "processing_profile": grounded_result.get("processing_profile"),
                "processing_notice": grounded_result.get("processing_notice"),
                "evidence_count": grounded_result.get("evidence_count"),
                "source_roles_used": grounded_result.get("source_roles_used") or [],
                "source_scope": grounded_result.get("source_scope"),
                "gaps_or_conflicts": grounded_result.get("gaps_or_conflicts") or [],
            }
            _, ui = split_ui(assistant_text)
            if ui:
                grounded_done_payload["ui"] = ui
            if normalized_understanding:
                grounded_done_payload["understanding"] = normalized_understanding
            agent_state = grounded_final.agent_state
            if agent_state:
                grounded_done_payload["agent_state"] = agent_state
            grounded_done = json.dumps(grounded_done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {grounded_done}\n\n"
            return

        secret_result = await self._message_orchestration_service.generate_secret_recall_reply(
            message=message,
            role=role,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        if secret_result is not None:
            secret_execution = TurnExecutionResult.from_payload(
                strategy=TurnStrategy.SECRET_RECALL,
                payload=secret_result,
                default_role=role,
            )
            secret_final = self._message_orchestration_service.finalize_turn(
                execution=secret_execution,
                understanding=understanding,
            )
            assistant_text = secret_final.response
            tok = json.dumps(
                {"text": assistant_text, "timestamp": int(_time.time() * 1000)},
                ensure_ascii=False,
            )
            yield f"event: token\ndata: {tok}\n\n"
            yield f"event: partial\ndata: {tok}\n\n"
            saved_message = await self._repo_io.add_message(
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "citations": secret_final.citations,
                    "citation_status": secret_final.citation_status,
                    "understanding": secret_final.understanding,
                    "confirmation": secret_final.confirmation,
                    "agent_state": secret_final.agent_state,
                    "delivery_status": secret_final.delivery_status,
                    "failure_classification": secret_final.failure_classification,
                    "provider": secret_final.provider,
                    "model": secret_final.model,
                },
            )
            secret_done = json.dumps(
                {
                    "conversation_id": conversation_id,
                    "message_id": str(saved_message.get("id")) if isinstance(saved_message, dict) else None,
                    "provider": secret_final.provider,
                    "model": secret_final.model,
                    "citations": secret_final.citations,
                    "citation_status": secret_final.citation_status,
                    "understanding": secret_final.understanding,
                    "confirmation": secret_final.confirmation,
                    "agent_state": secret_final.agent_state,
                    "delivery_status": secret_final.delivery_status,
                    "failure_classification": secret_final.failure_classification,
                },
                ensure_ascii=False,
            )
            yield f"event: done\ndata: {secret_done}\n\n"
            return

        persona = conv.get("persona") or "assistant"
        history = await self._repo_io.get_recent_messages(conversation_id, limit=20)

        relevant_memories = None
        if self._rag_service and not use_light_chat:
            relevant_memories = await self._rag_service.retrieve_context(
                message,
                user_id=user_id,
                conversation_id=conversation_id,
                caller_endpoint="/api/v1/chat/stream/{conversation_id}",
                transport="sse",
                identity_source=identity_source,
            )

        prompt = await self._prompt_service.build_prompt(
            persona, history, message, conv.get("summary"), relevant_memories
        )
        in_tokens = self._prompt_service.estimate_tokens(prompt)
        CHAT_TOKENS_TOTAL.labels(direction="in").inc(in_tokens)

        try:
            start_t = _time.time()
            task = asyncio.create_task(
                self._message_orchestration_service.execute_dynamic_turn(
                    plan=turn_plan,
                    request=turn_request,
                    prompt=prompt,
                    persona=persona,
                )
            )

            if heartbeat_interval and heartbeat_interval > 0:
                sent_heartbeat = False
                while True:
                    completed_tasks, _ = await asyncio.wait(
                        {task}, timeout=max(1, heartbeat_interval)
                    )
                    if completed_tasks:
                        if not sent_heartbeat:
                            hb = json.dumps({"timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                            yield f"event: heartbeat\ndata: {hb}\n\n"
                        break
                    hb = json.dumps({"timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                    yield f"event: heartbeat\ndata: {hb}\n\n"
                    sent_heartbeat = True

            execution = await task
            result = execution.to_payload()
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            citations: list[dict[str, Any]] = []
            citations_retrieval_failed = False
            citation_failure_classification = None
            citation_failure_reason = None
            needs_study_job = False
            if citation_lookup_required:
                citation_result = await collect_chat_citations_with_deadline(
                    message=message,
                    conversation_id=conversation_id,
                    memory_service=getattr(self._rag_service, "_memory", None),
                    limit=5,
                    collector=collect_chat_citations,
                )
                citations = citation_result.get("citations") or []
                citations_retrieval_failed = bool(citation_result.get("retrieval_failed"))
                citation_failure_classification = citation_result.get(
                    "failure_classification"
                )
                citation_failure_reason = citation_result.get("retrieval_failure_reason")

            raw_result_understanding = result.get("understanding")
            result_understanding: dict[str, Any] = (  # type: ignore[no-redef]
                dict(raw_result_understanding)
                if isinstance(raw_result_understanding, dict)
                else dict(understanding or {})
            )
            result["understanding"] = result_understanding

            result_understanding = build_routed_understanding(
                result_understanding,
                routing_decision=routing_decision,
                requested_role=requested_role,
                selected_role=role,
                route_applied=bool(route_applied),
                requires_confirmation=turn_plan.requires_confirmation,
                confirmation_reason=turn_plan.confirmation_reason,
            )
            result["understanding"] = result_understanding

            pending_action_id = extract_pending_action_id_from_text(str(result.get("response") or ""))
            pending_action_id, fallback_reason = maybe_create_fallback_pending_action(
                message=message,
                assistant_response=str(result.get("response") or ""),
                conversation_id=conversation_id,
                user_id=str(user_id) if user_id is not None else None,
                existing_pending_action_id=pending_action_id,
                understanding=result_understanding if isinstance(result_understanding, dict) else None,
            )
            if (
                fallback_reason
                and isinstance(result_understanding, dict)
                and not result_understanding.get("confirmation_reason")
            ):
                result_understanding["confirmation_reason"] = fallback_reason
            confirmation_payload = build_confirmation_payload(
                pending_action_id=pending_action_id,
                reason=(
                    (result_understanding or {}).get("confirmation_reason")
                    if isinstance(result_understanding, dict)
                    else None
                ),
            )
            normalized_understanding = normalize_understanding_payload(
                result_understanding or understanding,
                confirmation=confirmation_payload,
            )
            citation_status = build_citation_status(
                message=message,
                citations=citations,
                retrieval_failed=citations_retrieval_failed,
                retrieval_failure_reason=citation_failure_reason,
            )
            assistant_text = await self._message_orchestration_service.apply_response_memory_policies(
                assistant_text=str(result.get("response") or ""),
                user_message=message,
                user_id=user_id,
                conversation_id=conversation_id,
            )
            if citation_status.get("status") == "missing_required":
                active_knowledge_space_id = (
                    knowledge_space_id
                    or self._message_orchestration_service.resolve_active_knowledge_space_id(
                        conversation_id=conversation_id,
                        user_id=str(user_id) if user_id is not None else None,
                        requested_knowledge_space_id=knowledge_space_id,
                    )
                )
                if active_knowledge_space_id:
                    result.update(
                        build_missing_citation_resolution(
                            active_knowledge_space_id=active_knowledge_space_id,
                            retrieval_reason=citation_status.get("reason"),
                        )
                    )
                    assistant_text = str(result["response"])
                    citations = []
                    yield (
                        "event: cognitive_status\ndata: "
                        + json.dumps(
                            {
                                "state": "reviewing_knowledge_space",
                                "reason": "Revisando o material vinculado para responder com seguranca.",
                                "timestamp": int(_time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
                else:
                    yield (
                        "event: cognitive_status\ndata: "
                        + json.dumps(
                            {
                                "state": "studying_codebase",
                                "reason": "Estudando a base para responder com seguranca; isso pode demorar.",
                                "timestamp": int(_time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
                    result.update(
                        build_missing_citation_resolution(
                            active_knowledge_space_id=None,
                            retrieval_reason=citation_status.get("reason"),
                        )
                    )
                    assistant_text = str(result["response"])
                    needs_study_job = True
            execution.response = assistant_text
            execution.provider = str(result.get("provider") or execution.provider)
            execution.model = str(result.get("model") or execution.model)
            execution.citations = citations
            execution.citation_status = citation_status
            if needs_study_job:
                business_state = TurnBusinessState.PENDING_STUDY
            elif (
                result.get("knowledge_space_id")
                and citation_status.get("status") == "missing_required"
            ):
                business_state = TurnBusinessState.PENDING_KNOWLEDGE_SPACE
            else:
                business_state = TurnBusinessState.COMPLETED
            finalized = self._message_orchestration_service.finalize_turn(
                execution=execution,
                understanding=result_understanding,
                pending_action_id=pending_action_id,
                confirmation_reason=(
                    (result_understanding or {}).get("confirmation_reason")
                    if isinstance(result_understanding, dict)
                    else None
                ),
                business_state=business_state,
                delivery_status=business_state.value,
                failure_classification=(
                    "knowledge_space_pending"
                    if business_state is TurnBusinessState.PENDING_KNOWLEDGE_SPACE
                    else (
                        citation_failure_classification
                        if business_state is not TurnBusinessState.PENDING_STUDY
                        else None
                    )
                ),
            )
            normalized_understanding = finalized.understanding
            confirmation_payload = finalized.confirmation
            _, ui = split_ui(assistant_text)

            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps({"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"

            saved_message = await self._repo_io.add_message(
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "citations": finalized.citations,
                    "citation_status": finalized.citation_status,
                    "understanding": normalized_understanding,
                    "confirmation": confirmation_payload,
                    "agent_state": finalized.agent_state,
                    "delivery_status": finalized.delivery_status,
                    "failure_classification": finalized.failure_classification,
                    "provider": finalized.provider,
                    "model": finalized.model,
                },
            )
            study_job_payload = None
            if needs_study_job and self._study_jobs is not None:
                job = await asyncio.to_thread(
                    self._study_jobs.create_job,
                    conversation_id=conversation_id,
                    message_id=str(saved_message.get("id")),
                    question=message,
                    user_id=str(user_id) if user_id is not None else None,
                    placeholder_message=assistant_text,
                )
                study_job_payload = {
                    "job_id": job.job_id,
                    "status": job.status,
                    "poll_url": f"/api/v1/chat/study-jobs/{job.job_id}",
                    "conversation_id": conversation_id,
                    "message_id": str(saved_message.get("id")),
                    "placeholder_message": job.placeholder_message,
                }
                asyncio.create_task(
                    self._study_jobs.run_job(
                        job_id=job.job_id,
                        role=role,
                        priority=priority,
                    )
                )
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            try:
                provider = result.get("provider", "unknown")
                pricing = _provider_pricing.get(provider)
                if pricing:
                    cost = (in_tokens / 1000.0) * float(pricing.input_per_1k_usd) + (
                        out_tokens / 1000.0
                    ) * float(pricing.output_per_1k_usd)
                    if user_id:
                        CHAT_SPEND_USD_TOTAL.labels(kind="user").inc(cost)
                    if project_id:
                        CHAT_SPEND_USD_TOTAL.labels(kind="project").inc(cost)
            except Exception:
                pass

            try:
                self._message_orchestration_service.trigger_post_response_events(
                    conversation_id=conversation_id,
                    user_message=message,
                    assistant_text=assistant_text,
                    result=result,
                    project_id=project_id,
                )
            except Exception:
                pass

            done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "message_id": str(saved_message.get("id")) if isinstance(saved_message, dict) else None,
                "provider": finalized.provider,
                "model": finalized.model,
                "citations": finalized.citations,
                "citation_status": finalized.citation_status,
                "delivery_status": finalized.delivery_status,
                "failure_classification": finalized.failure_classification,
            }
            if ui:
                done_payload["ui"] = ui
            if study_job_payload:
                done_payload["study_job"] = study_job_payload
            if normalized_understanding:
                done_payload["understanding"] = normalized_understanding
            if confirmation_payload:
                done_payload["confirmation"] = confirmation_payload
            agent_state = finalized.agent_state
            if agent_state:
                done_payload["agent_state"] = agent_state
                if agent_state.get("state") == "waiting_confirmation":
                    yield (
                        "event: cognitive_status\ndata: "
                        + json.dumps(
                            {
                                "state": "waiting_confirmation",
                                "requires_confirmation": True,
                                "reason": (confirmation_payload or {}).get("reason"),
                                "timestamp": int(_time.time() * 1000),
                            },
                            ensure_ascii=False,
                        )
                        + "\n\n"
                    )
            done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {done}\n\n"

            try:
                latency_ms = int((_time.time() - start_t_overall) * 1000)
                logger.info(
                    "chat.stream",
                    stage="done",
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    provider=result.get("provider"),
                    model=result.get("model"),
                    latency_ms=latency_ms,
                    retries=0,
                )
            except Exception:
                pass
        except Exception as e:
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="error").observe(
                max(0.0, _time.time() - start_t)
            )
            err = json.dumps(
                chat_sse_error_payload(
                    code="CHAT_INVOCATION_ERROR",
                    message=str(e),
                    category="internal",
                    retryable=True,
                ),
                ensure_ascii=False,
            )
            try:
                CHAT_ERRORS_TOTAL.labels(code="InvocationError").inc()
            except Exception:
                pass
            yield f"event: error\ndata: {err}\n\n"

    async def stream_events(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        import json
        import time as now_time

        from app.core.infrastructure.message_broker import get_broker

        yield "event: connected\ndata: {}\n\n"

        broker = await get_broker()
        try:
            await broker.connect()
        except Exception as e:
            logger.warning("event_stream_broker_connect_failed", error=str(e))

        queue: asyncio.Queue[Any] = asyncio.Queue()

        async def on_event(payload: Any) -> None:
            await queue.put(payload)

        routing_key = f"janus.event.conversation.{conversation_id}.#"
        subscription_task = broker.start_subscription(
            exchange_name="janus.events",
            routing_key=routing_key,
            callback=on_event,
            queue_name="",
        )

        try:
            start_time = now_time.time()
            max_duration = int(os.getenv("CHAT_EVENTS_MAX_DURATION_SECONDS", "1800"))

            while (now_time.time() - start_time) < max_duration:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    original_payload = payload
                    if isinstance(payload, (bytes, bytearray)):
                        try:
                            payload = json.loads(payload.decode("utf-8"))
                        except Exception:
                            payload = {"content": original_payload.decode("utf-8", errors="replace")}
                    elif isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except Exception:
                            payload = {"content": payload}
                    elif not isinstance(payload, dict):
                        payload = {"content": str(payload)}

                    evt_user = payload.get("user_id")
                    if user_id and evt_user and str(evt_user) != str(user_id):
                        continue

                    event_type = payload.get("event_type") or payload.get("type") or "unknown"
                    agent_role = payload.get("agent_role") or payload.get("agent") or "unknown"

                    sse_event = {
                        "event_type": event_type,
                        "agent_role": agent_role,
                        "content": payload.get("content", ""),
                        "timestamp": payload.get("timestamp") or now_time.time(),
                        "task_id": payload.get("task_id") or conversation_id,
                        "conversation_id": payload.get("conversation_id") or conversation_id,
                        "type": event_type,
                        "agent": agent_role,
                    }
                    yield f"event: agent_event\ndata: {json.dumps(sse_event, ensure_ascii=False)}\n\n"
                except (asyncio.TimeoutError, TimeoutError):
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            subscription_task.cancel()
            try:
                await subscription_task
            except Exception:
                pass
            logger.info("log_info", message=f"Stream de eventos encerrado para {conversation_id}")
