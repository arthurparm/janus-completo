import pytest

from app.core.prompts.context import ConversationContext, Message
from app.core.prompts.modules import ReasoningProtocolModule
from app.core.prompts.types import IntentType
from app.services.prompt_composer_service import PromptComposer


def test_reasoning_protocol_skips_common_questions():
    module = ReasoningProtocolModule()

    assert not module.is_applicable(IntentType.QUESTION)
    assert module.is_applicable(IntentType.ANALYSIS)


@pytest.mark.asyncio
async def test_prompt_composer_omits_reasoning_protocol_for_questions():
    composer = PromptComposer()
    context = ConversationContext(
        history=[
            Message(role="user", text="Oi"),
            Message(role="assistant", text="Olá"),
        ],
        current_message="Consegue imaginar uma historia para Frieren",
    )

    compiled = await composer.compose(IntentType.QUESTION, context)

    assert "reasoning_protocol" not in compiled.modules_used
