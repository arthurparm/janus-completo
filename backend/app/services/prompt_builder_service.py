"""
Prompt Builder Service - Modular Architecture
Delegates to PromptComposer for efficient, intent-based prompt generation.
"""

import logging
from typing import Any

from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)


class PromptBuilderService:
    """
    Service for building LLM prompts using modular composition.
    Uses intent classification and selective module loading for token efficiency.
    """

    def __init__(self, prompt_service: PromptService | None = None):
        """
        Initialize prompt builder.

        Args:
            prompt_service: Optional service for dynamic prompt loading
        """
        self.prompt_service = prompt_service

    async def build_prompt(
        self,
        persona: str,
        history: list[dict[str, Any]],
        new_user_message: str,
        summary: str | None,
        relevant_memories: str | None = None,
    ) -> str:
        """
        Build complete prompt for LLM using modular composition.

        Uses intent-based module selection for optimal token efficiency:
        - Classifies user intent (tool creation, question, etc.)
        - Loads only relevant prompt modules
        - Compresses context intelligently
        - Returns optimized prompt

        Args:
            persona: Conversation persona/style
            history: Previous messages in conversation
            new_user_message: Current user message
            summary: Optional conversation summary
            relevant_memories: Optional long-term memories

        Returns:
            Compiled prompt string ready for LLM
        """
        from app.core.prompts.context import ConversationContext, Message
        from app.core.prompts.intent_classifier import IntentClassifier
        from app.services.prompt_composer_service import get_prompt_composer

        logger.info(
            "[PROMPT_BUILD] Building prompt for message: '%s...'",
            new_user_message[:100] if new_user_message else "(empty)",
        )

        # Classify intent
        classifier = IntentClassifier()
        intent = classifier.classify(new_user_message)

        # Build context
        context = ConversationContext(
            history=[Message(role=h.get("role", "user"), text=h.get("text", "")) for h in history],
            current_message=new_user_message,
            summary=summary,
            relevant_memories=relevant_memories,
            persona=persona,
        )

        # Compose prompt using modular system
        composer = get_prompt_composer(self.prompt_service)
        compiled = await composer.compose(intent, context)

        logger.info(
            f"[PROMPT_BUILD] ✅ Composed {len(compiled.modules_used)} modules, "
            f"~{compiled.token_count} tokens (intent={intent.value})"
        )

        return compiled.text

    def is_capabilities_query(self, message: str) -> bool:
        """Check if message is asking about capabilities."""
        from app.core.prompts.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        # IntentClassifier methods are synchronous in recent versions
        return classifier.is_capabilities_query(message)

    def is_tool_request(self, message: str) -> bool:
        """Check if message is requesting tool creation."""
        from app.core.prompts.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        return classifier.is_tool_request(message)

    def is_script_request(self, message: str) -> bool:
        """Check if message is requesting script generation."""
        from app.core.prompts.intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        return classifier.is_script_request(message)

    def is_discovery_query(self, message: str) -> bool:
        """Check if message is an interactive discovery query."""
        keywords = [
            "quais ferramentas",
            "quais tools",
            "o que você pode fazer",
            "what tools",
            "listar ferramentas",
        ]
        return any(k in message.lower() for k in keywords)

    def is_docs_query(self, message: str) -> bool:
        """Check if message is asking for tool documentation."""
        keywords = [
            "como usar a ferramenta",
            "documentação da tool",
            "docs da tool",
            "exemplos de uso",
        ]
        return any(k in message.lower() for k in keywords)

    def render_discovery_intro(self, tools: Any) -> str:
        """Render introductory message listing available tools."""
        tool_list = []
        # Try ToolService.list_tools pattern
        if hasattr(tools, "list_tools"):
            try:
                # Assuming ToolService signature: list_tools(category, permission_level, tags)
                tool_list = tools.list_tools(category=None, permission_level=None, tags=None)
            except Exception:
                # Fallback for simple list_tools()
                try:
                    tool_list = tools.list_tools()
                except Exception:
                    pass
        # Fallback to get_tools pattern (legacy or mock)
        elif hasattr(tools, "get_tools"):
            tool_list = tools.get_tools()

        names = [t.name for t in tool_list] if isinstance(tool_list, list) else []

        if not names:
            return "Estou equipado com diversas ferramentas para análise de código e sistema. Pergunte 'quais ferramentas' novamente para tentar recarregar a lista."

        return f"Estou equipado com as seguintes ferramentas: {', '.join(names)}. Pergunte 'como usar [ferramenta]' para mais detalhes."

    def render_tools_documentation(self, tools: Any) -> str:
        """Render detailed documentation for all tools."""
        # Simple implementation for fallback
        return "Documentação detalhada das ferramentas: ..."

    def render_local_capabilities(self, tools: Any) -> str:
        """Render local capabilities overview."""
        return "Posso analisar código, executar comandos de terminal, e gerenciar arquivos."

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using character heuristic (char/4).
        Used for quick cost/size estimation without full tokenization.
        """
        if not text:
            return 0
        return len(text) // 4
