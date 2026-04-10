import pytest

from app.services.knowledge_service import KnowledgeService


class FakeRepo:
    def __init__(self):
        self.calls = []

    async def find_code_citations(self, tokens, limit=8):
        self.calls.append({"tokens": tokens, "limit": limit})
        return [
            {
                "type": "Function",
                "name": "run",
                "file_path": "/repo/app/main.py",
                "line": 10,
                "full_name": "/repo/app/main.py::run",
                "relevance": 6,
            }
        ]


class FakeRepoNoCitations:
    def __init__(self):
        self.calls = []

    async def find_code_citations(self, tokens, limit=8):
        self.calls.append({"tokens": tokens, "limit": limit})
        return []


class FakeKnowledgeService(KnowledgeService):
    async def semantic_query(self, question: str, limit: int = 10) -> str:
        return f"answer:{question}:{limit}"


@pytest.mark.asyncio
async def test_ask_code_with_citations_returns_answer_and_citations():
    repo = FakeRepo()
    svc = FakeKnowledgeService(repo)

    result = await svc.ask_code_with_citations(
        question="Como Engine.run chama helper em app/main.py", limit=7, citation_limit=4
    )

    assert result["answer"] == "answer:Como Engine.run chama helper em app/main.py?:7"
    assert len(result["citations"]) == 1
    assert repo.calls[0]["limit"] == 4
    assert "engine.run" in repo.calls[0]["tokens"]
    assert "helper" in repo.calls[0]["tokens"]


@pytest.mark.asyncio
async def test_ask_code_with_citations_returns_guard_message_when_no_citations():
    repo = FakeRepoNoCitations()
    svc = FakeKnowledgeService(repo)

    result = await svc.ask_code_with_citations(
        question="Como Engine.run chama helper em app/main.py", limit=7, citation_limit=4
    )

    assert result["citations"] == []
    assert "Nao encontrei citacoes rastreaveis" in result["answer"]


def test_extract_code_tokens_removes_noise_and_dedupes():
    tokens = KnowledgeService._extract_code_tokens("O que run run faz em app/main.py e helper")

    assert "run" in tokens
    assert "helper" in tokens
    assert "app/main.py" in tokens
    assert tokens.count("run") == 1
    assert "o" not in tokens
    assert "em" not in tokens
