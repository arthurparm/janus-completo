import asyncio
import inspect
import json
import os
import time as _time
from typing import Any
from uuid import uuid4

import structlog

from app.core.exceptions.chat_exceptions import ChatServiceError
from app.core.llm import ModelPriority, ModelRole
from app.core.llm.pricing import _provider_pricing
from app.core.monitoring.chat_metrics import (
    CHAT_LATENCY_SECONDS,
    CHAT_SPEND_USD_TOTAL,
    CHAT_TOKENS_TOTAL,
)
from app.repositories.chat_repository import ChatRepository, ChatRepositoryError
from app.services.chat.chat_citation_service import (
    MANDATORY_CITATION_GUARD_TEXT,
    build_citation_status,
    collect_chat_citations,
)
from app.services.chat.chat_contracts import (
    build_agent_state,
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
from app.services.chat.message_orchestration_service import MessageOrchestrationService
from app.services.chat_study_service import ChatStudyService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService

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
    ):
        self._repo = repo
        self._llm = llm_service
        self._tools = tool_service
        self._prompt_service = prompt_service
        self._rag_service = rag_service
        self._conversation_service = conversation_service
        self._message_orchestration_service = message_orchestration_service

    async def stream_message(
        self,
        conversation_id: str,
        message: str,
        role: ModelRole | None = None,
        priority: ModelPriority | None = None,
        timeout_seconds: int | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        identity_source: str = "unknown",
        requested_role: str | None = None,
        routing_decision: Any | None = None,
        route_applied: bool | None = None,
    ):
        role = role or ModelRole.ORCHESTRATOR
        priority = priority or ModelPriority.HIGH_QUALITY

        max_bytes = int(os.getenv("CHAT_MAX_MESSAGE_BYTES", str(10 * 1024)))
        default_timeout = int(os.getenv("CHAT_DEFAULT_TIMEOUT_SECONDS", "30"))
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
        try:
            conv = self._repo.get_conversation(conversation_id)
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

        self._repo.add_message(conversation_id, role="user", text=message)
        self._message_orchestration_service.schedule_active_memory_capture(
            message=message,
            user_id=user_id,
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

        grounded_result = await self._message_orchestration_service.generate_document_grounded_reply(
            conversation_id=conversation_id,
            message=message,
            role=role,
            priority=priority,
            timeout_seconds=timeout_seconds,
            user_id=user_id,
            project_id=project_id,
            understanding=understanding,
        )
        if grounded_result is not None:
            assistant_text = str(grounded_result.get("response") or "")
            citations = grounded_result.get("citations") or []
            citation_status = grounded_result.get("citation_status") or build_citation_status(
                message=message,
                citations=citations,
            )
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
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(
                            provider=str(grounded_result.get("provider") or "janus"),
                            model=str(grounded_result.get("model") or "document_grounding"),
                        ).observe(ttft_ms / 1000.0)
                    except Exception:
                        pass

            normalized_understanding = normalize_understanding_payload(understanding, confirmation=None)
            saved_message = self._repo.add_message(
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "citations": citations,
                    "citation_status": citation_status,
                    "understanding": normalized_understanding,
                    "confirmation": None,
                    "agent_state": build_agent_state(
                        stream_phase="completed",
                        understanding=normalized_understanding,
                        confirmation=None,
                    ),
                    "delivery_status": "completed",
                    "provider": grounded_result.get("provider"),
                    "model": grounded_result.get("model"),
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
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass

            done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "message_id": str(saved_message.get("id")) if isinstance(saved_message, dict) else None,
                "provider": grounded_result.get("provider"),
                "model": grounded_result.get("model"),
                "citations": citations,
                "citation_status": citation_status,
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            if normalized_understanding:
                done_payload["understanding"] = normalized_understanding
            agent_state = (
                saved_message.get("agent_state")
                if isinstance(saved_message, dict)
                else None
            ) or build_agent_state(
                stream_phase="completed",
                understanding=normalized_understanding,
                confirmation=None,
            )
            if agent_state:
                done_payload["agent_state"] = agent_state
            done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {done}\n\n"
            return

        persona = conv.get("persona") or "assistant"
        history = self._repo.get_recent_messages(conversation_id, limit=20)

        relevant_memories = None
        if self._rag_service:
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

        if self._prompt_service.is_discovery_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_discovery_intro(self._tools)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(provider="janus", model="discovery").observe(
                            ttft_ms / 1000.0
                        )
                    except Exception:
                        pass

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "discovery",
                "citations": [],
                "citation_status": build_citation_status(message=message, citations=[]),
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            normalized_understanding = normalize_understanding_payload(understanding, confirmation=None)
            if normalized_understanding:
                done_payload["understanding"] = normalized_understanding
            agent_state = build_agent_state(
                stream_phase="completed",
                understanding=normalized_understanding,
                confirmation=None,
            )
            if agent_state:
                done_payload["agent_state"] = agent_state
            done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {done}\n\n"
            return

        if self._prompt_service.is_docs_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_tools_documentation(self._tools)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(provider="janus", model="tools_docs").observe(
                            ttft_ms / 1000.0
                        )
                    except Exception:
                        pass

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            done_payload = {
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "tools_docs",
                "citations": [],
                "citation_status": build_citation_status(message=message, citations=[]),
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            normalized_understanding = normalize_understanding_payload(understanding, confirmation=None)
            if normalized_understanding:
                done_payload["understanding"] = normalized_understanding
            agent_state = build_agent_state(
                stream_phase="completed",
                understanding=normalized_understanding,
                confirmation=None,
            )
            if agent_state:
                done_payload["agent_state"] = agent_state
            done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {done}\n\n"
            return

        if self._prompt_service.is_capabilities_query(message):
            start_t = _time.time()
            assistant_text = self._prompt_service.render_local_capabilities(self._tools)
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)

            first_token = True
            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps(
                    {"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False
                )
                ttft = _time.time() - start_t_overall
                limit = float(timeout_seconds or default_timeout)
                if limit > 0 and ttft > limit:
                    err = json.dumps(
                        chat_sse_error_payload(
                            code="CHAT_STREAM_TIMEOUT",
                            message="TTFT timeout",
                            category="timeout",
                            retryable=True,
                            details={"phase": "ttft"},
                        ),
                        ensure_ascii=False,
                    )
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                        CHAT_ERRORS_TOTAL.labels(code="TTFTTimeout").inc()
                    except Exception:
                        pass
                    yield f"event: error\ndata: {err}\n\n"
                    return
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"
                if first_token:
                    ttft_ms = int((_time.time() - start_t_overall) * 1000)
                    first_token = False
                    try:
                        from app.core.monitoring.chat_metrics import CHAT_TTFT_SECONDS

                        CHAT_TTFT_SECONDS.labels(provider="janus", model="capabilities").observe(
                            ttft_ms / 1000.0
                        )
                    except Exception:
                        pass

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
            out_tokens = self._prompt_service.estimate_tokens(assistant_text)
            CHAT_TOKENS_TOTAL.labels(direction="out").inc(out_tokens)

            done_payload = {
                "conversation_id": conversation_id,
                "provider": "janus",
                "model": "capabilities",
                "citations": [],
                "citation_status": build_citation_status(message=message, citations=[]),
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            normalized_understanding = normalize_understanding_payload(understanding, confirmation=None)
            if normalized_understanding:
                done_payload["understanding"] = normalized_understanding
            agent_state = build_agent_state(
                stream_phase="completed",
                understanding=normalized_understanding,
                confirmation=None,
            )
            if agent_state:
                done_payload["agent_state"] = agent_state
            done = json.dumps(done_payload, ensure_ascii=False)
            yield f"event: done\ndata: {done}\n\n"
            return

        current_provider = None
        try:
            if inspect.iscoroutinefunction(self._llm.select_provider):
                pre = await self._llm.select_provider(
                    role=role, priority=priority, user_id=user_id, project_id=project_id
                )
            else:
                pre = await asyncio.to_thread(
                    self._llm.select_provider,
                    role,
                    priority,
                    user_id,
                    project_id,
                )
            current_provider = pre.get("provider")
            current_model = pre.get("model")
            if self._llm.is_provider_open(current_provider or ""):
                err = json.dumps(
                    chat_sse_error_payload(
                        code="CHAT_CIRCUIT_OPEN",
                        message="Circuit open",
                        category="availability",
                        retryable=True,
                    ),
                    ensure_ascii=False,
                )
                try:
                    from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                    CHAT_ERRORS_TOTAL.labels(code="CircuitOpen").inc()
                except Exception:
                    pass
                yield f"event: error\ndata: {err}\n\n"
                return

            start_t = _time.time()
            if inspect.iscoroutinefunction(self._llm.invoke_llm):
                task = asyncio.create_task(
                    self._llm.invoke_llm(
                        prompt=prompt,
                        role=role,
                        priority=priority,
                        timeout_seconds=timeout_seconds,
                        user_id=user_id,
                        project_id=project_id,
                    )
                )
            else:
                task = asyncio.create_task(
                    asyncio.to_thread(
                        self._llm.invoke_llm,
                        prompt=prompt,
                        role=role,
                        priority=priority,
                        timeout_seconds=timeout_seconds,
                        user_id=user_id,
                        project_id=project_id,
                    )
                )

            if heartbeat_interval and heartbeat_interval > 0:
                sent_heartbeat = False
                while True:
                    done, _ = await asyncio.wait({task}, timeout=max(1, heartbeat_interval))
                    if done:
                        if not sent_heartbeat:
                            hb = json.dumps({"timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                            yield f"event: heartbeat\ndata: {hb}\n\n"
                        break
                    hb = json.dumps({"timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                    yield f"event: heartbeat\ndata: {hb}\n\n"
                    sent_heartbeat = True

            result = await task
            elapsed = max(0.0, _time.time() - start_t)
            CHAT_LATENCY_SECONDS.labels(role=role.value, outcome="success").observe(elapsed)
            current_provider = result.get("provider")

            if self._cb_should_block(current_provider):
                err = json.dumps(
                    chat_sse_error_payload(
                        code="CHAT_CIRCUIT_OPEN",
                        message="Circuit open",
                        category="availability",
                        retryable=True,
                    ),
                    ensure_ascii=False,
                )
                try:
                    from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                    CHAT_ERRORS_TOTAL.labels(code="CircuitOpen").inc()
                except Exception:
                    pass
                yield f"event: error\ndata: {err}\n\n"
                return

            citations: list[dict[str, Any]] = []
            citations_retrieval_failed = False
            try:
                citation_result = await collect_chat_citations(
                    message=message,
                    user_id=str(user_id) if user_id is not None else None,
                    conversation_id=conversation_id,
                    memory_service=getattr(self._rag_service, "_memory", None),
                    limit=5,
                )
                citations = citation_result.get("citations") or []
                citations_retrieval_failed = bool(citation_result.get("retrieval_failed"))
            except Exception:
                citations = []
                citations_retrieval_failed = True

            result_understanding = result.get("understanding") if isinstance(result, dict) else None
            if not isinstance(result_understanding, dict):
                result_understanding = dict(understanding or {})
                result["understanding"] = result_understanding

            if routing_decision is not None and hasattr(routing_decision, "to_dict"):
                try:
                    result_understanding["routing"] = {
                        "requested_role": requested_role,
                        "selected_role": role.value,
                        "route_applied": bool(route_applied),
                        **routing_decision.to_dict(),
                    }
                except Exception:
                    pass

                try:
                    if getattr(routing_decision, "risk_level", None) == "high":
                        result_understanding["requires_confirmation"] = True
                        result_understanding["confirmation_reason"] = "high_risk"
                        if "alto risco" not in str(result.get("response", "")).lower():
                            result["response"] = (
                                "Pedido classificado como alto risco. Confirme o objetivo e o escopo antes de seguir.\n\n"
                                f"{result.get('response', '')}"
                            )
                except Exception:
                    pass

            pending_action_id = extract_pending_action_id_from_text(str(result.get("response") or ""))
            pending_action_id, fallback_reason = maybe_create_fallback_pending_action(
                user_id=str(user_id) if user_id is not None else None,
                message=message,
                assistant_response=str(result.get("response") or ""),
                conversation_id=conversation_id,
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
            )
            assistant_text = str(result.get("response") or "")
            if citation_status.get("status") == "missing_required":
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
                study_service = ChatStudyService(
                    llm_service=self._llm,
                    knowledge_service=None,
                    autonomy_admin_service=None,
                )
                pending_progress_events: list[str] = []

                async def _progress(value: int, stage: str, reason: str) -> None:
                    state = "study_progress" if stage != "synthesis" else "resuming_answer_generation"
                    payload = {
                        "state": state,
                        "reason": reason,
                        "progress": value,
                        "timestamp": int(_time.time() * 1000),
                    }
                    yield_data = json.dumps(payload, ensure_ascii=False)
                    pending_progress_events.append(
                        f"event: cognitive_status\ndata: {yield_data}\n\n"
                    )

                study_result = await study_service.answer_with_study(
                    question=message,
                    role=role,
                    priority=priority,
                    user_id=str(user_id) if user_id is not None else None,
                    conversation_id=conversation_id,
                    progress_cb=_progress,
                )
                for progress_event in pending_progress_events:
                    yield progress_event
                assistant_text = str(study_result.get("response") or MANDATORY_CITATION_GUARD_TEXT)
                result["response"] = assistant_text
                result["provider"] = study_result.get("provider") or result.get("provider")
                result["model"] = study_result.get("model") or result.get("model")
                citations = study_result.get("citations") or []
                citation_status = study_result.get("citation_status") or citation_status
            _, ui = split_ui(assistant_text)

            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps({"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"

            saved_message = self._repo.add_message(
                conversation_id,
                role="assistant",
                text=assistant_text,
                metadata={
                    "citations": citations,
                    "citation_status": citation_status,
                    "understanding": normalized_understanding,
                    "confirmation": confirmation_payload,
                    "agent_state": build_agent_state(
                        stream_phase="completed",
                        understanding=normalized_understanding,
                        confirmation=confirmation_payload,
                    ),
                    "delivery_status": "completed",
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                },
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
                    user_id=user_id,
                    project_id=project_id,
                )
            except Exception:
                pass

            done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "message_id": str(saved_message.get("id")) if isinstance(saved_message, dict) else None,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "citations": citations,
                "citation_status": citation_status,
            }
            if ui:
                done_payload["ui"] = ui
            if normalized_understanding:
                done_payload["understanding"] = normalized_understanding
            if confirmation_payload:
                done_payload["confirmation"] = confirmation_payload
            agent_state = (
                saved_message.get("agent_state")
                if isinstance(saved_message, dict)
                else None
            ) or build_agent_state(
                stream_phase="completed",
                understanding=normalized_understanding,
                confirmation=confirmation_payload,
            )
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

            self._cb_on_success(current_provider)
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
                from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                CHAT_ERRORS_TOTAL.labels(code="InvocationError").inc()
            except Exception:
                pass
            yield f"event: error\ndata: {err}\n\n"
            try:
                self._cb_on_error(current_provider)
            except Exception:
                pass

    async def stream_events(self, conversation_id: str, user_id: str | None = None):
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

        async def on_event(payload):
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

    def _cb_should_block(self, provider: str | None) -> bool:
        try:
            if not provider:
                return False
            state = getattr(self, "_cb_state", {})
            provider_state = state.get(provider)
            if not provider_state:
                return False
            opened_at = provider_state.get("opened_at") or 0
            cooldown = int(os.getenv("CHAT_CB_COOLDOWN_SECONDS", "60"))
            return provider_state.get("state") == "open" and (_time.time() - opened_at) < cooldown
        except Exception:
            return False

    def _cb_on_error(self, provider: str | None) -> None:
        try:
            if not provider:
                return
            state = getattr(self, "_cb_state", {})
            provider_state = state.get(provider) or {"failures": 0, "state": "closed"}
            provider_state["failures"] = int(provider_state.get("failures", 0)) + 1
            threshold = int(os.getenv("CHAT_CB_FAILURE_THRESHOLD", "5"))
            if provider_state["failures"] >= threshold:
                provider_state["state"] = "open"
                provider_state["opened_at"] = _time.time()
                try:
                    from app.core.monitoring.chat_metrics import CHAT_CB_STATE_CHANGES

                    CHAT_CB_STATE_CHANGES.labels(provider=provider, state="open").inc()
                except Exception:
                    pass
            state[provider] = provider_state
            self._cb_state = state
        except Exception:
            pass

    def _cb_on_success(self, provider: str | None) -> None:
        try:
            if not provider:
                return
            state = getattr(self, "_cb_state", {})
            provider_state = state.get(provider) or {"failures": 0, "state": "closed"}
            provider_state["failures"] = 0
            provider_state["state"] = "closed"
            try:
                from app.core.monitoring.chat_metrics import CHAT_CB_STATE_CHANGES

                CHAT_CB_STATE_CHANGES.labels(provider=provider, state="closed").inc()
            except Exception:
                pass
            state[provider] = provider_state
            self._cb_state = state
        except Exception:
            pass
