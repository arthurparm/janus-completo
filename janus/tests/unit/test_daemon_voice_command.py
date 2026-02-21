from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.llm import ModelPriority, ModelRole
from app.interfaces.daemon.voice_command import process_voice_command


@pytest.mark.asyncio
async def test_process_voice_command_uses_chat_service_and_persists_conversation():
    chat_service = SimpleNamespace(
        start_conversation_async=AsyncMock(return_value="conv-voice-1"),
        send_message=AsyncMock(return_value={"response": "Resposta do chat"}),
    )
    kernel = SimpleNamespace(chat_service=chat_service, llm_service=None)

    response, conversation_id = await process_voice_command(kernel, "Ola, Janus", None)

    assert response == "Resposta do chat"
    assert conversation_id == "conv-voice-1"
    call = chat_service.send_message.await_args.kwargs
    assert call["conversation_id"] == "conv-voice-1"
    assert call["role"] == ModelRole.ORCHESTRATOR
    assert call["priority"] == ModelPriority.FAST_AND_CHEAP


@pytest.mark.asyncio
async def test_process_voice_command_falls_back_to_llm_when_chat_fails():
    chat_service = SimpleNamespace(
        start_conversation_async=AsyncMock(side_effect=RuntimeError("chat unavailable")),
        send_message=AsyncMock(),
    )
    llm_service = SimpleNamespace(
        invoke_llm=AsyncMock(return_value={"response": "Resposta direta do LLM"})
    )
    kernel = SimpleNamespace(chat_service=chat_service, llm_service=llm_service)

    response, conversation_id = await process_voice_command(kernel, "Explique status", None)

    assert response == "Resposta direta do LLM"
    assert conversation_id is None
    llm_service.invoke_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_voice_command_uses_echo_when_no_services_are_available():
    kernel = SimpleNamespace(chat_service=None, llm_service=None)

    response, conversation_id = await process_voice_command(kernel, "Teste rapido", None)

    assert response == "Entendido: Teste rapido"
    assert conversation_id is None
