from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.planes.inference.facade import InferenceFacade
from app.planes.knowledge.contracts import RetrievalBackendName
from app.planes.knowledge.facade import KnowledgeFacade


class _DummyMemoryService:
    async def recall_filtered(self, **kwargs):
        return [{"id": "m1", "metadata": kwargs}]

    async def index_interaction(self, **kwargs):
        self.index_kwargs = kwargs


class _DummyKnowledgeService:
    pass


class _DummyDocumentService:
    async def ingest_file(self, **kwargs):
        return {"status": "indexed", "kwargs": kwargs}


class _DummyRagService:
    async def retrieve_context(self, **kwargs):
        return [{"content": "ctx", "kwargs": kwargs}]


class _DummyQdrantAdapter:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def search_documents(self, **kwargs):
        self.calls.append(("search_documents", kwargs))
        return [{"id": "doc-1", "score": 0.91}]

    async def delete_document(self, **kwargs):
        self.calls.append(("delete_document", kwargs))

    async def get_document_points(self, **kwargs):
        self.calls.append(("get_document_points", kwargs))
        return [], 0

    async def search_user_chat(self, **kwargs):
        self.calls.append(("search_user_chat", kwargs))
        return []

    async def search_user_memory(self, **kwargs):
        self.calls.append(("search_user_memory", kwargs))
        return []

    async def index_memory_event(self, **kwargs):
        self.calls.append(("index_memory_event", kwargs))

    async def load_user_timeline_points(self, **kwargs):
        self.calls.append(("load_user_timeline_points", kwargs))
        return []


class _DummyExperimentalAdapter(_DummyQdrantAdapter):
    async def search_documents(self, **kwargs):
        self.calls.append(("search_documents", kwargs))
        return [{"id": "exp-1", "score": 0.73, "doc_id": "doc-exp"}]

    async def search_user_chat(self, **kwargs):
        self.calls.append(("search_user_chat", kwargs))
        return [SimpleNamespace(id="chat-exp", score=0.7, payload={"metadata": {"session_id": "s1"}})]

    async def search_user_memory(self, **kwargs):
        self.calls.append(("search_user_memory", kwargs))
        return [SimpleNamespace(id="mem-exp", score=0.68, payload={"metadata": {"type": "calendar_event"}})]


class _DummyExperimentalIndexManager:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def last_build_summary(self):
        return {"domain": "docs", "built_at": "2026-04-15T00:00:00+00:00"}

    async def build_index(self, **kwargs):
        self.calls.append(("build_index", kwargs))
        return SimpleNamespace(
            dry_run=bool(kwargs.get("dry_run", False)),
            output_dir="/tmp/experimental",
            manifest=SimpleNamespace(domain=kwargs.get("domain"), version="v1"),
        )

    async def append_point(self, **kwargs):
        self.calls.append(("append_point", kwargs))


class _DummyLLMService:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def invoke_llm(self, **kwargs):
        self.calls.append(("invoke_llm", kwargs))
        return {
            "response": "ok",
            "provider": "ollama",
            "model": "dummy",
            "role": kwargs["role"].value,
        }

    async def select_provider_and_model(self, **kwargs):
        self.calls.append(("select_provider_and_model", kwargs))
        return {"provider": "ollama", "model": "dummy"}


class _DummyDeploymentRepo:
    def stage(self, model_id: str, rollout_percent: int):
        return {"action": "stage", "model_id": model_id, "rollout_percent": rollout_percent}

    def publish(self, model_id: str):
        return {"action": "publish", "model_id": model_id}

    def rollback(self, model_id: str):
        return {"action": "rollback", "model_id": model_id}


class _DummyBiasCheckService:
    def run_precheck(self, model_id: str):
        return {"action": "precheck", "model_id": model_id, "precheck_passed": True}


@pytest.mark.asyncio
async def test_knowledge_facade_uses_baseline_backend_by_default(monkeypatch):
    monkeypatch.setattr(
        "app.planes.knowledge.facade.settings",
        SimpleNamespace(
            KNOWLEDGE_RETRIEVAL_BACKEND="baseline_qdrant",
            KNOWLEDGE_RETRIEVAL_SHADOW_MODE=False,
            KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX=None,
            KNOWLEDGE_EXPERIMENTAL_INDEX_ENABLED=False,
            KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION="v1",
            KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL=False,
            KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ=False,
            KNOWLEDGE_RETRIEVAL_PROMOTION_ALLOWED=False,
        ),
    )
    adapter = _DummyQdrantAdapter()
    experimental_manager = _DummyExperimentalIndexManager()
    facade = KnowledgeFacade(
        memory_service=_DummyMemoryService(),
        knowledge_service=_DummyKnowledgeService(),
        document_service=_DummyDocumentService(),
        rag_service=_DummyRagService(),
        qdrant_adapter=adapter,
        experimental_index_manager=experimental_manager,
    )

    result = await facade.search_documents(query="janus", user_id="u1", limit=3)

    assert result == [{"id": "doc-1", "score": 0.91}]
    assert adapter.calls[0][0] == "search_documents"
    assert facade.health_snapshot()["active_backend"] == RetrievalBackendName.BASELINE_QDRANT.value
    assert facade.health_snapshot()["last_build"]["domain"] == "docs"


@pytest.mark.asyncio
async def test_knowledge_facade_routes_to_experimental_backend_when_enabled(monkeypatch):
    monkeypatch.setattr(
        "app.planes.knowledge.facade.settings",
        SimpleNamespace(
            KNOWLEDGE_RETRIEVAL_BACKEND="experimental_quantized_retrieval",
            KNOWLEDGE_RETRIEVAL_SHADOW_MODE=False,
            KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX="-turboquant",
            KNOWLEDGE_EXPERIMENTAL_INDEX_ENABLED=True,
            KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION="v1",
            KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL=False,
            KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ=False,
            KNOWLEDGE_RETRIEVAL_PROMOTION_ALLOWED=False,
        ),
    )
    adapter = _DummyQdrantAdapter()
    experimental_adapter = _DummyExperimentalAdapter()
    facade = KnowledgeFacade(
        memory_service=_DummyMemoryService(),
        knowledge_service=_DummyKnowledgeService(),
        document_service=_DummyDocumentService(),
        rag_service=_DummyRagService(),
        qdrant_adapter=adapter,
        experimental_adapter=experimental_adapter,
        experimental_index_manager=_DummyExperimentalIndexManager(),
    )

    result = await facade.search_documents(query="janus", user_id="u1", limit=3)

    assert result[0]["id"] == "exp-1"
    assert experimental_adapter.calls[0][0] == "search_documents"
    assert (
        facade.retrieval_backend_decision().active_backend
        == RetrievalBackendName.EXPERIMENTAL_QUANTIZED_RETRIEVAL
    )


@pytest.mark.asyncio
async def test_knowledge_facade_runs_shadow_compare_without_breaking_active_response(monkeypatch):
    monkeypatch.setattr(
        "app.planes.knowledge.facade.settings",
        SimpleNamespace(
            KNOWLEDGE_RETRIEVAL_BACKEND="baseline_qdrant",
            KNOWLEDGE_RETRIEVAL_SHADOW_MODE=True,
            KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX="-turboquant",
            KNOWLEDGE_EXPERIMENTAL_INDEX_ENABLED=True,
            KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION="v1",
            KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL=False,
            KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ=True,
            KNOWLEDGE_RETRIEVAL_PROMOTION_ALLOWED=False,
        ),
    )
    baseline = _DummyQdrantAdapter()
    experimental = _DummyExperimentalAdapter()
    facade = KnowledgeFacade(
        memory_service=_DummyMemoryService(),
        knowledge_service=_DummyKnowledgeService(),
        document_service=_DummyDocumentService(),
        rag_service=_DummyRagService(),
        qdrant_adapter=baseline,
        experimental_adapter=experimental,
        experimental_index_manager=_DummyExperimentalIndexManager(),
    )

    result = await facade.search_documents(query="janus", user_id="u1", limit=3)

    assert result == [{"id": "doc-1", "score": 0.91}]
    assert baseline.calls[0][0] == "search_documents"
    assert experimental.calls[0][0] == "search_documents"


@pytest.mark.asyncio
async def test_knowledge_facade_dual_write_uses_experimental_index_manager(monkeypatch):
    monkeypatch.setattr(
        "app.planes.knowledge.facade.settings",
        SimpleNamespace(
            KNOWLEDGE_RETRIEVAL_BACKEND="baseline_qdrant",
            KNOWLEDGE_RETRIEVAL_SHADOW_MODE=False,
            KNOWLEDGE_EXPERIMENTAL_COLLECTION_SUFFIX="-turboquant",
            KNOWLEDGE_EXPERIMENTAL_INDEX_ENABLED=True,
            KNOWLEDGE_EXPERIMENTAL_INDEX_VERSION="v1",
            KNOWLEDGE_EXPERIMENTAL_WRITE_DUAL=True,
            KNOWLEDGE_RETRIEVAL_COMPARE_ON_READ=False,
            KNOWLEDGE_RETRIEVAL_PROMOTION_ALLOWED=False,
        ),
    )
    manager = _DummyExperimentalIndexManager()
    facade = KnowledgeFacade(
        memory_service=_DummyMemoryService(),
        knowledge_service=_DummyKnowledgeService(),
        document_service=_DummyDocumentService(),
        rag_service=_DummyRagService(),
        qdrant_adapter=_DummyQdrantAdapter(),
        experimental_adapter=_DummyExperimentalAdapter(),
        experimental_index_manager=manager,
    )

    await facade.append_experimental_point(
        domain="chat",
        point_id="p1",
        vector=[0.1, 0.2],
        payload={"metadata": {"type": "chat_msg"}},
    )

    assert manager.calls[0][0] == "append_point"


@pytest.mark.asyncio
async def test_inference_facade_delegates_invoke_and_admin_actions():
    llm = _DummyLLMService()
    facade = InferenceFacade(
        llm_service=llm,
        deployment_repository=_DummyDeploymentRepo(),
        bias_check_service=_DummyBiasCheckService(),
    )

    result = await facade.invoke(
        prompt="hello",
        role="code_generator",
        priority="high_quality",
        timeout_seconds=5,
        user_id="u1",
        project_id="p1",
        objective_id="o1",
    )

    assert result["provider"] == "ollama"
    assert llm.calls[0][0] == "invoke_llm"
    assert facade.stage_model(model_id="m1", rollout_percent=10)["action"] == "stage"
    assert facade.publish_model(model_id="m1")["action"] == "publish"
    assert facade.rollback_model(model_id="m1")["action"] == "rollback"
    assert facade.precheck(model_id="m1")["precheck_passed"] is True
