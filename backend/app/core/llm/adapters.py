import structlog
from abc import ABC, abstractmethod
from inspect import isawaitable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

logger = structlog.get_logger(__name__)


class LLMAdapter(ABC):
    """Abstract adapter for LLM provider specifics."""

    def __init__(self, base_model: BaseChatModel):
        self.base_model = base_model

    @abstractmethod
    def apply_output_limit(self, max_output_tokens: int) -> None:
        """Applies max output token limit to the underlying model."""
        pass

    def invoke(self, prompt: str, **kwargs) -> Any:
        """Invokes the underlying model."""
        return self.base_model.invoke(prompt, **kwargs)

    async def ainvoke(self, prompt: str, **kwargs) -> Any:
        """Prefere o caminho assíncrono nativo do LangChain quando disponível."""
        async_invoke = getattr(self.base_model, "ainvoke", None)
        if callable(async_invoke):
            result = async_invoke(prompt, **kwargs)
            if isawaitable(result):
                return await result
            return result
        return self.invoke(prompt, **kwargs)


class OpenAIAdapter(LLMAdapter):
    def invoke(self, prompt: str, **kwargs) -> Any:
        # Handle 'strict' mode shortcut
        if kwargs.pop("strict", False):
            if "response_format" not in kwargs:
                kwargs["response_format"] = {"type": "json_object"}

        return super().invoke(prompt, **kwargs)

    async def ainvoke(self, prompt: str, **kwargs) -> Any:
        if kwargs.pop("strict", False):
            if "response_format" not in kwargs:
                kwargs["response_format"] = {"type": "json_object"}

        return await super().ainvoke(prompt, **kwargs)

    def apply_output_limit(self, max_output_tokens: int) -> None:
        try:
            mk = getattr(self.base_model, "model_kwargs", None)
            if isinstance(mk, dict):
                mk["max_tokens"] = max_output_tokens
            else:
                self.base_model.model_kwargs = {"max_tokens": max_output_tokens}
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to apply output limit for OpenAI: {e}")



class GeminiAdapter(LLMAdapter):
    def apply_output_limit(self, max_output_tokens: int) -> None:
        try:
            if hasattr(self.base_model, "max_output_tokens"):
                self.base_model.max_output_tokens = max_output_tokens
            else:
                mk = getattr(self.base_model, "model_kwargs", None)
                if isinstance(mk, dict):
                    mk["max_output_tokens"] = max_output_tokens
                else:
                    self.base_model.model_kwargs = {"max_output_tokens": max_output_tokens}
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to apply output limit for Gemini: {e}")


class OllamaAdapter(LLMAdapter):
    def apply_output_limit(self, max_output_tokens: int) -> None:
        # Ollama usually handles context/prediction limits via different params (num_predict)
        # or it might reuse model_kwargs depending on LangChain version.
        # For now, we implement a safe no-op or mapping if known.
        # In the original code, Ollama wasn't explicitly handled in _apply_output_limit block
        # (it fell through the if/elif), so we keep it as no-op or basic model_kwargs support.
        try:
            mk = getattr(self.base_model, "model_kwargs", None)
            if isinstance(mk, dict):
                mk["num_predict"] = max_output_tokens  # Common param for Ollama
            else:
                # Try configuring if possible, otherwise ignore
                pass
        except Exception:
            pass  # Silent fail pattern for optional config


class GenericAdapter(LLMAdapter):
    """Fallback adapter for unknown providers."""

    def apply_output_limit(self, max_output_tokens: int) -> None:
        pass


def get_adapter(base_model: BaseChatModel, provider: str) -> LLMAdapter:
    if provider == "openai":
        return OpenAIAdapter(base_model)
    elif provider == "google_gemini":
        return GeminiAdapter(base_model)
    elif provider == "ollama":
        return OllamaAdapter(base_model)
    else:
        return GenericAdapter(base_model)
