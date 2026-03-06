from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.autonomy_admin_service as autonomy_admin_module
from app.services.autonomy_admin_service import AutonomyAdminService


class _DummyLLM:
    async def invoke_llm(self, **kwargs):
        return {"response": "{\"sprint_type\": \"QA\"}", "provider": "local", "model": "local"}


class _DummyKnowledge:
    def __init__(self, citations, answer: str = "resposta"):
        self._citations = citations
        self._answer = answer

    async def ask_code_with_citations(self, question: str, limit: int = 10, citation_limit: int = 8):
        return {"answer": self._answer, "citations": self._citations}


class _DummyMeta:
    def get_latest_report(self):
        return None


class _DummyGraph:
    async def query(self, *args, **kwargs):
        return []


@pytest.fixture(autouse=True)
def _patch_meta(monkeypatch):
    monkeypatch.setattr(autonomy_admin_module, "get_meta_agent_service", lambda: _DummyMeta())

    class _DummyMemoryDb:
        async def arecall_filtered(self, *args, **kwargs):
            return []

    async def _fake_get_memory_db():
        return _DummyMemoryDb()

    monkeypatch.setattr(autonomy_admin_module, "get_memory_db", _fake_get_memory_db)


def _new_service(citations, answer: str = "resposta"):
    return AutonomyAdminService(
        llm_service=_DummyLLM(),
        knowledge_service=_DummyKnowledge(citations=citations, answer=answer),
    )


def test_resolve_files_for_study_includes_only_app_paths(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    inside_backend = tmp_path / "backend" / "app" / "services" / "x.py"
    inside_frontend = tmp_path / "frontend" / "src" / "app" / "components" / "x.ts"
    outside_backend = tmp_path / "backend" / "scripts" / "private.py"
    outside_frontend = tmp_path / "frontend" / "src" / "lib" / "x.ts"

    for path in [inside_backend, inside_frontend, outside_backend, outside_frontend]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    rows = service._resolve_files_for_study(
        mode="full",
        base_commit=None,
        target_commit=None,
    )
    paths = {row["file_path"] for row in rows}

    assert "backend/app/services/x.py" in paths
    assert "frontend/src/app/components/x.ts" in paths
    assert "backend/scripts/private.py" not in paths
    assert "frontend/src/lib/x.ts" not in paths


def test_resolve_files_for_study_incremental_without_diff_or_task_files_falls_back_to_full(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    inside_backend = tmp_path / "backend" / "app" / "services" / "x.py"
    inside_backend.parent.mkdir(parents=True, exist_ok=True)
    inside_backend.write_text("ok", encoding="utf-8")

    rows = service._resolve_files_for_study(
        mode="incremental",
        base_commit=None,
        target_commit=None,
        task_files=None,
    )
    assert len(rows) == 1
    assert rows[0]["file_path"] == "backend/app/services/x.py"
    assert rows[0]["change_type"] == "full"


def test_resolve_files_for_study_incremental_uses_task_context_when_present(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    inside_backend = tmp_path / "backend" / "app" / "services" / "x.py"
    inside_backend.parent.mkdir(parents=True, exist_ok=True)
    inside_backend.write_text("ok", encoding="utf-8")

    rows = service._resolve_files_for_study(
        mode="incremental",
        base_commit=None,
        target_commit=None,
        task_files=["backend/app/services/x.py"],
    )

    assert len(rows) == 1
    assert rows[0]["file_path"] == "backend/app/services/x.py"
    assert rows[0]["change_type"] == "task_context"


def test_resolve_files_for_study_rejects_remote_or_outside_task_context(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    inside_backend = tmp_path / "backend" / "app" / "services" / "x.py"
    inside_backend.parent.mkdir(parents=True, exist_ok=True)
    inside_backend.write_text("ok", encoding="utf-8")

    outside_repo = tmp_path.parent / "outside.py"
    outside_repo.write_text("bad", encoding="utf-8")

    rows = service._resolve_files_for_study(
        mode="incremental",
        base_commit=None,
        target_commit=None,
        task_files=[
            "https://example.com/backend/app/services/x.py",
            str(outside_repo),
            "backend/app/services/x.py",
        ],
    )

    assert len(rows) == 1
    assert rows[0]["file_path"] == "backend/app/services/x.py"


def test_infer_self_memory_relationship_types_is_local_and_code_aware(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    py_file = tmp_path / "backend" / "app" / "services" / "example_service.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(
        "\n".join(
            [
                "import os",
                "from typing import Any",
                "",
                "class Base: ...",
                "class Example(Base):",
                "    def run(self):",
                "        helper()",
                "",
                "def helper():",
                "    return 1",
            ]
        ),
        encoding="utf-8",
    )

    rels = service._infer_self_memory_relationship_types(
        "backend/app/services/example_service.py",
        "backend/app/services/example_service.py: 10 linhas analisadas.",
    )
    assert "RELATES_TO" in rels
    assert "IMPORTS" in rels
    assert "DEFINES" in rels
    assert "CALLS" in rels
    assert "INHERITS_FROM" in rels
    assert "USES" in rels

    style_file = tmp_path / "frontend" / "src" / "app" / "features" / "x.scss"
    style_file.parent.mkdir(parents=True, exist_ok=True)
    style_file.write_text(".panel { color: red; }", encoding="utf-8")
    rels_style = service._infer_self_memory_relationship_types(
        "frontend/src/app/features/x.scss",
        "Arquivo de interface/estilo.",
    )
    assert "RELATES_TO" in rels_style
    assert "HAS_PROPERTY" in rels_style
    assert "CONTAINS" in rels_style


def test_summarize_file_returns_structured_python_memory(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    py_file = tmp_path / "backend" / "app" / "services" / "example_service.py"
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(
        '\n'.join(
            [
                '"""Handle chat orchestration."""',
                "import httpx",
                "from app.db.graph import get_graph_db",
                "",
                "class ExampleService:",
                "    async def run(self):",
                "        return await helper()",
                "",
                "async def helper():",
                "    return 1",
            ]
        ),
        encoding="utf-8",
    )

    summary = service._summarize_file("backend/app/services/example_service.py")

    assert summary is not None
    assert summary["language"] == "python"
    assert "ExampleService" in summary["symbols"]
    assert "helper" in summary["symbols"]
    assert "httpx" in summary["imports"]
    assert summary["summary_version"] == service.SELF_MEMORY_SUMMARY_VERSION
    assert "compact_text" in summary


def test_summarize_file_returns_none_for_unhelpful_file(tmp_path: Path):
    service = _new_service(citations=[])
    service._repo_root = tmp_path

    data_file = tmp_path / "app" / "workspace" / "training_data.jsonl"
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text("{}", encoding="utf-8")

    assert service._summarize_file("app/workspace/training_data.jsonl") is None


@pytest.mark.asyncio
async def test_admin_code_qa_filters_citations_outside_app(monkeypatch):
    citations = [
        {"file_path": "backend/app/services/autonomy_admin_service.py", "line": 10},
        {"file_path": "backend/scripts/private.py", "line": 20},
    ]
    service = _new_service(citations=citations)

    async def _fake_get_graph_db():
        return _DummyGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    result = await service.ask_code_as_admin(question="onde fica autonomia_admin_service")
    out = result.get("citations") or []

    assert len(out) == 1
    assert out[0]["file_path"] == "backend/app/services/autonomy_admin_service.py"


@pytest.mark.asyncio
async def test_admin_code_qa_returns_safe_mode_when_only_outside_app_citations(monkeypatch):
    citations = [
        {"file_path": "backend/scripts/private.py", "line": 20},
        {"file_path": "documentation/secret.md", "line": 1},
    ]
    service = _new_service(citations=citations)

    async def _fake_get_graph_db():
        return _DummyGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    result = await service.ask_code_as_admin(question="me fale do sistema")
    assert result["citations"] == []
    assert "Nao encontrei evidencia suficiente" in result["answer"]


@pytest.mark.asyncio
async def test_admin_code_qa_does_not_fail_when_self_memory_query_errors(monkeypatch):
    citations = [
        {"file_path": "backend/app/services/autonomy_admin_service.py", "line": 10},
    ]
    service = _new_service(citations=citations)

    class _FailGraph:
        async def query(self, *args, **kwargs):
            raise RuntimeError("neo4j unavailable")

    async def _fake_get_graph_db():
        return _FailGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    result = await service.ask_code_as_admin(question="onde fica autonomia_admin_service")
    assert result["answer"] == "resposta"
    assert len(result["citations"]) == 1
    assert result["self_memory"] == []


@pytest.mark.asyncio
async def test_admin_code_qa_replaces_legacy_answer_with_evidence_summary(monkeypatch):
    citations = [
        {"file_path": "backend/app/services/autonomy_admin_service.py", "line": 690},
        {"file_path": "backend/app/services/autonomy_admin_service.py", "line": 740},
    ]
    service = _new_service(citations=citations, answer="Graph RAG not initialized.")

    async def _fake_get_graph_db():
        return _DummyGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    result = await service.ask_code_as_admin(question="me fale dos seus arquivos")
    assert result["citations"]
    assert "Graph RAG not initialized." not in result["answer"]
    assert "backend/app/services/autonomy_admin_service.py" in result["answer"]


@pytest.mark.asyncio
async def test_persist_self_memory_inserts_with_between_foreach_and_optional(monkeypatch):
    service = _new_service(citations=[])
    captured_queries: dict[str, str] = {}
    captured_params: dict[str, object] = {}
    owner_params: dict[str, object] = {}

    class _CaptureGraph:
        async def query(self, query: str, params: dict[str, object], *args, **kwargs):
            operation = str(kwargs.get("operation") or "")
            captured_queries[operation] = query
            if operation == "self_study_selfmemory_node_upsert":
                captured_params.update(params)
                return [{"owner_links": 0, "symbol_links": 0}]
            if operation == "self_study_selfmemory_owner_link":
                owner_params.update(params)
                return [{"owner_links": 1}]
            if operation == "self_study_selfmemory_owner_fallback":
                return [{"owner_links": 1}]
            if operation in {"self_study_selfmemory_function_link", "self_study_selfmemory_class_link"}:
                return [{"symbol_links": 1}]
            if operation == "self_study_selfmemory_provenance_link":
                return [{"provenance_links": 1}]
            if operation == "self_study_selfmemory_verify":
                return [{"owner_links": 1, "symbol_links": 1}]
            return []

    async def _fake_get_graph_db():
        return _CaptureGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    await service._persist_self_memory(
        rel_path="backend/app/services/autonomy_admin_service.py",
        summary_payload={
            "summary": "ok",
            "summary_version": service.SELF_MEMORY_SUMMARY_VERSION,
            "language": "python",
            "symbols": ["AutonomyAdminService"],
            "imports": ["json"],
            "touchpoints": ["neo4j"],
            "domain_tags": ["service"],
            "confidence": 0.9,
        },
        sha_after="abc123",
        source_experience_id="exp-1",
    )

    assert "MERGE (m:SelfMemory {memory_key: $memory_key})" in captured_queries["self_study_selfmemory_node_upsert"]
    assert "MERGE (m)-[:RELATES_TO]->(owner)" in captured_queries["self_study_selfmemory_owner_link"]
    assert "MATCH (fn:CodeFunction)" in captured_queries["self_study_selfmemory_function_link"]
    assert "MATCH (cl:CodeClass)" in captured_queries["self_study_selfmemory_class_link"]
    assert "MERGE (m)-[:EXTRACTED_FROM]->(exp)" in captured_queries["self_study_selfmemory_provenance_link"]
    candidates = owner_params.get("path_candidates")
    assert isinstance(candidates, list)
    assert "backend/app/services/autonomy_admin_service.py" in candidates
    assert "/backend/app/services/autonomy_admin_service.py" in candidates
    assert "app/services/autonomy_admin_service.py" in candidates
    assert "/app/app/services/autonomy_admin_service.py" in candidates
    owner_query = captured_queries["self_study_selfmemory_owner_link"]
    assert "owner.path IN $path_candidates" in owner_query
    assert captured_params["source_experience_id"] == "exp-1"
    assert captured_params["symbols"] == ["AutonomyAdminService"]
    assert captured_params["memory_key"] == service._build_self_memory_key(
        rel_path="backend/app/services/autonomy_admin_service.py",
        summary_version=service.SELF_MEMORY_SUMMARY_VERSION,
        sha_after="abc123",
    )
    assert captured_params["is_legacy"] is False


@pytest.mark.asyncio
async def test_persist_self_memory_retries_after_code_graph_reindex(monkeypatch):
    service = _new_service(citations=[])
    query_calls: list[str] = []

    class _RetryGraph:
        async def query(self, query: str, params: dict[str, object] | None = None, *args, **kwargs):
            query_calls.append(str(kwargs.get("operation") or ""))
            operation = str(kwargs.get("operation") or "")
            if operation == "self_study_selfmemory_node_upsert":
                return [{"owner_links": 0, "symbol_links": 0}]
            if operation == "self_study_selfmemory_owner_link":
                if query_calls.count("self_study_selfmemory_owner_link") == 1:
                    return [{"owner_links": 0}]
                return [{"owner_links": 1}]
            if operation == "self_study_selfmemory_owner_fallback":
                return [{"owner_links": 0}]
            if operation in {"self_study_selfmemory_function_link", "self_study_selfmemory_class_link"}:
                return [{"symbol_links": 0}]
            if operation == "self_study_selfmemory_provenance_link":
                return [{"provenance_links": 1}]
            if operation == "self_study_selfmemory_verify":
                if query_calls.count("self_study_selfmemory_verify") == 1:
                    return [{"owner_links": 0, "symbol_links": 0}]
                return [{"owner_links": 1, "symbol_links": 0}]
            if operation == "self_study_code_graph_file_count":
                return [{"file_count": 341}]
            return []

    async def _fake_get_graph_db():
        return _RetryGraph()

    reindex_calls = {"count": 0}

    async def _fake_index_codebase():
        reindex_calls["count"] += 1
        return {"message": "ok"}

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)
    service._knowledge_service.index_codebase = _fake_index_codebase  # type: ignore[method-assign]

    await service._persist_self_memory(
        rel_path="app/app/core/memory/graph_embeddings.py",
        summary_payload={
            "summary": "ok",
            "summary_version": service.SELF_MEMORY_SUMMARY_VERSION,
            "language": "python",
            "symbols": ["GraphEmbeddingsManager"],
            "imports": ["json"],
            "touchpoints": ["neo4j"],
            "domain_tags": ["memory"],
            "confidence": 0.9,
        },
        sha_after="abc123",
        source_experience_id="exp-1",
    )

    assert query_calls.count("self_study_selfmemory_node_upsert") == 2
    assert query_calls.count("self_study_selfmemory_owner_link") == 2
    assert query_calls.count("self_study_selfmemory_verify") == 2
    assert reindex_calls["count"] == 1


@pytest.mark.asyncio
async def test_persist_self_memory_uses_verify_query_to_avoid_false_negative(monkeypatch):
    service = _new_service(citations=[])
    query_calls: list[str] = []

    class _VerifyGraph:
        async def query(self, query: str, params: dict[str, object] | None = None, *args, **kwargs):
            operation = str(kwargs.get("operation") or "")
            query_calls.append(operation)
            if operation == "self_study_selfmemory_node_upsert":
                return [{"owner_links": 0, "symbol_links": 0}]
            if operation == "self_study_selfmemory_owner_link":
                return [{"owner_links": 1}]
            if operation == "self_study_selfmemory_owner_fallback":
                return [{"owner_links": 0}]
            if operation in {"self_study_selfmemory_function_link", "self_study_selfmemory_class_link"}:
                return [{"symbol_links": 0}]
            if operation == "self_study_selfmemory_provenance_link":
                return [{"provenance_links": 1}]
            if operation == "self_study_selfmemory_verify":
                return [{"owner_links": 1, "symbol_links": 1}]
            if operation == "self_study_code_graph_file_count":
                return [{"file_count": 341}]
            return []

    async def _fake_get_graph_db():
        return _VerifyGraph()

    reindex_calls = {"count": 0}

    async def _fake_index_codebase():
        reindex_calls["count"] += 1
        return {"message": "ok"}

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)
    service._knowledge_service.index_codebase = _fake_index_codebase  # type: ignore[method-assign]

    await service._persist_self_memory(
        rel_path="app/app/core/memory/graph_embeddings.py",
        summary_payload={
            "summary": "ok",
            "summary_version": service.SELF_MEMORY_SUMMARY_VERSION,
            "language": "python",
            "symbols": ["GraphEmbeddingsManager"],
            "imports": ["json"],
            "touchpoints": ["neo4j"],
            "domain_tags": ["memory"],
            "confidence": 0.9,
        },
        sha_after="abc123",
        source_experience_id="exp-1",
    )

    assert query_calls.count("self_study_selfmemory_node_upsert") == 1
    assert query_calls.count("self_study_selfmemory_owner_link") == 1
    assert query_calls.count("self_study_selfmemory_verify") == 1
    assert reindex_calls["count"] == 0


@pytest.mark.asyncio
async def test_persist_self_memory_creates_fallback_owner_when_code_owner_is_missing(monkeypatch):
    service = _new_service(citations=[])
    captured_queries: dict[str, str] = {}

    class _FallbackGraph:
        async def query(self, query: str, params: dict[str, object] | None = None, *args, **kwargs):
            operation = str(kwargs.get("operation") or "")
            captured_queries[operation] = query
            if operation == "self_study_selfmemory_node_upsert":
                return [{"owner_links": 0, "symbol_links": 0}]
            if operation == "self_study_selfmemory_owner_link":
                return [{"owner_links": 0}]
            if operation == "self_study_selfmemory_owner_fallback":
                return [{"owner_links": 1}]
            if operation in {"self_study_selfmemory_function_link", "self_study_selfmemory_class_link"}:
                return [{"symbol_links": 0}]
            if operation == "self_study_selfmemory_provenance_link":
                return [{"provenance_links": 0}]
            if operation == "self_study_selfmemory_verify":
                return [{"owner_links": 1, "symbol_links": 0}]
            return []

    async def _fake_get_graph_db():
        return _FallbackGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    await service._persist_self_memory(
        rel_path="frontend/src/app/features/auth/login.ts",
        summary_payload={
            "summary": "ok",
            "summary_version": service.SELF_MEMORY_SUMMARY_VERSION,
            "language": "typescript",
            "symbols": ["LoginComponent"],
            "imports": ["@angular/core"],
            "touchpoints": ["ui"],
            "domain_tags": ["frontend"],
            "confidence": 0.9,
        },
        sha_after="def456",
        source_experience_id=None,
    )

    assert "MERGE (owner:File {path: $primary_owner_path})" in captured_queries[
        "self_study_selfmemory_owner_fallback"
    ]


@pytest.mark.asyncio
async def test_ensure_code_graph_ready_reindexes_when_graph_is_empty():
    service = _new_service(citations=[])
    counts = iter([0, 12])

    async def _fake_get_code_graph_file_count():
        return next(counts)

    reindex_calls = {"count": 0}

    async def _fake_index_codebase():
        reindex_calls["count"] += 1
        return {"message": "ok"}

    service._get_code_graph_file_count = _fake_get_code_graph_file_count  # type: ignore[method-assign]
    service._knowledge_service.index_codebase = _fake_index_codebase  # type: ignore[method-assign]

    count = await service._ensure_code_graph_ready(force=True)

    assert count == 12
    assert reindex_calls["count"] == 1
    assert service._code_graph_file_count_cache == 12


@pytest.mark.asyncio
async def test_ensure_code_graph_ready_force_reindexes_when_graph_exists():
    service = _new_service(citations=[])
    counts = iter([97, 341])

    async def _fake_get_code_graph_file_count():
        return next(counts)

    reindex_calls = {"count": 0}

    async def _fake_index_codebase():
        reindex_calls["count"] += 1
        return {"message": "ok"}

    service._get_code_graph_file_count = _fake_get_code_graph_file_count  # type: ignore[method-assign]
    service._knowledge_service.index_codebase = _fake_index_codebase  # type: ignore[method-assign]

    count = await service._ensure_code_graph_ready(force=True)

    assert count == 341
    assert reindex_calls["count"] == 1
    assert service._code_graph_file_count_cache == 341


def test_get_self_study_status_includes_running_progress():
    service = _new_service(citations=[])
    now = datetime(2026, 3, 4, 19, 10, tzinfo=timezone.utc)

    class _Repo:
        def get_self_study_state(self):
            return SimpleNamespace(last_studied_commit="abc123", last_success_at=now)

        def get_latest_running_self_study(self):
            return SimpleNamespace(
                id=99,
                status="running",
                mode="incremental",
                created_at=now,
            )

        def get_self_study_run_progress(self, run_id: int):
            assert run_id == 99
            return {
                "files_total": 429,
                "files_processed": 7,
                "current_file_path": "backend/app/services/autonomy_admin_service.py",
                "current_file_index": 8,
            }

        def list_self_study_runs(self, limit: int = 5):
            assert limit == 5
            return []

    service._repo = _Repo()  # type: ignore[assignment]

    status = service.get_self_study_status()
    assert status["local_only"] is True
    assert status["run_budget_seconds"] == service._max_run_seconds
    assert status["run_deadline_local"] is None
    assert status["last_studied_commit"] == "abc123"
    assert status["running"]["id"] == 99
    assert status["running"]["files_total"] == 429
    assert status["running"]["files_processed"] == 7
    assert status["running"]["current_file_index"] == 8
    assert status["running"]["current_file_path"] == "backend/app/services/autonomy_admin_service.py"


def test_get_self_study_run_budget_uses_local_deadline(monkeypatch):
    service = _new_service(citations=[])
    service._max_run_seconds = 600
    service._self_study_deadline_local = "2026-03-07T09:00:00-03:00"

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            frozen = cls(2026, 3, 6, 18, 0, tzinfo=timezone.utc)
            if tz is None:
                return frozen
            return frozen.astimezone(tz)

    monkeypatch.setattr(autonomy_admin_module, "datetime", _FrozenDateTime)

    assert service._get_self_study_run_budget_seconds() == 64800


@pytest.mark.asyncio
async def test_recall_self_study_memories_prefers_linked_code_summary(monkeypatch):
    service = _new_service(citations=[])
    filters_seen: list[dict[str, object]] = []

    class _MemoryDb:
        async def arecall_filtered(self, *, query, filters, limit, min_score):
            del query, limit, min_score
            filters_seen.append(filters)
            if filters.get("neo4j_sync_status") == "linked":
                return []
            return [
                SimpleNamespace(
                    content="Resumo forte",
                    metadata={
                        "file_path": "backend/app/services/example.py",
                        "captured_at": 123,
                    },
                    score=0.8,
                )
            ]

    async def _fake_get_memory_db():
        return _MemoryDb()

    monkeypatch.setattr(autonomy_admin_module, "get_memory_db", _fake_get_memory_db)

    rows = await service._recall_self_study_memories(question="example")

    assert len(rows) == 1
    assert rows[0]["file_path"] == "backend/app/services/example.py"
    assert filters_seen[0] == {
        "origin": "self_study",
        "strong_memory": True,
        "source_kind": "code_file",
        "content_kind": "code_summary",
        "neo4j_sync_status": "linked",
    }
    assert filters_seen[1] == {
        "origin": "self_study",
        "strong_memory": True,
        "source_kind": "code_file",
        "content_kind": "code_summary",
    }
