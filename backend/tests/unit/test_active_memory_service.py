import pytest

from app.services.active_memory_service import ActiveMemoryService


@pytest.mark.asyncio
async def test_active_memory_prioritizes_secret_capture(monkeypatch):
    svc = ActiveMemoryService()

    async def _secret(**kwargs):
        return {"status": "created", "id": "sec-1"}

    async def _procedural(**kwargs):
        raise AssertionError("procedural should not run after secret capture")

    async def _semantic(**kwargs):
        raise AssertionError("semantic should not run after secret capture")

    monkeypatch.setattr(
        "app.services.active_memory_service.secret_memory_service.maybe_capture_from_message",
        _secret,
    )
    monkeypatch.setattr(
        "app.services.active_memory_service.procedural_memory_service.maybe_capture_from_message",
        _procedural,
    )
    monkeypatch.setattr(
        "app.services.active_memory_service.user_preference_memory_service.maybe_capture_from_message",
        _semantic,
    )

    result = await svc.maybe_capture_from_message(
        message="Minha senha do Wi-Fi é Abc12345",
        user_id="u-1",
        conversation_id="c-1",
    )

    assert result is not None
    assert result["memory_class"] == "secret"
    assert result["status"] == "created"
