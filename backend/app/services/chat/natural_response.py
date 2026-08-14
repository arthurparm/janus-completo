"""
Shared "responder" layer for chat replies that are built from real,
deterministically-computed facts but should never repeat a fixed template.

Used by quick commands (chat_command_handler.py) and by the static-intent
resolver (turn_core.py) so both phrase their replies the same way: prefer the
OmniRoute provider, ground the model strictly in the given facts, and fall
back to a static, fact-accurate string if no LLM service is wired or
generation fails end-to-end. Never used for security/policy messages, which
must stay exact and are never routed through this helper.
"""

from typing import Any

import structlog

from app.core.llm import ModelPriority, ModelRole

logger = structlog.get_logger(__name__)


async def respond_naturally(
    llm_service: Any,
    *,
    facts: str,
    instruction: str,
    conversation_id: str,
    user_id: str | None,
    fallback: str,
) -> str:
    """
    Phrase a response grounded in `facts`, preferring the OmniRoute provider.

    `facts` must already be computed from real state before calling this -
    this function only asks the model to phrase them naturally, never to
    invent new ones. Falls back to `fallback` (a static, fact-accurate
    string) when no LLM service is wired or generation fails, so callers
    always get a response instead of an exception.
    """
    if not llm_service:
        return fallback

    prompt = (
        f"{instruction}\n\n"
        "Fatos reais (use exatamente estes; nao invente nem altere numeros ou fatos "
        f"que nao estejam listados aqui):\n{facts}\n\n"
        "Responda em portugues do Brasil, tom natural e caloroso, sem repetir um "
        "formato de template fixo a cada vez."
    )
    try:
        result = await llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            timeout_seconds=12,
            policy_overrides={
                "provider": "omniroute",
                "role": "orchestrator",
                "priority": "fast_and_cheap",
            },
            user_id=user_id,
            objective_id=conversation_id,
        )
        response = str((result or {}).get("response") or "").strip()
        return response or fallback
    except Exception as e:
        logger.warning(
            "natural_response_generation_failed",
            error=str(e),
            conversation_id=conversation_id,
        )
        return fallback
