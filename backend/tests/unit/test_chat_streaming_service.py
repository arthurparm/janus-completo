import json

import pytest

from app.core.llm import ModelPriority, ModelRole
from app.services.chat.conversation_service import ConversationService
from app.services.chat.streaming_service import StreamingService


class _FakeRepo:
    def __init__(self):
        self.messages = []
        self.conv = {"persona": "assistant", "summary": None, "messages": []}

    def get_conversation(self, conversation_id):
        if conversation_id != "conv-1":
            raise ValueError("missing")
        return self.conv

    def add_message(self, conversation_id, role, text):
        self.messages.append((conversation_id, role, text))

    def get_recent_messages(self, conversation_id, limit=20):
        return []


class _FakeLLM:
    def select_provider(self, role, priority, user_id=None, project_id=None):
        return {"provider": "dummy", "model": "m"}

    def is_provider_open(self, provider: str) -> bool:
        return False

    def invoke_llm(
        self, prompt, role, priority, timeout_seconds=None, user_id=None, project_id=None
    ):
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
    def __init__(self):
        self.calls = 0

    def trigger_post_response_events(
        self, conversation_id, user_message, assistant_text, result, user_id, project_id
    ):
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
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration()
    streaming = StreamingService(
        repo=repo,
        llm_service=_FakeLLM(),
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
    assert msg_orch.calls == 1


@pytest.mark.asyncio
async def test_streaming_service_sse_high_risk_emits_confirmation_and_waiting_state(monkeypatch):
    repo = _FakeRepo()
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration()
    streaming = StreamingService(
        repo=repo,
        llm_service=_FakeLLM(),
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
            user_id="1",
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
    convo_service = ConversationService(repo)
    msg_orch = _FakeMessageOrchestration()
    streaming = StreamingService(
        repo=repo,
        llm_service=_FakeLLM(),
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
            user_id="1",
            requested_role="auto",
            routing_decision=_FakeRoutingDecision(risk_level="low"),
            route_applied=True,
        )
    ]
    events = _parse_sse_chunks(chunks)
    done = [p for e, p in events if e == "done" and isinstance(p, dict)][-1]
    assert not done.get("confirmation")
    assert (done.get("agent_state") or {}).get("state") != "waiting_confirmation"
