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
    captured_query: dict[str, str] = {}
    captured_params: dict[str, object] = {}

    class _CaptureGraph:
        async def query(self, query: str, params: dict[str, object], *args, **kwargs):
            captured_query["value"] = query
            captured_params.update(params)
            return [{"owner_links": 1, "symbol_links": 1}]

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

    query = captured_query["value"]
    assert "MERGE (m)-[:RELATES_TO]->(owner)" in query
    assert "OPTIONAL MATCH (fn:CodeFunction)" in query
    assert "OPTIONAL MATCH (cl:CodeClass)" in query
    assert "MERGE (m)-[:DEFINES]->(fn)" in query
    candidates = captured_params.get("path_candidates")
    assert isinstance(candidates, list)
    assert "backend/app/services/autonomy_admin_service.py" in candidates
    assert "/backend/app/services/autonomy_admin_service.py" in candidates
    assert "app/services/autonomy_admin_service.py" in candidates
    assert captured_params["source_experience_id"] == "exp-1"
    assert captured_params["symbols"] == ["AutonomyAdminService"]


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
    assert status["last_studied_commit"] == "abc123"
    assert status["running"]["id"] == 99
    assert status["running"]["files_total"] == 429
    assert status["running"]["files_processed"] == 7
    assert status["running"]["current_file_index"] == 8
    assert status["running"]["current_file_path"] == "backend/app/services/autonomy_admin_service.py"
