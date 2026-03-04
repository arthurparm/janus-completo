from pathlib import Path

import pytest

import app.services.autonomy_admin_service as autonomy_admin_module
from app.services.autonomy_admin_service import AutonomyAdminService


class _DummyLLM:
    async def invoke_llm(self, **kwargs):
        return {"response": "{\"sprint_type\": \"QA\"}", "provider": "local", "model": "local"}


class _DummyKnowledge:
    def __init__(self, citations):
        self._citations = citations

    async def ask_code_with_citations(self, question: str, limit: int = 10, citation_limit: int = 8):
        return {"answer": "resposta", "citations": self._citations}


class _DummyMeta:
    def get_latest_report(self):
        return None


class _DummyGraph:
    async def query(self, *args, **kwargs):
        return []


@pytest.fixture(autouse=True)
def _patch_meta(monkeypatch):
    monkeypatch.setattr(autonomy_admin_module, "get_meta_agent_service", lambda: _DummyMeta())


def _new_service(citations):
    return AutonomyAdminService(
        llm_service=_DummyLLM(),
        knowledge_service=_DummyKnowledge(citations=citations),
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
