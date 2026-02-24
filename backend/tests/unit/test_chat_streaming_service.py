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
