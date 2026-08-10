import json

import pytest
from app.core.llm import ModelPriority, ModelRole
from app.services.chat.chat_citation_service import (
    references_uploaded_material,
    requires_mandatory_citations,
)
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

    def get_conversation(self, conversation_id):
        if conversation_id != "conv-1":
            raise ValueError("missing")
        return self.conv

    def add_message(self, conversation_id, role, text, metadata=None):
        payload = {"id": "55", "text": text, **(metadata or {})}
        self.messages.append((conversation_id, role, text, metadata or {}))
        return payload

    def get_recent_messages(self, conversation_id, limit=20):
        return []


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
    async def build_prompt(self, persona, history, message, summary, relevant_memories):
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

    def render_local_capabilities(self, tools):
        return "capabilities"


class _FakeMessageOrchestration:
    def __init__(self, llm_service):
        self.calls = 0
        self.grounded_calls = 0
        self.grounded_result = None
        self._llm = llm_service
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
                risk_level=risk_level,
            ),
        )

    async def execute_dynamic_turn(self, *, plan, request, prompt, persona):
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

    def execute_static_turn(self, *, strategy, role):
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
            model=strategy.value,
            role=role.value,
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


@pytest.mark.asyncio
async def test_streaming_service_emits_protocol_partial_and_done():
    repo = _FakeRepo()
    llm = _FakeLLM()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration(llm)
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
    msg_orch = _FakeMessageOrchestration(llm)
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
    msg_orch = _FakeMessageOrchestration(llm)
    streaming = StreamingService(
        repo=repo,
        llm_service=llm,
        tool_service=None,
        prompt_service=_FakePromptService(),
        rag_service=None,
        conversation_service=convo_service,
        message_orchestration_service=msg_orch,
    )

    def _fake_fallback_pending_action(**kwargs):
        understanding = kwargs.get("understanding") or {}
        assert understanding.get("requires_confirmation") is True
        assert understanding.get("confirmation_reason") == "high_risk"
        return 999, "high_risk"

    monkeypatch.setattr(
        "app.services.chat.streaming_service.maybe_create_fallback_pending_action",
        _fake_fallback_pending_action,
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
    msg_orch = _FakeMessageOrchestration(llm)
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
        "app.services.chat.streaming_service.maybe_create_fallback_pending_action",
        lambda **kwargs: (None, None),
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
    msg_orch = _FakeMessageOrchestration(llm)
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
    msg_orch = _FakeMessageOrchestration(llm)
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
    msg_orch = _FakeMessageOrchestration(llm)
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
    token_text = "".join(
        str(payload.get("text") or "")
        for event, payload in events
        if event == "token" and isinstance(payload, dict)
    )
    assert "facial droop" in token_text
