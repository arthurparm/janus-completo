from pathlib import Path

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

    class _CaptureGraph:
        async def execute(self, query: str, *args, **kwargs):
            captured_query["value"] = query

    async def _fake_get_graph_db():
        return _CaptureGraph()

    monkeypatch.setattr(autonomy_admin_module, "get_graph_db", _fake_get_graph_db)

    await service._persist_self_memory(
        rel_path="backend/app/services/autonomy_admin_service.py",
        summary="ok",
        sha_after="abc123",
    )

    query = captured_query["value"]
    assert "FOREACH (_ IN CASE WHEN f IS NULL THEN [] ELSE [1] END |" in query
    assert ")\n            WITH m\n            OPTIONAL MATCH (cf:CodeFile {path: $file_path})" in query
