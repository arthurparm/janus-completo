import inspect
from typing import Any

import structlog

from app.core.llm import ModelPriority, ModelRole

logger = structlog.get_logger(__name__)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _get_or_create_voice_conversation(
    kernel: Any, conversation_id: str | None
) -> str | None:
    if conversation_id:
        return conversation_id

    chat_service = getattr(kernel, "chat_service", None)
    if not chat_service:
        return None

    try:
        if hasattr(chat_service, "start_conversation_async"):
            created = await _maybe_await(
                chat_service.start_conversation_async("assistant", "daemon_voice", "voice")
            )
        else:
            created = await _maybe_await(
                chat_service.start_conversation("assistant", "daemon_voice", "voice")
            )
        return str(created) if created else None
    except Exception as e:
        logger.warning("voice_chat_conversation_start_failed", error=str(e))
        return None


async def process_voice_command(
    kernel: Any, command: str, conversation_id: str | None
) -> tuple[str, str | None]:
    chat_service = getattr(kernel, "chat_service", None)
    if chat_service:
        try:
            voice_conversation_id = await _get_or_create_voice_conversation(kernel, conversation_id)
            if voice_conversation_id:
                result = await _maybe_await(
                    chat_service.send_message(
                        conversation_id=voice_conversation_id,
                        message=command,
                        role=ModelRole.ORCHESTRATOR,
                        priority=ModelPriority.FAST_AND_CHEAP,
                        timeout_seconds=30,
                        user_id="daemon_voice",
                        project_id="voice",
                    )
                )
                response_text = result.get("response") if isinstance(result, dict) else str(result)
                if response_text:
                    return str(response_text), voice_conversation_id
                conversation_id = voice_conversation_id
        except Exception as e:
            logger.warning("voice_chat_service_failed", error=str(e))

    llm_service = getattr(kernel, "llm_service", None)
    if llm_service:
        try:
            result = await _maybe_await(
                llm_service.invoke_llm(
                    prompt=command,
                    role=ModelRole.ORCHESTRATOR,
                    priority=ModelPriority.FAST_AND_CHEAP,
                    timeout_seconds=30,
                    user_id="daemon_voice",
                    project_id="voice",
                )
            )
            response_text = result.get("response") if isinstance(result, dict) else str(result)
            if response_text:
                return str(response_text), conversation_id
        except Exception as e:
            logger.warning("voice_llm_fallback_failed", error=str(e))

    return f"Entendido: {command}", conversation_id
