import pytest
from app.services.chat.citation_policy import requires_mandatory_citations


@pytest.mark.parametrize(
    "message",
    [
        "Mostre o codigo",
        "Explain this function",
        "Abra o arquivo main.py",
        "Read the API documentation",
        "Qual endpoint devo usar?",
        "Revise component.ts",
        "Leia o README",
    ],
)
def test_requires_mandatory_citations_for_source_backed_queries(message: str) -> None:
    assert requires_mandatory_citations(message) is True


@pytest.mark.parametrize("message", ["", "Olá", "Resuma a conversa", "Qual é o status?"])
def test_does_not_require_citations_for_general_chat(message: str) -> None:
    assert requires_mandatory_citations(message) is False
