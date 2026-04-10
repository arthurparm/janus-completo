import pytest

from app.services.procedural_memory_service import ProceduralMemoryService


class _FakeExperience:
    def __init__(self, exp_id: str = "proc-1"):
        self.id = exp_id


def test_extract_rule_identifies_recurring_instruction():
    svc = ProceduralMemoryService()

    result = svc.extract_rule("Sempre termine com próximos passos objetivos.")

    assert result is not None
    assert result["scope"] == "closing"
    assert result["procedure_kind"] == "response_structure"
    assert result["confidence"] >= 0.88


@pytest.mark.asyncio
async def test_maybe_capture_builds_procedural_metadata(monkeypatch):
    svc = ProceduralMemoryService()
    captured: dict[str, object] = {}

    async def _fake_exists(*, dedupe_key: str) -> bool:
        captured["checked_dedupe_key"] = dedupe_key
        return False

    async def _fake_deactivate_scope_conflicts(*, scope: str, keep_dedupe_key: str) -> None:
        captured["scope"] = scope
        captured["keep_dedupe_key"] = keep_dedupe_key

    async def _fake_add_memory(content: str, type: str, metadata: dict):
        captured["content"] = content
        captured["type"] = type
        captured["metadata"] = metadata
        return _FakeExperience()

    monkeypatch.setattr(svc, "_rule_exists", _fake_exists)
    monkeypatch.setattr(svc, "_deactivate_scope_conflicts", _fake_deactivate_scope_conflicts)
    monkeypatch.setattr(
        "app.services.procedural_memory_service.generative_memory_service.add_memory",
        _fake_add_memory,
    )

    result = await svc.maybe_capture_from_message(
        message="Sempre termine com próximos passos objetivos.",
        conversation_id="c-1",
        user_id="1",
    )

    assert result is not None
    assert result["status"] == "created"
    assert captured["type"] == "procedural"
    metadata = captured["metadata"]
    assert metadata["type"] == "procedural_rule"
    assert metadata["memory_class"] == "procedural"
    assert metadata["scope"] == "closing"
    assert metadata["recall_policy"] == "always"
    assert metadata["retention_policy"] == "persistent"


def test_format_procedural_context_emphasizes_priority():
    svc = ProceduralMemoryService()

    text = svc.format_procedural_context(
        [{"instruction_text": "Sempre termine com próximos passos objetivos."}]
    )

    assert text is not None
    assert "instruções persistentes do usuário" in text.lower()
    assert "Sempre termine com próximos passos objetivos." in text
