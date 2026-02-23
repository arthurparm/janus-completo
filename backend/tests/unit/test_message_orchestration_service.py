import pytest

from app.core.exceptions.chat_exceptions import MessageTooLargeError
from app.core.llm import ModelPriority, ModelRole
from app.repositories.chat_repository import ChatRepositoryError
from app.services.chat.conversation_service import ConversationService
from app.services.chat.message_orchestration_service import MessageOrchestrationService


class _FakeRepo:
    def __init__(self):
        self.conversation = {"persona": "assistant", "summary": None, "messages": []}
        self.messages = []

    def get_conversation(self, conversation_id):
        if conversation_id != "conv-1":
            raise ChatRepositoryError("Conversation not found: conv-1")
        return self.conversation

    def get_recent_messages(self, conversation_id, limit=60):
        return [{"role": "user", "text": "previous"}]

    def add_message(self, conversation_id, role, text):
        self.messages.append((conversation_id, role, text))


class _FakePromptService:
    def __init__(self):
        self.discovery = False
        self.docs = False
        self.capabilities = False
        self.tool_request = False

    async def build_prompt(self, persona, history, message, summary, relevant_memories):
        return f"{persona}:{message}"

    def estimate_tokens(self, text):
        return max(1, len(text) // 4)

    def is_discovery_query(self, message):
        return self.discovery

    def render_discovery_intro(self, tools):
        return "discovery response"

    def is_docs_query(self, message):
        return self.docs

    def render_tools_documentation(self, tools):
        return "docs response"

    def is_capabilities_query(self, message):
        return self.capabilities

    def render_local_capabilities(self, tools):
        return "capabilities response"

    def is_tool_request(self, message):
        return self.tool_request


class _FakeCommandHandler:
    def __init__(self, enabled=False, response=None):
        self.enabled = enabled
        self.response = response

    def is_command(self, message):
        return self.enabled

    async def handle_command(self, message, conversation_id, user_id):
        return self.response


class _FakeAgentLoop:
    def __init__(self):
        self.calls = 0

    async def run_loop(self, **kwargs):
        self.calls += 1
        return {
            "response": "resposta do agent loop",
            "provider": "dummy",
            "model": "m",
            "role": "assistant",
        }


class _FakeRagService:
    def __init__(self):
        self.index_calls = 0
        self.summary_calls = 0

    async def retrieve_context(self, message, user_id=None, conversation_id=None):
        return [{"content": "ctx"}]

    async def maybe_index_message(self, text, user_id=None, conversation_id=None, role=None):
        self.index_calls += 1

    async def maybe_summarize(
        self, conversation_id, role=None, priority=None, user_id=None, project_id=None
    ):
        self.summary_calls += 1


class _FakeOutboxService:
    def __init__(self):
        self.calls = []

    def enqueue_consolidation(self, payload, aggregate_id, dedupe_key):
        self.calls.append((payload, aggregate_id, dedupe_key))


class _FakeConversationService(ConversationService):
    def __init__(self):
        self.validations = []

    def validate_conversation_access(self, conversation_id, conv, user_id, project_id):
        self.validations.append((conversation_id, user_id, project_id))


def _build_service(
    repo=None,
    prompt_service=None,
    command_handler=None,
    agent_loop=None,
    rag_service=None,
    outbox_service=None,
):
    return MessageOrchestrationService(
        repo=repo or _FakeRepo(),
        llm_service=object(),
        tool_service=None,
        prompt_service=prompt_service or _FakePromptService(),
        rag_service=rag_service,
        command_handler=command_handler or _FakeCommandHandler(),
        agent_loop=agent_loop or _FakeAgentLoop(),
        conversation_service=_FakeConversationService(),
        outbox_service=outbox_service,
    )


@pytest.mark.asyncio
async def test_send_message_command_shortcut_persists_and_returns_understanding():
    repo = _FakeRepo()
    prompt = _FakePromptService()
    command = _FakeCommandHandler(enabled=True, response="Use /help para comandos")
    service = _build_service(repo=repo, prompt_service=prompt, command_handler=command)

    result = await service.send_message(
        conversation_id="conv-1",
        message="como usar?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )

    assert repo.messages[0] == ("conv-1", "user", "como usar?")
    assert repo.messages[1] == ("conv-1", "assistant", "Use /help para comandos")
    assert result["provider"] == "janus"
    assert result["model"] == "quick_command"
    assert result["conversation_id"] == "conv-1"
    assert result["understanding"]["intent"] == "question"


@pytest.mark.asyncio
async def test_send_message_rejects_large_payload(monkeypatch):
    repo = _FakeRepo()
    service = _build_service(repo=repo, prompt_service=_FakePromptService())
    monkeypatch.setenv("CHAT_MAX_MESSAGE_BYTES", "8")

    with pytest.raises(MessageTooLargeError):
        await service.send_message(
            conversation_id="conv-1",
            message="mensagem grande demais",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )


@pytest.mark.asyncio
async def test_send_message_agent_loop_path_persists_and_enqueues_post_event():
    repo = _FakeRepo()
    prompt = _FakePromptService()
    command = _FakeCommandHandler(enabled=False, response=None)
    agent_loop = _FakeAgentLoop()
    rag = _FakeRagService()
    outbox = _FakeOutboxService()
    service = _build_service(
        repo=repo,
        prompt_service=prompt,
        command_handler=command,
        agent_loop=agent_loop,
        rag_service=rag,
        outbox_service=outbox,
    )

    result = await service.send_message(
        conversation_id="conv-1",
        message="mensagem normal",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
        user_id="user-1",
        project_id="proj-1",
    )

    assert agent_loop.calls == 1
    assert ("conv-1", "assistant", "resposta do agent loop") in repo.messages
    assert result["conversation_id"] == "conv-1"
    assert result["response"] == "resposta do agent loop"
    assert len(outbox.calls) == 1
    payload, aggregate_id, dedupe_key = outbox.calls[0]
    assert aggregate_id == "conv-1"
    assert payload["metadata"]["user_id"] == "user-1"
    assert dedupe_key.startswith("consolidation:conv-1:")
