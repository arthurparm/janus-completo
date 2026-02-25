import pytest

from app.services.user_preference_memory_service import UserPreferenceMemoryService


class _FakeExperience:
    def __init__(self, exp_id: str = "exp-1"):
        self.id = exp_id


def test_extract_preference_do():
    svc = UserPreferenceMemoryService()
    result = svc.extract_preference("Daqui pra frente, responda em tópicos curtos.")
    assert result is not None
    assert result["preference_kind"] == "do"
    assert result["should_persist"] is True
    assert result["confidence"] >= 0.75


def test_extract_preference_dont():
    svc = UserPreferenceMemoryService()
    result = svc.extract_preference("Não use emojis nas respostas para mim.")
    assert result is not None
    assert result["preference_kind"] == "dont"
    assert result["scope"] == "style"


def test_extract_preference_ignores_regular_message():
    svc = UserPreferenceMemoryService()
    assert svc.extract_preference("Qual é o status do sistema?") is None


@pytest.mark.asyncio
async def test_maybe_capture_builds_structured_metadata(monkeypatch):
    svc = UserPreferenceMemoryService()
    captured: dict[str, object] = {}

    async def _fake_exists(*, user_id: str, dedupe_key: str) -> bool:
        captured["checked_user_id"] = user_id
        captured["checked_dedupe_key"] = dedupe_key
        return False

    async def _fake_add_memory(content: str, type: str, metadata: dict):
        captured["content"] = content
        captured["type"] = type
        captured["metadata"] = metadata
        return _FakeExperience()

    monkeypatch.setattr(svc, "_preference_exists", _fake_exists)
    monkeypatch.setattr(
        "app.services.user_preference_memory_service.generative_memory_service.add_memory",
        _fake_add_memory,
    )

    result = await svc.maybe_capture_from_message(
        message="Não use emojis nas respostas para mim. [PREF-DONT-TEST]",
        user_id="1",
        conversation_id="42",
    )

    assert result is not None
    assert result["status"] == "created"
    assert captured["type"] == "semantic"
    metadata = captured["metadata"]
    assert metadata["type"] == "user_preference"
    assert metadata["preference_kind"] == "dont"
    assert metadata["user_id"] == "1"
    assert metadata["conversation_id"] == "42"
    assert metadata["session_id"] == "42"
    assert metadata["origin"] == "chat.user_preference_extractor"
    assert metadata["active"] is True


def test_format_preference_context_groups_do_and_dont():
    svc = UserPreferenceMemoryService()
    text = svc.format_preference_context(
        [
            {"preference_kind": "do", "instruction_text": "Responder em tópicos curtos."},
            {"preference_kind": "dont", "instruction_text": "Não usar emojis."},
        ]
    )
    assert text is not None
    assert "FAZER:" in text
    assert "NÃO FAZER:" in text

