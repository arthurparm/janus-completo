import pytest

from app.services.chat_command_handler import ChatCommandHandler


@pytest.mark.asyncio
async def test_about_command_reinforces_janus_identity():
    handler = ChatCommandHandler()

    response = await handler._handle_about(
        args="",
        conversation_id="conv-1",
        user_id="user-1",
    )

    assert "Sobre o Janus" in response
    assert "Sou o Janus" in response
    assert "interface única de assistência" in response
    assert "motores de IA internamente" in response
    assert "GPT" not in response
    assert "Gemini" not in response
