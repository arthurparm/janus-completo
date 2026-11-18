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
        Uses native async repository with proper session management.
        """
        try:
            # We need to inject a session into the repository since it's now async and session-less by default
            from app.db import get_db_session
            
            async for session in get_db_session():
                # Temporarily attach session to repo (or create a new repo instance with session)
                repo_with_session = PromptRepository(session)
                prompt = await repo_with_session.get_active_prompt(prompt_name=prompt_name)
                
                if prompt and prompt.prompt_text:
                    return prompt.prompt_text
                
                break # Ensure we only use one session

            if fallback_text:
                logger.warning("log_warning", message=f"Prompt '{prompt_name}' not found or inactive. Using fallback.")
                return fallback_text

            logger.error("log_error", message=f"Prompt '{prompt_name}' not found and no fallback provided.")
            return ""
        except Exception as e:
            logger.error("log_error", message=f"Error serving prompt '{prompt_name}': {e}")
            return fallback_text or ""


def get_prompt_service(request: Request = None) -> PromptService:
    # If using dependency injection via app state
    if request:
        return request.app.state.prompt_service
    # Standalone instantiation if needed (e.g. workers)
    return PromptService(PromptRepository())
