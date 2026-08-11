"""
Prompt Builder Service - Modular Architecture
Delegates to PromptComposer for efficient, intent-based prompt generation.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import structlog
from app.services.prompt_service import PromptService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CompiledPromptSnapshot:
    """Validated immutable projection returned by the prompt composer."""

    text: str
    modules_used: tuple[str, ...]
    token_count: int

    @classmethod
    def from_value(cls, value: object) -> "CompiledPromptSnapshot":
        text = getattr(value, "text", None)
        modules_used = getattr(value, "modules_used", None)
        token_count = getattr(value, "token_count", None)
        if not isinstance(text, str) or not text.strip():
            raise TypeError("Compiled prompt text must be a non-empty string")
        if not isinstance(modules_used, list) or not all(
            isinstance(module, str) and module for module in modules_used
        ):
            raise TypeError("Compiled prompt modules must be a list of non-empty strings")
        if isinstance(token_count, bool) or not isinstance(token_count, int) or token_count < 0:
            raise TypeError("Compiled prompt token count must be a non-negative integer")
        return cls(
            text=text,
            modules_used=tuple(modules_used),
            token_count=token_count,
        )


@runtime_checkable
class ToolDiscoveryCatalog(Protocol):
    def list_tools(
        self,
        *,
        category: object | None,
        permission_level: object | None,
        tags: list[str] | None,
    ) -> Sequence[object]: ...


@runtime_checkable
class ToolDocumentationCatalog(Protocol):
    def generate_documentation(self) -> str: ...


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

    @staticmethod
    def _classify_intent_value(message: str) -> str:
        from app.core.prompts.intent_classifier import IntentClassifier

        classified = IntentClassifier().classify(message)
        value = getattr(classified, "value", None)
        if not isinstance(value, str):
            raise TypeError("Intent classifier returned an invalid intent")
        return value

    async def build_prompt(
        self,
        persona: str,
        history: Sequence[Mapping[str, object]],
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
        normalized_history: list[Message] = []
        for entry in history:
            history_role = entry.get("role", "user")
            history_text = entry.get("text", "")
            if not isinstance(history_role, str) or not isinstance(history_text, str):
                raise TypeError("Prompt history entries require string role and text fields")
            normalized_history.append(Message(role=history_role, text=history_text))

        context = ConversationContext(
            history=normalized_history,
            current_message=new_user_message,
            summary=summary,
            relevant_memories=relevant_memories,
            persona=persona,
        )

        # Compose prompt using modular system
        composer = get_prompt_composer(self.prompt_service)
        compiled = CompiledPromptSnapshot.from_value(await composer.compose(intent, context))

        logger.info("log_info", message=f"[PROMPT_BUILD] ✅ Composed {len(compiled.modules_used)} modules, "
            f"~{compiled.token_count} tokens (intent={intent.value})"
        )

        return compiled.text

    def is_capabilities_query(self, message: str) -> bool:
        """Check if message is asking about capabilities."""
        from app.core.prompts.types import IntentType

        return self._classify_intent_value(message) == str(IntentType.CAPABILITIES_QUERY.value)

    def is_tool_request(self, message: str) -> bool:
        """Check if message is requesting tool creation."""
        from app.core.prompts.types import IntentType

        return self._classify_intent_value(message) == str(IntentType.TOOL_CREATION.value)

    def is_script_request(self, message: str) -> bool:
        """Check if message is requesting script generation."""
        from app.core.prompts.types import IntentType

        return self._classify_intent_value(message) == str(IntentType.SCRIPT_GENERATION.value)

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

    def render_discovery_intro(self, tools: ToolDiscoveryCatalog | None) -> str:
        """Render the homologated catalog without hiding repository failures."""
        if not isinstance(tools, ToolDiscoveryCatalog):
            raise RuntimeError("Homologated tool catalog is unavailable")

        tool_list = tools.list_tools(category=None, permission_level=None, tags=None)
        if not isinstance(tool_list, list):
            raise RuntimeError("Homologated tool catalog returned an invalid payload")

        names: list[str] = []
        for metadata in tool_list:
            raw_name = getattr(metadata, "name", None)
            if isinstance(raw_name, str) and raw_name.strip():
                names.append(raw_name.strip())
        names = sorted(dict.fromkeys(names), key=str.casefold)

        if not tool_list:
            return "O catálogo homologado de ferramentas está vazio no momento."
        if not names:
            return "O catálogo homologado não possui ferramentas com metadata válida no momento."

        return f"Estou equipado com as seguintes ferramentas: {', '.join(names)}. Pergunte 'como usar [ferramenta]' para mais detalhes."

    def render_tools_documentation(self, tools: ToolDocumentationCatalog | None) -> str:
        """Delegate tool documentation to the homologated product catalog."""
        if not isinstance(tools, ToolDocumentationCatalog):
            raise RuntimeError("Homologated tool documentation is unavailable")
        documentation = tools.generate_documentation()
        if not isinstance(documentation, str) or not documentation.strip():
            raise RuntimeError("Homologated tool documentation is empty")
        return documentation

    def render_local_capabilities(self) -> str:
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
