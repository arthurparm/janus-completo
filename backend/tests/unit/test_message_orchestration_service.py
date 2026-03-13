import pytest
import asyncio
from unittest.mock import AsyncMock

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
        self.index_calls = 0
        self.summary_calls = 0

    async def retrieve_context(self, message, **kwargs):
        self.retrieve_calls += 1
        return [{"content": "ctx"}]

    async def maybe_index_message(self, text, **kwargs):
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
):
    return MessageOrchestrationService(
        repo=repo or _FakeRepo(),
        llm_service=llm_service or _FakeLLMService(),
        tool_service=None,
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
        message="Implemente uma rotina de deploy com rollback e validacao completa.",
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
        user_id="user-1",
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
        user_id="user-1",
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
        user_id="user-1",
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
        user_id="user-1",
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
        user_id="user-1",
    )

    assert "Nao encontrei no documento" in result["response"]
    assert "diabetes mellitus" in result["response"]
    assert "facial droop" not in result["response"]


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
        lambda self, *, knowledge_space_id, user_id: {
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
        user_id="user-1",
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
