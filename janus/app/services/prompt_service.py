from typing import Any
import asyncio
import structlog
from fastapi import Request

from app.repositories.prompt_repository import PromptRepository
from app.db import db

logger = structlog.get_logger(__name__)


class PromptService:
    """
    Service for managing retrieval of dynamic prompts.
    """

    def __init__(self, repo: PromptRepository):
        self._repo = repo

    async def get_prompt(self, prompt_name: str, fallback_text: str | None = None) -> str:
        """
        Retrieves the active prompt text by name.
        Uses asyncio.to_thread to avoid blocking the loop with sync DB calls.
        """
        try:
            prompt = await asyncio.to_thread(self._repo.get_active_prompt, prompt_name=prompt_name)
            if prompt and prompt.prompt_text:
                return prompt.prompt_text

            if fallback_text:
                logger.warning(f"Prompt '{prompt_name}' not found or inactive. Using fallback.")
                return fallback_text

            logger.error(f"Prompt '{prompt_name}' not found and no fallback provided.")
            return ""
        except Exception as e:
            logger.error(f"Error serving prompt '{prompt_name}': {e}")
            return fallback_text or ""


def get_prompt_service(request: Request = None) -> PromptService:
    # If using dependency injection via app state
    if request:
        return request.app.state.prompt_service
    # Standalone instantiation if needed (e.g. workers)
    return PromptService(PromptRepository())
