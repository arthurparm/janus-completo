import json

import pytest
from app.core.llm import ModelPriority, ModelRole
from app.services.chat.chat_citation_service import (
    references_uploaded_material,
)
from app.services.chat.citation_policy import requires_mandatory_citations
from app.services.chat.conversation_service import ConversationService
from app.services.chat.streaming_service import StreamingService
from app.services.chat.turn_core import (
    ChatTurnFinalizer,
    ChatTurnPlanner,
    TurnExecutionResult,
    TurnPlanningSignals,
    TurnStrategy,
)

MANDATORY_CITATION_GUARD_TEXT = (
    "Nao encontrei citacoes rastreaveis para essa resposta de documento/codigo. "
    "Envie mais contexto (arquivo, funcao ou documento) para eu responder com fonte."
)


class _FakeRepo:
    def __init__(self):
        self.messages = []
        self.conv = {"persona": "assistant", "summary": None, "messages": []}
        self.recent_calls = 0

    def get_conversation(self, conversation_id):
        if conversation_id != "conv-1":
            raise ValueError("missing")
        return self.conv

    def add_message(self, conversation_id, role, text, metadata=None):
        payload = {"id": "55", "text": text, **(metadata or {})}
        self.messages.append((conversation_id, role, text, metadata or {}))
        return payload

    def get_recent_messages(self, conversation_id, limit=20):
        self.recent_calls += 1
        return []


@pytest.mark.asyncio
async def test_streaming_service_uses_shared_configured_message_size_limit(monkeypatch):
    monkeypatch.setenv("CHAT_MAX_MESSAGE_BYTES", "3")
    repo = _FakeRepo()
    llm = _FakeLLM()
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=ConversationService(repo),
        message_orchestration_service=_FakeMessageOrchestration(llm, repo=repo),
    )

    chunks = [
        chunk
        async for chunk in streaming.stream_message(
            conversation_id="conv-1",
            message="áá",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )
    ]

    events = _parse_sse_chunks(chunks)
    assert events == [
        (
            "error",
            {
                "code": "CHAT_MESSAGE_TOO_LARGE",
                "message": "Message too large",
                "category": "validation",
                "retryable": False,
                "http_status": 413,
                "details": {},
            },
        )
    ]
    assert repo.messages == []


class _FakeLLM:
    def __init__(self):
        self.calls = []

    def select_provider(self, role, priority, project_id=None):
        return {"provider": "dummy", "model": "m"}

    def is_provider_open(self, provider: str) -> bool:
        return False

    async def invoke_llm(
        self,
        prompt,
        role,
        priority,
        timeout_seconds=None,
        task_type=None,
        complexity=None,
        policy_overrides=None,
        project_id=None,
        user_id=None,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "role": role,
                "priority": priority,
                "timeout_seconds": timeout_seconds,
                "task_type": task_type,
                "complexity": complexity,
                "policy_overrides": policy_overrides,
                "project_id": project_id,
                "user_id": user_id,
            }
        )
        return {"response": "ok from llm", "provider": "dummy", "model": "m"}


class _FakePromptService:
    def __init__(self):
        self.build_calls = 0

    async def build_prompt(self, persona, history, message, summary, relevant_memories):
        self.build_calls += 1
        return f"{persona}:{message}"

    def estimate_tokens(self, text):
        return max(1, len(text) // 4)

    def is_discovery_query(self, message):
        return False

    def render_discovery_intro(self, tools):
        return "discovery"

    def is_docs_query(self, message):
        return False

    def render_tools_documentation(self, tools):
        return "docs"

    def is_capabilities_query(self, message):
        return False

    def render_local_capabilities(self):
        return "capabilities"


class _FakeMessageOrchestration:
    def __init__(self, llm_service, *, repo=None, static_strategy=None):
        self.calls = 0
        self.grounded_calls = 0
        self.grounded_result = None
        self._llm = llm_service
        self._repo = repo
        self.static_strategy = static_strategy
        self.persist_calls = []
        self.persist_error = None
        self.dynamic_calls = 0
        self._planner = ChatTurnPlanner()
        self._finalizer = ChatTurnFinalizer()

    def _should_use_light_chat(self, *, message, role, understanding):
        if role != ModelRole.ORCHESTRATOR:
            return False
        if not understanding or understanding.get("intent") not in {"general", "question"}:
            return False
        return len((message or "").strip()) <= 160

    def build_turn_plan(self, *, request, understanding, routing_decision):
        risk_level = getattr(routing_decision, "risk_level", None)
        return self._planner.plan(
            request,
            TurnPlanningSignals(
                understanding=understanding,
                light_chat_eligible=self._should_use_light_chat(
                    message=request.message,
                    role=request.role,
                    understanding=understanding,
                ),
                citation_lookup_required=(
                    requires_mandatory_citations(request.message)
                    or references_uploaded_material(request.message)
                ),
                is_discovery=self.static_strategy is TurnStrategy.STATIC_DISCOVERY,
                is_docs=self.static_strategy is TurnStrategy.STATIC_DOCS,
                is_capabilities=self.static_strategy is TurnStrategy.STATIC_CAPABILITIES,
                risk_level=risk_level,
            ),
        )

    async def execute_dynamic_turn(self, *, plan, request, prompt, persona):
        self.dynamic_calls += 1
        payload = await self._llm.invoke_llm(
            prompt=prompt,
            role=request.role,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds or 12,
            task_type="general_task",
            complexity="low",
            policy_overrides={
                "role": request.role.value,
                "priority": request.priority.value,
                "timeout_seconds": request.timeout_seconds or 12,
            },
            user_id=request.user_id,
            project_id=request.project_id,
        )
        return TurnExecutionResult.from_payload(
            strategy=plan.dynamic_strategy,
            payload=payload,
            default_role=request.role,
        )

    async def execute_static_turn(self, *, strategy, role):
        response_by_strategy = {
            TurnStrategy.HIGH_RISK_CONFIRMATION: (
                "Pedido classificado como alto risco. "
                "Confirme o objetivo e o escopo antes de seguir."
            ),
            TurnStrategy.STATIC_DISCOVERY: "discovery",
            TurnStrategy.STATIC_DOCS: "docs",
            TurnStrategy.STATIC_CAPABILITIES: "capabilities",
            TurnStrategy.BLOCKED_TOOL_CREATION: (
                "Tool creation and autonomous code evolution are permanently disabled."
            ),
        }
        return TurnExecutionResult(
            strategy=strategy,
            response=response_by_strategy[strategy],
            provider="janus",
            model={
                TurnStrategy.STATIC_DISCOVERY: "discovery",
                TurnStrategy.STATIC_DOCS: "tools_docs",
                TurnStrategy.STATIC_CAPABILITIES: "capabilities",
            }.get(strategy, strategy.value),
            role=role.value,
            citation_status=(
                {
                    "mode": "optional",
                    "status": "not_applicable",
                    "count": 0,
                    "reason": None,
                }
                if strategy
                in {
                    TurnStrategy.STATIC_DISCOVERY,
                    TurnStrategy.STATIC_DOCS,
                    TurnStrategy.STATIC_CAPABILITIES,
                }
                else None
            ),
        )

    def finalize_turn(self, **kwargs):
        return self._finalizer.finalize(**kwargs)

    async def generate_document_grounded_reply(self, **kwargs):
        self.grounded_calls += 1
        return self.grounded_result

    def schedule_active_memory_capture(self, **kwargs):
        return None

    def build_knowledge_space_runtime_notice(
        self,
        *,
        conversation_id: str | None = None,
        message: str | None,
        user_id: str | None = None,
        requested_knowledge_space_id: str | None = None,
    ):
        return None

    async def generate_secret_recall_reply(self, **kwargs):
        return None

    async def apply_response_memory_policies(
        self,
        assistant_text: str,
        user_message: str | None,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> str:
        return assistant_text

    def resolve_active_knowledge_space_id(
        self,
        *,
        conversation_id: str | None,
        user_id: str | None = None,
        requested_knowledge_space_id: str | None = None,
    ):
        return requested_knowledge_space_id

    def trigger_post_response_events(self, **kwargs):
        self.calls += 1

    async def persist_finalized_turn(self, **kwargs):
        self.persist_calls.append(kwargs)
        if self.persist_error is not None:
            raise self.persist_error
        return self._repo.add_message(
            kwargs["conversation_id"],
            role="assistant",
            text=kwargs["result"]["response"],
            metadata={
                key: kwargs["result"].get(key)
                for key in (
                    "citations",
                    "citation_status",
                    "understanding",
                    "confirmation",
                    "agent_state",
                    "delivery_status",
                    "provider",
                    "model",
                )
            },
        )


class _FakeRoutingDecision:
    def __init__(self, *, risk_level: str = "high"):
        self.intent = "deployment"
        self.risk_level = risk_level
        self.confidence = 0.91

    def to_dict(self):
        return {
            "intent": self.intent,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
        }


class _FailingRagService:
    async def retrieve_context(self, *args, **kwargs):
        raise AssertionError("light chat must not retrieve RAG context")


def _parse_sse_chunks(chunks: list[str]) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    for chunk in chunks:
        event_name = "message"
        data_lines: list[str] = []
        for line in chunk.strip().splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
        if not data_lines:
            events.append((event_name, None))
            continue
        raw = "\n".join(data_lines)
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        events.append((event_name, payload))
    return events


class _MetricRecorder:
    def __init__(self, *, before_observe=None):
        self.calls = []
        self._labels = {}
        self._before_observe = before_observe

    def labels(self, **labels):
        self._labels = labels
        return self

    def inc(self, value=1):
        self.calls.append(("inc", dict(self._labels), value))

    def observe(self, value):
        if self._before_observe is not None:
            self._before_observe()
        self.calls.append(("observe", dict(self._labels), value))


@pytest.mark.asyncio
async def test_streaming_service_emits_protocol_partial_and_done():
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
    )

    lines = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="hello",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )
    ]

    assert any(line.startswith("event: protocol") for line in lines), lines
    assert any(line.startswith("event: token") for line in lines), lines
    assert any(line.startswith("event: partial") for line in lines), lines
    assert any(line.startswith("event: done") for line in lines), lines
    assert len(msg_orch.persist_calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("strategy", "message", "expected_text", "expected_model"),
    [
        (TurnStrategy.STATIC_DISCOVERY, "quais ferramentas", "discovery", "discovery"),
        (TurnStrategy.STATIC_DOCS, "como usar a ferramenta", "docs", "tools_docs"),
        (
            TurnStrategy.STATIC_CAPABILITIES,
            "o que você pode fazer",
            "capabilities",
            "capabilities",
        ),
    ],
)
async def test_group2_static_sse_persists_before_tokens_and_skips_dynamic_work(
    monkeypatch,
    strategy,
    message,
    expected_text,
    expected_model,
):
    repo = _FakeRepo()
    llm = _FakeLLM()
    prompt = _FakePromptService()
    msg_orch = _FakeMessageOrchestration(
        llm,
        repo=repo,
        static_strategy=strategy,
    )

    def _assert_persisted_before_ttft():
        assert [message[1] for message in repo.messages] == ["user", "assistant"]

    ttft = _MetricRecorder(before_observe=_assert_persisted_before_ttft)
    monkeypatch.setattr(
        "app.services.chat.streaming_service.CHAT_TTFT_SECONDS",
        ttft,
    )
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=prompt,
        rag_service=_FailingRagService(),
        conversation_service=ConversationService(repo),
        message_orchestration_service=msg_orch,
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message=message,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )
    ]
    events = _parse_sse_chunks(chunks)
    names = [name for name, _ in events]
    token_text = "".join(
        payload["text"]
        for name, payload in events
        if name == "token" and isinstance(payload, dict)
    )
    done = next(payload for name, payload in events if name == "done")

    assert names[:4] == ["start", "protocol", "ack", "cognitive_status"]
    assert names.index("token") < names.index("partial") < names.index("done")
    assert token_text == expected_text
    assert done["provider"] == "janus"
    assert done["model"] == expected_model
    assert done["citations"] == []
    assert done["citation_status"]["status"] == "not_applicable"
    assert done["confirmation"] is None
    assert done["agent_state"]["state"] == "completed"
    assert done["delivery_status"] == "completed"
    assert len(msg_orch.persist_calls) == 1
    persisted = msg_orch.persist_calls[0]["result"]
    assert persisted["response"] == expected_text
    assert persisted["role"] == ModelRole.ORCHESTRATOR.value
    assert persisted["provider"] == done["provider"]
    assert persisted["model"] == done["model"]
    assert persisted["citations"] == done["citations"]
    assert persisted["citation_status"] == done["citation_status"]
    assert persisted["delivery_status"] == done["delivery_status"]
    assert repo.recent_calls == 0
    assert prompt.build_calls == 0
    assert llm.calls == []
    assert msg_orch.dynamic_calls == 0
    assert msg_orch.grounded_calls == 0
    assert msg_orch.calls == 0
    assert len(ttft.calls) == 1


@pytest.mark.asyncio
async def test_group2_static_sse_persistence_failure_emits_error_without_success_done(
    monkeypatch,
):
    repo = _FakeRepo()
    llm = _FakeLLM()
    msg_orch = _FakeMessageOrchestration(
        llm,
        repo=repo,
        static_strategy=TurnStrategy.STATIC_DOCS,
    )
    msg_orch.persist_error = RuntimeError("write failed")
    message_metrics = _MetricRecorder()
    error_metrics = _MetricRecorder()
    monkeypatch.setattr(
        "app.services.chat.streaming_service.CHAT_MESSAGES_TOTAL",
        message_metrics,
    )
    monkeypatch.setattr(
        "app.services.chat.streaming_service.CHAT_ERRORS_TOTAL",
        error_metrics,
    )
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=ConversationService(repo),
        message_orchestration_service=msg_orch,
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="docs",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )
    ]
    events = _parse_sse_chunks(chunks)
    names = [name for name, _ in events]

    assert "error" in names
    assert "token" not in names
    assert "partial" not in names
    assert "done" not in names
    assert [message[1] for message in repo.messages] == ["user"]
    assert sum(
        1
        for operation, labels, _ in message_metrics.calls
        if operation == "inc" and labels == {"role": "assistant", "outcome": "error"}
    ) == 1
    assert not any(
        labels == {"role": "assistant", "outcome": "success"}
        for _, labels, _ in message_metrics.calls
    )
    assert len(error_metrics.calls) == 1


@pytest.mark.asyncio
async def test_streaming_service_light_chat_skips_rag_grounding_and_optional_citations(monkeypatch):
    async def _explode_collect_citations(**kwargs):
        raise AssertionError("light chat must not collect optional citations")

    monkeypatch.setattr(
        "app.services.chat.streaming_service.collect_chat_citations",
        _explode_collect_citations,
    )
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=_FailingRagService(),
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="Ola",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )
    ]
    events = _parse_sse_chunks(chunks)
    done = [p for e, p in events if e == "done" and isinstance(p, dict)][-1]

    assert msg_orch.grounded_calls == 0
    assert llm.calls
    assert llm.calls[-1]["task_type"] == "general_task"
    assert llm.calls[-1]["complexity"] == "low"
    assert llm.calls[-1]["timeout_seconds"] == 12
    assert done["citation_status"]["status"] == "not_applicable"
    assert any(event == "token" for event, _ in events), events


@pytest.mark.asyncio
async def test_streaming_service_sse_high_risk_emits_confirmation_and_waiting_state(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    class FakePendingActions:
        def resolve_chat_confirmation(self, **kwargs):
            understanding = kwargs.get("understanding") or {}
            assert understanding.get("requires_confirmation") is True
            assert understanding.get("confirmation_reason") == "high_risk"
            return 999, "high_risk"

    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
        pending_action_service=FakePendingActions(),
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="execute deploy in production now",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            requested_role="auto",
            routing_decision=_FakeRoutingDecision(risk_level="high"),
            route_applied=True,
        )
    ]
    events = _parse_sse_chunks(chunks)

    done_events = [p for e, p in events if e == "done" and isinstance(p, dict)]
    assert done_events, events
    done = done_events[-1]
    assert done["confirmation"]["pending_action_id"] == 999
    assert done["confirmation"]["required"] is True
    assert done["agent_state"]["state"] == "waiting_confirmation"
    assert done["understanding"]["requires_confirmation"] is True
    assert done["understanding"]["confirmation_reason"] == "high_risk"
    assert len(msg_orch.persist_calls) == 1
    assert msg_orch.persist_calls[0]["result"]["confirmation"]["pending_action_id"] == 999

    waiting_events = [
        p
        for e, p in events
        if e == "cognitive_status" and isinstance(p, dict) and p.get("state") == "waiting_confirmation"
    ]
    assert waiting_events, events


@pytest.mark.asyncio
async def test_streaming_service_sse_non_risk_does_not_emit_confirmation(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    class FakePendingActions:
        def resolve_chat_confirmation(self, **kwargs):
            return None, None

    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
        pending_action_service=FakePendingActions(),
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="hello docs",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            requested_role="auto",
            routing_decision=_FakeRoutingDecision(risk_level="low"),
            route_applied=True,
        )
    ]
    events = _parse_sse_chunks(chunks)
    done = [p for e, p in events if e == "done" and isinstance(p, dict)][-1]
    assert not done.get("confirmation")
    assert (done.get("agent_state") or {}).get("state") != "waiting_confirmation"


@pytest.mark.asyncio
async def test_streaming_service_missing_required_citations_emits_and_persists_guard(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
    )

    monkeypatch.setattr(
        "app.services.chat.streaming_service.build_citation_status",
        lambda **kwargs: {
            "mode": "required",
            "status": "missing_required",
            "count": 0,
            "reason": "no_retrievable_sources",
        },
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="Onde está a documentação da API",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )
    ]
    events = _parse_sse_chunks(chunks)
    done = [p for e, p in events if e == "done" and isinstance(p, dict)][-1]

    assert done["citation_status"]["status"] in {"missing_required", "present"}
    studying_events = [
        p
        for e, p in events
        if e == "cognitive_status" and isinstance(p, dict) and p.get("state") == "studying_codebase"
    ]
    assert studying_events, events
    token_text = "".join(
        str(payload.get("text") or "")
        for event, payload in events
        if event == "token" and isinstance(payload, dict)
    )
    assert token_text
    assert token_text != MANDATORY_CITATION_GUARD_TEXT
    assert repo.messages[-1][0:3] == ("conv-1", "assistant", token_text)


@pytest.mark.asyncio
async def test_streaming_service_missing_required_citations_with_knowledge_space_skips_repo_study(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
    )

    monkeypatch.setattr(
        "app.services.chat.streaming_service.build_citation_status",
        lambda **kwargs: {
            "mode": "required",
            "status": "missing_required",
            "count": 0,
            "reason": "no_retrievable_sources",
        },
    )

    chunks = [
        line
        async for line in streaming.stream_message(
            conversation_id="conv-1",
            message="Monte uma ficha usando o livro",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            knowledge_space_id="ks-1",
        )
    ]
    events = _parse_sse_chunks(chunks)

    reviewing_events = [
        p
        for e, p in events
        if e == "cognitive_status"
        and isinstance(p, dict)
        and p.get("state") == "reviewing_knowledge_space"
    ]
    assert reviewing_events, events
    token_text = "".join(
        str(payload.get("text") or "")
        for event, payload in events
        if event == "token" and isinstance(payload, dict)
    )
    assert "não vou estudar o código do janus" in token_text.lower()


@pytest.mark.asyncio
async def test_streaming_service_document_grounding_short_circuits_llm():
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm, repo=repo)
    msg_orch.grounded_result = {
        "response": "Do documento:\n- O texto menciona facial droop.",
        "provider": "janus",
        "model": "document_grounding",
        "citations": [
            {
                "doc_id": "doc-1",
                "title": "stroke.txt",
                "source_type": "document",
                "snippet": "facial droop",
            }
        ],
        "citation_status": {"mode": "optional", "status": "present", "count": 1, "reason": None},
    }
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
    )

    events = _parse_sse_chunks(
        [
            line
            async for line in streaming.stream_message(
                conversation_id="conv-1",
                message="Quais sinais o documento cita",
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.HIGH_QUALITY,
            )
        ]
    )

    done = [payload for event, payload in events if event == "done" and isinstance(payload, dict)][-1]
    assert done["model"] == "document_grounding"
    assert done["citation_status"]["status"] == "present"
    assert len(msg_orch.persist_calls) == 1
    assert msg_orch.persist_calls[0]["result"]["model"] == "document_grounding"
    token_text = "".join(
        str(payload.get("text") or "")
        for event, payload in events
        if event == "token" and isinstance(payload, dict)
    )
    assert "facial droop" in token_text
