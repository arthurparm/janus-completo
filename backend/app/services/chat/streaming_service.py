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
from app.services.chat.conversation_service import ConversationService
from app.services.chat.message_helpers import (
    build_understanding_payload,
    split_ui,
)
from app.services.chat.message_orchestration_service import MessageOrchestrationService
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
                    {"error": "Message too large", "code": "MessageTooLarge"}, ensure_ascii=False
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
                {"error": "Conversation not found", "code": "ConversationNotFound"},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {err}\n\n"
            return
        except ChatServiceError as e:
            err = json.dumps({"error": str(e), "code": "AccessDenied"}, ensure_ascii=False)
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
        ack = json.dumps({"conversation_id": conversation_id}, ensure_ascii=False)
        yield f"event: ack\ndata: {ack}\n\n"

        persona = conv.get("persona") or "assistant"
        history = self._repo.get_recent_messages(conversation_id, limit=20)

        relevant_memories = None
        if self._rag_service:
            relevant_memories = await self._rag_service.retrieve_context(
                message, user_id=user_id, conversation_id=conversation_id
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
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            if understanding:
                done_payload["understanding"] = understanding
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
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            if understanding:
                done_payload["understanding"] = understanding
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
                    err = json.dumps({"error": "TTFT timeout", "code": "TTFTTimeout"}, ensure_ascii=False)
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
            }
            _, ui = split_ui(assistant_text)
            if ui:
                done_payload["ui"] = ui
            if understanding:
                done_payload["understanding"] = understanding
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
                err = json.dumps({"error": "Circuit open", "code": "CircuitOpen"}, ensure_ascii=False)
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
            assistant_text = result.get("response", "")
            _, ui = split_ui(assistant_text)
            current_provider = result.get("provider")

            if self._cb_should_block(current_provider):
                err = json.dumps({"error": "Circuit open", "code": "CircuitOpen"}, ensure_ascii=False)
                try:
                    from app.core.monitoring.chat_metrics import CHAT_ERRORS_TOTAL

                    CHAT_ERRORS_TOTAL.labels(code="CircuitOpen").inc()
                except Exception:
                    pass
                yield f"event: error\ndata: {err}\n\n"
                return

            for i in range(0, len(assistant_text), 256):
                chunk = assistant_text[i : i + 256]
                tok = json.dumps({"text": chunk, "timestamp": int(_time.time() * 1000)}, ensure_ascii=False)
                yield f"event: token\ndata: {tok}\n\n"
                yield f"event: partial\ndata: {tok}\n\n"

            self._repo.add_message(conversation_id, role="assistant", text=assistant_text)
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

            citations: list[dict[str, Any]] = []
            try:
                from qdrant_client import models as qdrant_models

                from app.core.embeddings.embedding_manager import aembed_text
                from app.db.vector_store import aget_or_create_collection, get_async_qdrant_client

                vec = await aembed_text(message)
                coll = (
                    await aget_or_create_collection(f"user_{user_id}")
                    if user_id
                    else await aget_or_create_collection("janus_episodic_memory")
                )

                must: list[qdrant_models.FieldCondition] = []
                if user_id:
                    must.append(
                        qdrant_models.FieldCondition(
                            key="metadata.user_id", match=qdrant_models.MatchValue(value=str(user_id))
                        )
                    )
                if conversation_id:
                    must.append(
                        qdrant_models.FieldCondition(
                            key="metadata.session_id",
                            match=qdrant_models.MatchValue(value=conversation_id),
                        )
                    )
                must_not: list[qdrant_models.FieldCondition] = [
                    qdrant_models.FieldCondition(
                        key="metadata.status", match=qdrant_models.MatchValue(value="duplicate")
                    )
                ]

                query_filter = (
                    qdrant_models.Filter(must=must, must_not=must_not)
                    if must
                    else qdrant_models.Filter(must_not=must_not)
                )
                client = get_async_qdrant_client()
                res = await client.query_points(
                    collection_name=coll,
                    query=vec,
                    limit=5,
                    with_payload=True,
                    query_filter=query_filter,
                )
                hits = getattr(res, "points", res) or []
                for hit in hits:
                    payload = getattr(hit, "payload", {}) or {}
                    meta = payload.get("metadata") or {}
                    line_start = (
                        meta.get("line_start")
                        or meta.get("start_line")
                        or meta.get("line")
                        or meta.get("line_no")
                    )
                    line_end = meta.get("line_end") or meta.get("end_line")
                    citations.append(
                        {
                            "id": getattr(hit, "id", None),
                            "title": meta.get("title"),
                            "url": meta.get("url"),
                            "doc_id": meta.get("doc_id"),
                            "file_path": meta.get("file_path"),
                            "type": meta.get("type"),
                            "origin": meta.get("origin"),
                            "line_start": line_start,
                            "line_end": line_end,
                            "line": line_start,
                            "score": float(getattr(hit, "score", 0.0) or 0.0),
                            "snippet": payload.get("content"),
                        }
                    )
            except Exception:
                citations = []

            done_payload: dict[str, Any] = {
                "conversation_id": conversation_id,
                "provider": result.get("provider"),
                "model": result.get("model"),
                "citations": citations,
            }
            if ui:
                done_payload["ui"] = ui
            result_understanding = result.get("understanding") if isinstance(result, dict) else None
            if result_understanding or understanding:
                done_payload["understanding"] = result_understanding or understanding
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
            err = json.dumps({"error": str(e), "code": "InvocationError"}, ensure_ascii=False)
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
            logger.info(f"Stream de eventos encerrado para {conversation_id}")

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
