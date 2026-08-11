import asyncio
from unittest.mock import AsyncMock

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
        self.message_records = []
        self.recent_calls = 0

    def get_conversation(self, conversation_id):
        if conversation_id != "conv-1":
            raise ChatRepositoryError("Conversation not found: conv-1")
        return self.conversation

    def get_recent_messages(self, conversation_id, limit=60):
        self.recent_calls += 1
        return [{"role": "user", "text": "previous"}]

    def add_message(self, conversation_id, role, text, metadata=None):
        self.messages.append((conversation_id, role, text))
        self.message_records.append(
            {
                "conversation_id": conversation_id,
                "role": role,
                "text": text,
                "metadata": metadata or {},
            }
        )
        return {"id": str(len(self.message_records)), "role": role, "text": text}


class _FakePromptService:
    def __init__(self):
        self.discovery = False
        self.docs = False
        self.capabilities = False
        self.tool_request = False
        self.build_calls = 0

    async def build_prompt(self, persona, history, message, summary, relevant_memories):
        self.build_calls += 1
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

    def render_local_capabilities(self):
        return "capabilities response"

    def is_tool_request(self, message):
        return self.tool_request


class _FakeCommandHandler:
    def __init__(self, enabled=False, response=None):
        self.enabled = enabled
        self.response = response

    def is_command(self, message):
        return self.enabled

    async def handle_command(self, message, conversation_id, user_id=None):
        return self.response


class _FakeAgentLoop:
    def __init__(self):
        self.calls = 0
        self.kwargs = None

    async def run_loop(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return {
            "response": "resposta do agent loop",
            "provider": "dummy",
            "model": "m",
            "role": "assistant",
        }


class _FakeLLMService:
    def __init__(self, response="resposta do llm"):
        self.calls = []
        self.response = response

    async def invoke_llm(self, **kwargs):
        self.calls.append(kwargs)
        response = self.response
        if isinstance(response, list):
            response = response.pop(0)
        return {
            "response": response,
            "provider": "dummy-llm",
            "model": "light-model",
            "role": kwargs["role"].value,
        }


class _FakeRagService:
    def __init__(self):
        self.retrieve_calls = 0
        self.retrieve_kwargs = None
        self.index_calls = 0
        self.index_kwargs = []
        self.summary_calls = 0

    async def retrieve_context(self, message, **kwargs):
        self.retrieve_calls += 1
        self.retrieve_kwargs = kwargs
        return [{"content": "ctx"}]

    async def maybe_index_message(self, text, **kwargs):
        self.index_calls += 1
        self.index_kwargs.append(kwargs)

    async def maybe_summarize(
        self, conversation_id, role=None, priority=None, project_id=None
    ):
        self.summary_calls += 1


class _FakeOutboxService:
    def __init__(self):
        self.calls = []

    def enqueue_consolidation(self, payload, aggregate_id, dedupe_key):
        self.calls.append((payload, aggregate_id, dedupe_key))


class _MetricRecorder:
    def __init__(self):
        self.calls = []
        self._labels = {}

    def labels(self, **labels):
        self._labels = labels
        return self

    def inc(self, value=1):
        self.calls.append((dict(self._labels), value))

    def observe(self, value):
        self.calls.append((dict(self._labels), value))


class _FakeConversationService(ConversationService):
    def __init__(self):
        self.validations = []

    def validate_conversation_access(
        self,
        conversation_id,
        conv,
        user_id=None,
        project_id=None,
    ):
        self.validations.append((conversation_id, user_id, project_id))


class _FakeManifestRepo:
    def __init__(self, rows=None):
        self.rows = rows or []

    def list_manifests(self, **kwargs):
        return list(self.rows)


@pytest.fixture(autouse=True)
def _stub_active_memory_capture(monkeypatch):
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.active_memory_service.maybe_capture_from_message",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.procedural_memory_service.list_rules",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.secret_memory_service.should_authorize_prompt_recall",
        lambda _message: False,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.secret_memory_service.list_secrets",
        AsyncMock(return_value=[]),
    )


def _build_service(
    repo=None,
    llm_service=None,
    prompt_service=None,
    command_handler=None,
    agent_loop=None,
    rag_service=None,
    outbox_service=None,
    manifest_repo=None,
    tool_service=None,
):
    return MessageOrchestrationService(
        repo=repo or _FakeRepo(),
        llm_service=llm_service or _FakeLLMService(),
        tool_service=tool_service,
        prompt_service=prompt_service or _FakePromptService(),
        rag_service=rag_service,
        command_handler=command_handler or _FakeCommandHandler(),
        agent_loop=agent_loop or _FakeAgentLoop(),
        conversation_service=_FakeConversationService(),
        outbox_service=outbox_service,
        manifest_repo=manifest_repo or _FakeManifestRepo(),
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
    assert result["understanding"]["intent"] == "command"
    assert result["understanding"]["confidence"] == 1.0


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
@pytest.mark.parametrize(
    ("flag", "message", "expected_model", "expected_text"),
    [
        ("discovery", "quais ferramentas", "discovery", "discovery response"),
        ("docs", "como usar a ferramenta", "tools_docs", "docs response"),
    ],
)
async def test_group2_static_turn_persists_once_with_complete_metadata_and_no_knowledge_effects(
    flag,
    message,
    expected_model,
    expected_text,
):
    repo = _FakeRepo()
    prompt = _FakePromptService()
    setattr(prompt, flag, True)
    rag = _FakeRagService()
    outbox = _FakeOutboxService()
    llm = _FakeLLMService()
    agent_loop = _FakeAgentLoop()
    service = _build_service(
        repo=repo,
        prompt_service=prompt,
        rag_service=rag,
        outbox_service=outbox,
        llm_service=llm,
        agent_loop=agent_loop,
    )

    result = await service.send_message(
        conversation_id="conv-1",
        message=message,
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
        user_id="user-1",
        project_id="project-1",
    )
    await asyncio.sleep(0)

    assert [record["role"] for record in repo.message_records] == ["user", "assistant"]
    assistant = repo.message_records[1]
    assert assistant["text"] == expected_text
    assert assistant["metadata"] == {
        "knowledge_space_id": None,
        "mode_used": None,
        "base_used": None,
        "answer_strategy": None,
        "estimated_wait_seconds": None,
        "estimated_wait_range_seconds": None,
        "processing_profile": None,
        "processing_notice": None,
        "evidence_count": None,
        "source_roles_used": None,
        "source_scope": None,
        "gaps_or_conflicts": None,
        "citations": [],
        "citation_status": {
            "mode": "optional",
            "status": "not_applicable",
            "count": 0,
            "reason": None,
        },
        "ui": None,
        "understanding": result["understanding"],
        "confirmation": None,
        "agent_state": result["agent_state"],
        "delivery_status": "completed",
        "failure_classification": None,
        "provider": "janus",
        "model": expected_model,
    }
    assert result["response"] == expected_text
    assert result["provider"] == "janus"
    assert result["model"] == expected_model
    assert result["citations"] == []
    assert result["citation_status"]["status"] == "not_applicable"
    assert result["delivery_status"] == "completed"
    assert result["confirmation"] is None
    assert result["message_id"] == "2"
    assert repo.recent_calls == 0
    assert prompt.build_calls == 0
    assert llm.calls == []
    assert agent_loop.calls == 0
    assert rag.retrieve_calls == 0
    assert rag.index_calls == 0
    assert rag.summary_calls == 1
    assert outbox.calls == []


@pytest.mark.asyncio
async def test_static_summarization_is_fail_open_after_assistant_persistence():
    class FailingSummaryRag(_FakeRagService):
        async def maybe_summarize(self, *args, **kwargs):
            self.summary_calls += 1
            raise RuntimeError("summary unavailable")

    repo = _FakeRepo()
    prompt = _FakePromptService()
    prompt.discovery = True
    rag = FailingSummaryRag()
    service = _build_service(repo=repo, prompt_service=prompt, rag_service=rag)

    result = await service.send_message(
        conversation_id="conv-1",
        message="quais ferramentas",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )

    assert result["delivery_status"] == "completed"
    assert [record["role"] for record in repo.message_records] == ["user", "assistant"]
    assert rag.summary_calls == 1


@pytest.mark.asyncio
async def test_static_metrics_are_recorded_once_after_final_persistence(monkeypatch):
    repo = _FakeRepo()
    prompt = _FakePromptService()
    prompt.docs = True
    messages = _MetricRecorder()
    tokens = _MetricRecorder()
    spend = _MetricRecorder()
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.CHAT_MESSAGES_TOTAL",
        messages,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.CHAT_TOKENS_TOTAL",
        tokens,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.CHAT_SPEND_USD_TOTAL",
        spend,
    )
    service = _build_service(repo=repo, prompt_service=prompt)

    await service.send_message(
        conversation_id="conv-1",
        message="docs da tool",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )

    assert messages.calls.count(({"role": "user", "outcome": "accepted"}, 1)) == 1
    assert messages.calls.count(({"role": "assistant", "outcome": "success"}, 1)) == 1
    assert ({"role": "assistant", "outcome": "error"}, 1) not in messages.calls
    assert len(tokens.calls) == 1
    assert tokens.calls[0][0] == {"direction": "out"}
    assert spend.calls == []


@pytest.mark.asyncio
async def test_static_persistence_failure_records_error_without_success(monkeypatch):
    class FailingAssistantRepo(_FakeRepo):
        def add_message(self, conversation_id, role, text, metadata=None):
            if role == "assistant":
                raise RuntimeError("assistant write failed")
            return super().add_message(conversation_id, role, text, metadata)

    repo = FailingAssistantRepo()
    prompt = _FakePromptService()
    prompt.docs = True
    messages = _MetricRecorder()
    errors = _MetricRecorder()
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.CHAT_MESSAGES_TOTAL",
        messages,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.CHAT_ERRORS_TOTAL",
        errors,
    )
    service = _build_service(repo=repo, prompt_service=prompt)

    with pytest.raises(RuntimeError, match="assistant write failed"):
        await service.send_message(
            conversation_id="conv-1",
            message="como usar a ferramenta",
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
        )

    assert messages.calls.count(({"role": "assistant", "outcome": "error"}, 1)) == 1
    assert ({"role": "assistant", "outcome": "success"}, 1) not in messages.calls
    assert errors.calls == [({"code": "InvocationError"}, 1)]
    assert [record["role"] for record in repo.message_records] == ["user"]


@pytest.mark.asyncio
async def test_negative_group2_message_continues_to_existing_light_llm_path():
    repo = _FakeRepo()
    prompt = _FakePromptService()
    llm = _FakeLLMService(response="dynamic response")
    service = _build_service(repo=repo, prompt_service=prompt, llm_service=llm)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Qual é o status?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )

    assert result["response"] == "dynamic response"
    assert len(llm.calls) == 1
    assert prompt.build_calls == 1


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
        message="Implemente uma rotina de deploy com rollback e validacao completa.",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
        user_id="user-1",
        project_id="proj-1",
    )
    await asyncio.sleep(0)

    assert agent_loop.calls == 1
    assert ("conv-1", "assistant", "resposta do agent loop") in repo.messages
    assert result["conversation_id"] == "conv-1"
    assert result["response"] == "resposta do agent loop"
    assert rag.retrieve_kwargs["user_id"] == "user-1"
    assert {call["user_id"] for call in rag.index_kwargs} == {"user-1"}
    assert len(outbox.calls) == 1
    payload, aggregate_id, dedupe_key = outbox.calls[0]
    assert aggregate_id == "conv-1"
    assert dedupe_key.startswith("consolidation:conv-1:")


@pytest.mark.asyncio
async def test_send_message_light_chat_bypasses_agent_loop_and_skips_rag_lookup(monkeypatch):
    repo = _FakeRepo()
    prompt = _FakePromptService()
    llm = _FakeLLMService(response="resposta leve")
    agent_loop = _FakeAgentLoop()
    rag = _FakeRagService()
    outbox = _FakeOutboxService()
    scheduled = []
    original_create_task = asyncio.create_task

    def _track_task(coro):
        task = original_create_task(coro)
        scheduled.append(task)
        return task

    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.asyncio.create_task",
        _track_task,
    )

    service = _build_service(
        repo=repo,
        llm_service=llm,
        prompt_service=prompt,
        agent_loop=agent_loop,
        rag_service=rag,
        outbox_service=outbox,
    )

    result = await service.send_message(
        conversation_id="conv-1",
        message="Qual é o status do sistema?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
        user_id="user-1",
        project_id="proj-1",
    )
    await asyncio.gather(*scheduled)

    assert agent_loop.calls == 0
    assert len(llm.calls) == 1
    assert rag.retrieve_calls == 0
    assert rag.index_calls == 2
    assert result["provider"] == "dummy-llm"
    assert result["response"] == "resposta leve"


@pytest.mark.asyncio
async def test_send_message_document_grounding_uses_evidence_and_preserves_citations(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=(
            '{"answer":"O documento cita sinais neurologicos agudos.",'
            '"supported_points":[{"statement":"O texto menciona facial droop.",'
            '"citation_ids":[1]},{"statement":"O texto menciona speech disturbance.",'
            '"citation_ids":[1]}],'
            '"missing_information":[]}'
        )
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "status": "indexed",
                "chunks_indexed": 3,
                "file_name": "stroke.txt",
            }
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "doc-1",
                    "title": "stroke.txt",
                    "file_path": "stroke.txt",
                    "source_type": "document",
                    "snippet": "Ischemic stroke warning signs include facial droop and speech disturbance.",
                }
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Quais sinais de AVC o documento menciona?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert "Do documento:" in result["response"]
    assert "facial droop" in result["response"]
    assert "Nao encontrei no documento" not in result["response"]
    assert result["citations"][0]["doc_id"] == "doc-1"
    assert result["citation_status"]["status"] == "present"
    assert llm.calls


@pytest.mark.asyncio
async def test_send_message_document_grounding_returns_processing_notice_when_no_indexed_docs():
    repo = _FakeRepo()
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "status": "processing",
                "chunks_indexed": 0,
                "file_name": "stroke.txt",
            }
        ]
    )
    llm = _FakeLLMService()
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Analise o arquivo que eu mandei",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert "ainda estao sendo processados" in result["response"]
    assert result["model"] == "document_processing"
    assert result["citation_status"]["status"] == "not_applicable"
    assert not llm.calls


@pytest.mark.asyncio
async def test_send_message_document_grounding_ignores_processing_doc_chunks(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=(
            '{"answer":"O documento menciona facial droop e speech disturbance.",'
            '"supported_points":[{"statement":"Ha mencao a facial droop.","citation_ids":[1]}],'
            '"missing_information":[]}'
        )
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-indexed",
                "status": "indexed",
                "chunks_indexed": 1,
                "file_name": "indexed.txt",
            },
            {
                "doc_id": "doc-processing",
                "status": "processing",
                "chunks_indexed": 40,
                "file_name": "processing.txt",
            },
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            side_effect=[
                [
                    {
                        "doc_id": "doc-processing",
                        "title": "processing.txt",
                        "file_path": "processing.txt",
                        "source_type": "document",
                        "snippet": "Trecho parcial sem a resposta correta.",
                    }
                ],
                [
                    {
                        "doc_id": "doc-indexed",
                        "title": "indexed.txt",
                        "file_path": "indexed.txt",
                        "source_type": "document",
                        "snippet": "Ischemic stroke signs include facial droop and speech disturbance.",
                    }
                ],
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="No documento enviado, quais sinais de AVC aparecem?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert "facial droop" in result["response"]
    assert result["citations"][0]["doc_id"] == "doc-indexed"


@pytest.mark.asyncio
async def test_send_message_document_grounding_rechecks_false_negative_extraction(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=[
            (
                '{"answer":"Nenhum sinal especifico de AVC isquemico e mencionado.",'
                '"supported_points":[],"missing_information":["sinais especificos de AVC isquemico"]}'
            ),
            (
                '{"answered":true,"supported_points":[{"statement":"O documento menciona facial droop, arm weakness e speech disturbance.",'
                '"citation_ids":[1],"quote":"common acute warning signs of ischemic stroke include facial droop, arm weakness, and speech disturbance"}],'
                '"missing_information":[]}'
            ),
        ]
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "status": "indexed",
                "chunks_indexed": 1,
                "file_name": "stroke.txt",
            }
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "doc-1",
                    "title": "stroke.txt",
                    "file_path": "stroke.txt",
                    "source_type": "document",
                    "snippet": (
                        "The document states that common acute warning signs of ischemic stroke "
                        "include facial droop, arm weakness, and speech disturbance. Sudden "
                        "unilateral numbness can also occur."
                    ),
                }
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="No documento enviado, quais sinais de AVC isquemico sao mencionados?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert "facial droop" in result["response"]
    assert "speech disturbance" in result["response"]
    assert "Nao encontrei no documento" not in result["response"]
    assert len(llm.calls) == 2


@pytest.mark.asyncio
async def test_send_message_document_grounding_negative_omits_irrelevant_snippet(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=(
            '{"answered":false,"answer":"","supported_points":[],"missing_information":["diabetes mellitus"]}'
        )
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "status": "indexed",
                "chunks_indexed": 1,
                "file_name": "stroke.txt",
            }
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "doc-1",
                    "title": "stroke.txt",
                    "file_path": "stroke.txt",
                    "source_type": "document",
                    "snippet": "The document states that common acute warning signs of ischemic stroke include facial droop.",
                }
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="No documento enviado, ele fala sobre diabetes mellitus?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert "Nao encontrei no documento" in result["response"]
    assert "diabetes mellitus" in result["response"]
    assert "facial droop" not in result["response"]


@pytest.mark.asyncio
async def test_send_message_document_grounding_prefers_primary_source_for_operational_requests(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=(
            '{"response":"O manual principal descreve o procedimento passo a passo.",'
            '"used_citation_ids":[1],'
            '"missing_user_decisions":[],'
            '"source_gaps":[],'
            '"artifact_type":"procedure"}'
        )
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-core",
                "status": "indexed",
                "chunks_indexed": 50,
                "chunks_total": 50,
                "file_name": "Core Handbook.pdf",
            },
            {
                "doc_id": "doc-companion",
                "status": "indexed",
                "chunks_indexed": 20,
                "chunks_total": 20,
                "file_name": "Companion Guide.pdf",
            },
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "doc-companion",
                    "title": "Companion Guide.pdf",
                    "file_path": "Companion Guide.pdf",
                    "source_type": "document",
                    "snippet": "Companion material with extra options.",
                },
                {
                    "doc_id": "doc-core",
                    "title": "Core Handbook.pdf",
                    "file_path": "Core Handbook.pdf",
                    "source_type": "document",
                    "snippet": "Core handbook with the canonical step-by-step procedure.",
                },
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Crie o procedimento passo a passo usando os documentos enviados",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert result["citations"]
    assert {citation["doc_id"] for citation in result["citations"]} == {"doc-core"}
    assert "manual principal" in result["response"]


@pytest.mark.asyncio
async def test_send_message_document_grounding_allows_secondary_when_user_requests_it(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=(
            '{"response":"O manual principal cobre a base e o Companion Guide adiciona opções extras.",'
            '"used_citation_ids":[1,2],'
            '"missing_user_decisions":[],'
            '"source_gaps":[],'
            '"artifact_type":"procedure"}'
        )
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-core",
                "status": "indexed",
                "chunks_indexed": 50,
                "chunks_total": 50,
                "file_name": "Core Handbook.pdf",
            },
            {
                "doc_id": "doc-companion",
                "status": "indexed",
                "chunks_indexed": 20,
                "chunks_total": 20,
                "file_name": "Companion Guide.pdf",
            },
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "doc-companion",
                    "title": "Companion Guide.pdf",
                    "file_path": "Companion Guide.pdf",
                    "source_type": "document",
                    "snippet": "Companion material with extra options.",
                },
                {
                    "doc_id": "doc-core",
                    "title": "Core Handbook.pdf",
                    "file_path": "Core Handbook.pdf",
                    "source_type": "document",
                    "snippet": "Core handbook with the canonical step-by-step procedure.",
                },
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Crie o procedimento usando o Core Handbook e tambem o Companion Guide",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert result["citations"]
    assert {citation["doc_id"] for citation in result["citations"]} == {"doc-core", "doc-companion"}


@pytest.mark.asyncio
async def test_send_message_document_grounding_operational_task_returns_direct_artifact(monkeypatch):
    repo = _FakeRepo()
    llm = _FakeLLMService(
        response=(
            '{"response":"Ficha sugerida\\n- Classe: Cavaleiro\\n- Origem: Nobre\\n- Atributos priorizados: Força, Constituição e Carisma",'
            '"used_citation_ids":[1],'
            '"missing_user_decisions":["nome do personagem"],'
            '"source_gaps":["a fonte nao detalha o equipamento inicial completo neste trecho"],'
            '"artifact_type":"character_sheet"}'
        )
    )
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "status": "indexed",
                "chunks_indexed": 5,
                "chunks_total": 5,
                "file_name": "Livro Base.pdf",
            }
        ]
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.collect_document_citations",
        AsyncMock(
            return_value=[
                {
                    "doc_id": "doc-1",
                    "title": "Livro Base.pdf",
                    "file_path": "Livro Base.pdf",
                    "source_type": "document",
                    "snippet": "Cavaleiros nobres priorizam força, constituição e carisma para defender o reino.",
                }
            ]
        ),
    )
    service = _build_service(repo=repo, llm_service=llm, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Crie uma ficha de cavaleiro com base no livro enviado",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert result["response"].startswith("Ficha sugerida")
    assert "Do documento:" not in result["response"]
    assert "Decisões pendentes do usuário:" in result["response"]
    assert "Lacunas da fonte:" in result["response"]
    assert result["citation_status"]["status"] == "present"


@pytest.mark.asyncio
async def test_send_message_knowledge_space_path_prefers_canonical_answer(monkeypatch):
    repo = _FakeRepo()
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "status": "indexed",
                "chunks_indexed": 4,
                "file_name": "livro.pdf",
                "knowledge_space_id": "ks-1",
            }
        ]
    )
    query_space = AsyncMock(
        return_value={
            "answer": "Base consolidada indica:\n- Capítulo 1: ordem de estudo.",
            "mode_used": "canonical_answer",
            "base_used": "consolidated",
            "answer_strategy": "sequence",
            "evidence_count": 1,
            "source_roles_used": ["base"],
            "source_scope": {
                "knowledge_space_id": "ks-1",
                "consolidation_status": "ready",
            },
            "citations": [{"doc_id": "doc-1", "file_name": "livro.pdf"}],
            "confidence": 0.93,
            "gaps_or_conflicts": [],
        }
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.KnowledgeSpaceService.query_space",
        query_space,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.KnowledgeSpaceService.get_space",
        lambda self, *, knowledge_space_id: {
            "knowledge_space_id": knowledge_space_id,
            "consolidation_status": "ready",
        },
    )
    service = _build_service(repo=repo, manifest_repo=manifest_repo)

    result = await service.send_message(
        conversation_id="conv-1",
        message="Qual a sequência do material?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
    )

    assert result["knowledge_space_id"] == "ks-1"
    assert result["mode_used"] == "canonical_answer"
    assert result["base_used"] == "consolidated"
    assert result["source_scope"]["knowledge_space_id"] == "ks-1"
    assert "Base consolidada indica" in result["response"]
    assert repo.message_records[-1]["metadata"]["knowledge_space_id"] == "ks-1"
    assert repo.message_records[-1]["metadata"]["mode_used"] == "canonical_answer"
    assert repo.message_records[-1]["metadata"]["answer_strategy"] == "sequence"
    assert query_space.await_args.kwargs["mode"] == "auto"


def test_prefer_canonical_answer_for_comparative_question():
    service = _build_service()

    assert service._prefer_canonical_answer(
        "Como Heróis de Arton complementa o livro base? Diferencie o que cada um adiciona.",
        {"intent": "question"},
    )


def test_resolve_knowledge_space_mode_delegates_to_service_auto_mode():
    service = _build_service()

    mode = service._resolve_knowledge_space_mode(
        message="Como Heróis de Arton complementa o livro base?",
        understanding={"intent": "question"},
        requested_knowledge_space_id="ks-1",
        source_scope={"consolidation_status": "ready"},
    )

    assert mode == "auto"


def test_resolve_knowledge_space_mode_stays_auto_for_locator_prompt():
    service = _build_service()

    mode = service._resolve_knowledge_space_mode(
        message="Em que página o livro fala do treinador?",
        understanding={"intent": "question"},
        requested_knowledge_space_id="ks-1",
        source_scope={"consolidation_status": "ready"},
    )

    assert mode == "auto"


@pytest.mark.asyncio
async def test_send_message_standard_path_reuses_initial_prompt_and_single_rag_lookup(monkeypatch):
    repo = _FakeRepo()
    prompt = _FakePromptService()
    agent_loop = _FakeAgentLoop()
    rag = _FakeRagService()
    outbox = _FakeOutboxService()
    scheduled = []
    original_create_task = asyncio.create_task

    def _track_task(coro):
        task = original_create_task(coro)
        scheduled.append(task)
        return task

    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.asyncio.create_task",
        _track_task,
    )

    service = _build_service(
        repo=repo,
        prompt_service=prompt,
        agent_loop=agent_loop,
        rag_service=rag,
        outbox_service=outbox,
    )

    await service.send_message(
        conversation_id="conv-1",
        message="Implemente um endpoint de health check com teste.",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
        user_id="user-1",
        project_id="proj-1",
    )
    await asyncio.gather(*scheduled)

    assert agent_loop.calls == 1
    assert repo.recent_calls == 1
    assert prompt.build_calls == 1
    assert rag.retrieve_calls == 1
    assert rag.index_calls == 2
    assert agent_loop.kwargs["initial_prompt"] == "assistant:Implemente um endpoint de health check com teste."


@pytest.mark.asyncio
async def test_send_message_secret_recall_uses_explicit_authorized_path(monkeypatch):
    repo = _FakeRepo()
    service = _build_service(repo=repo)
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.secret_memory_service.should_authorize_prompt_recall",
        lambda _message: True,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.secret_memory_service.list_secrets",
        AsyncMock(
            return_value=[
                {
                    "secret_label": "senha ficticia do wi-fi",
                    "secret_value": "Abc12345",
                }
            ]
        ),
    )

    result = await service.send_message(
        conversation_id="conv-1",
        message="Qual é a minha senha fictícia do Wi-Fi?",
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
        user_id="user-1",
    )

    assert result["model"] == "secret_memory"
    assert result["response"] == "senha ficticia do wi-fi: Abc12345"


@pytest.mark.asyncio
async def test_secret_recall_ignores_ordinary_chat_message(monkeypatch):
    service = _build_service()
    list_secrets = AsyncMock(return_value=[])
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.secret_memory_service.should_authorize_prompt_recall",
        lambda _message: False,
    )
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.secret_memory_service.list_secrets",
        list_secrets,
    )

    result = await service.generate_secret_recall_reply(
        message="Quanto e dois mais dois?",
        role=ModelRole.ORCHESTRATOR,
        user_id="user-1",
        conversation_id="conv-1",
    )

    assert result is None
    list_secrets.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_response_memory_policies_appends_next_steps(monkeypatch):
    service = _build_service()
    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.procedural_memory_service.list_rules",
        AsyncMock(return_value=[{"scope": "closing"}]),
    )

    result = await service.apply_response_memory_policies(
        assistant_text="Resposta objetiva.",
        user_message="Explique cache invalidation.",
        user_id="user-1",
        conversation_id="conv-1",
    )

    assert "Próximos passos:" in result


def test_build_knowledge_space_runtime_notice_returns_estimate_for_resolved_space(monkeypatch):
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "knowledge_space_id": "ks-1",
                "status": "indexed",
                "chunks_indexed": 10,
            }
        ]
    )
    service = _build_service(manifest_repo=manifest_repo)

    class _FakeKnowledgeSpaceService:
        def __init__(self, manifest_repo=None, llm_service=None):
            self.manifest_repo = manifest_repo
            self.llm_service = llm_service

        def estimate_query_timing(self, **kwargs):
            return {
                "estimated_wait_seconds": 48,
                "estimated_wait_range_seconds": [35, 60],
                "processing_profile": "deep_task",
                "processing_notice": "Consulta profunda em andamento. Estimativa: 35-60s.",
                "estimated_mode": "canonical_answer",
                "estimated_answer_strategy": "task",
            }

    monkeypatch.setattr(
        "app.services.chat.message_orchestration_service.KnowledgeSpaceService",
        _FakeKnowledgeSpaceService,
    )

    result = service.build_knowledge_space_runtime_notice(
        conversation_id="conv-1",
        message="Crie uma ficha completa usando os livros.",
        requested_knowledge_space_id=None,
    )

    assert result is not None
    assert result["processing_profile"] == "deep_task"
    assert result["estimated_wait_range_seconds"] == [35, 60]


def test_resolve_active_knowledge_space_id_prefers_single_manifest_scope():
    manifest_repo = _FakeManifestRepo(
        rows=[
            {
                "doc_id": "doc-1",
                "knowledge_space_id": "ks-1",
                "status": "indexed",
                "chunks_indexed": 10,
            }
        ]
    )
    service = _build_service(manifest_repo=manifest_repo)

    result = service.resolve_active_knowledge_space_id(
        conversation_id="conv-1",
        requested_knowledge_space_id=None,
    )

    assert result == "ks-1"
