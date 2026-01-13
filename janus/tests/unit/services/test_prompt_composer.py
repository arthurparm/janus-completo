"""
Unit tests for PromptComposer service.
Tests module selection, composition logic, and token optimization.
"""

import pytest

from app.core.prompts.context import ConversationContext, Message
from app.core.prompts.types import IntentType
from app.services.prompt_composer_service import PromptComposer


class TestPromptComposer:
    """Test suite for PromptComposer."""

    @pytest.fixture
    def composer(self):
        """Create composer instance."""
        return PromptComposer()

    @pytest.fixture
    def simple_context(self):
        """Simple conversation context."""
        return ConversationContext(
            history=[
                Message(role="user", text="Hello"),
                Message(role="assistant", text="Hi there!"),
            ],
            current_message="What can you do?",
        )

    @pytest.mark.asyncio
    async def test_casual_chat_modules(self, composer, simple_context):
        """Test that casual chat loads minimal modules."""
        compiled = await composer.compose(IntentType.CASUAL_CHAT, simple_context)

        # Should load: SystemIdentity, Context (if history), but NOT reasoning/tools
        assert "system_identity" in compiled.modules_used
        assert "reasoning_protocol" not in compiled.modules_used
        assert "tool_documentation" not in compiled.modules_used
        assert compiled.token_count < 500  # Should be very compact

    @pytest.mark.asyncio
    async def test_tool_creation_modules(self, composer, simple_context):
        """Test that tool creation loads appropriate modules."""
        simple_context.current_message = "Crie uma ferramenta para buscar CEP"

        compiled = await composer.compose(IntentType.TOOL_CREATION, simple_context)

        # Should load: Identity, Reasoning, Tools, Task-specific
        assert "system_identity" in compiled.modules_used
        assert "reasoning_protocol" in compiled.modules_used
        assert "tool_documentation" in compiled.modules_used
        assert "task_specific" in compiled.modules_used

    @pytest.mark.asyncio
    async def test_token_estimation(self, composer, simple_context):
        """Test token count estimation."""
        compiled = await composer.compose(IntentType.QUESTION, simple_context)

        # Verify token count is reasonable
        assert compiled.token_count > 0
        assert compiled.token_count < 2000  # Should be less than old system

    @pytest.mark.asyncio
    async def test_long_history_compression(self, composer):
        """Test that long histories are compressed."""
        # Create context with long history
        long_history = [
            Message(role="user", text=f"Message {i}") for i in range(20)  # Many messages
        ]
        context = ConversationContext(
            history=long_history,
            current_message="Current question",
        )

        compiled = await composer.compose(IntentType.QUESTION, context)

        # Should use context compression
        assert "context_compression" in compiled.modules_used

        # Should still be reasonably sized
        assert compiled.token_count < 1500

    @pytest.mark.asyncio
    async def test_intent_tool_filter(self, composer, simple_context):
        """Test that only relevant tools are documented."""
        compiled = await composer.compose(IntentType.TOOL_CREATION, simple_context)

        # Check that output contains only relevant tools
        assert "evolve_tool" in compiled.text
        # Should NOT contain irrelevant tools for this intent
        # (This is a basic check - could be more specific)

    @pytest.mark.asyncio
    async def test_no_duplicate_sections(self, composer, simple_context):
        """Test that modules don't produce duplicate content."""
        compiled = await composer.compose(IntentType.ANALYSIS, simple_context)

        # Count occurrences of section headers
        header_count = compiled.text.count("═══════════════════")

        # Should have reasonable number of headers (one per section)
        assert header_count < 10  # Not excessive duplication


class TestModuleApplicability:
    """Test module selection logic."""

    @pytest.fixture
    def composer(self):
        return PromptComposer()

    def test_system_identity_always_applicable(self, composer):
        """SystemIdentity should apply to all intents."""
        from app.core.prompts.modules import SystemIdentityModule

        module = SystemIdentityModule()

        for intent in IntentType:
            assert module.is_applicable(intent)

    def test_reasoning_not_for_casual_chat(self, composer):
        """Reasoning protocol should not load for casual chat."""
        from app.core.prompts.modules import ReasoningProtocolModule

        module = ReasoningProtocolModule()

        assert not module.is_applicable(IntentType.CASUAL_CHAT)
        assert module.is_applicable(IntentType.ANALYSIS)

    def test_tools_not_for_casual_chat(self, composer):
        """Tools should not load for casual chat."""
        from app.core.prompts.modules import ToolDocumentationModule

        module = ToolDocumentationModule()

        assert not module.is_applicable(IntentType.CASUAL_CHAT)
        assert module.is_applicable(IntentType.TOOL_CREATION)


@pytest.mark.asyncio
async def test_composer_error_handling():
    """Test composer handles module errors gracefully."""
    composer = PromptComposer()

    # Create a module that will fail
    class BrokenModule:
        name = "broken"
        priority = 100

        def is_applicable(self, intent):
            return True

        async def render(self, intent, context):
            raise ValueError("Intentional error")

    # Add broken module
    composer.modules.append(BrokenModule())

    context = ConversationContext(history=[], current_message="test")

    # Should not crash, should continue with other modules
    compiled = await composer.compose(IntentType.CASUAL_CHAT, context)

    assert compiled.text  # Should still produce output
    assert "broken" not in compiled.modules_used  # Broken module not included
