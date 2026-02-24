import structlog
import json
import time
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm.router import get_llm
from app.core.llm.types import ModelPriority, ModelRole

logger = structlog.get_logger(__name__)


class KnowledgeExtractionService:
    """
    Serviço responsável por extrair conhecimento estruturado (entidades, relacionamentos)
    de texto bruto usando LLMs.
    """

    def __init__(self):
        self.llm: Optional[BaseChatModel] = None
        self._llm_unavailable_until: float | None = None
        self._llm_init_failures: int = 0
        self._last_llm_unavailable_log_ts: float | None = None
        self._llm_unavailable_cooldown_seconds = 300.0

    def is_llm_temporarily_unavailable(self) -> bool:
        until = self._llm_unavailable_until
        return bool(until and time.time() < until)

    def llm_unavailable_remaining_seconds(self) -> float:
        until = self._llm_unavailable_until
        if not until:
            return 0.0
        return max(0.0, until - time.time())

    async def _ensure_llm(self):
        if not self.llm:
            now = time.time()
            if self.is_llm_temporarily_unavailable():
                remaining = self.llm_unavailable_remaining_seconds()
                # Log at most once per cooldown window.
                if (
                    self._last_llm_unavailable_log_ts is None
                    or now - self._last_llm_unavailable_log_ts >= self._llm_unavailable_cooldown_seconds
                ):
                    self._last_llm_unavailable_log_ts = now
                    logger.warning(
                        "knowledge_extraction_llm_temporarily_unavailable",
                        cooldown_remaining_seconds=round(remaining, 1),
                    )
                return
            try:
                self.llm = await get_llm(
                    role=ModelRole.KNOWLEDGE_CURATOR, priority=ModelPriority.FAST_AND_CHEAP
                )
                self._llm_unavailable_until = None
                self._llm_init_failures = 0
            except Exception as e:
                self._llm_init_failures += 1
                self._llm_unavailable_until = now + self._llm_unavailable_cooldown_seconds
                self._last_llm_unavailable_log_ts = now
                logger.warning(
                    "knowledge_extraction_llm_init_failed",
                    failure_count=self._llm_init_failures,
                    cooldown_seconds=int(self._llm_unavailable_cooldown_seconds),
                    error=str(e),
                )
                return

    async def extract_from_text(self, text: str, metadata: dict[str, Any] = None) -> dict[str, Any]:
        """
        Extrai entidades e relacionamentos de um texto.

        Args:
            text: Conteúdo textual para analisar
            metadata: Metadados contextuais (opcional)

        Returns:
            Dict com chaves 'entities' e 'relationships'
        """
        await self._ensure_llm()
        if not self.llm:
            return {}

        try:
            system_prompt = await get_formatted_prompt(
                "knowledge_extraction_system",
                text=text[:4000],
                metadata=json.dumps(metadata or {}),
            )

            messages = [SystemMessage(content=system_prompt), HumanMessage(content="")]

            response = await self.llm.ainvoke(messages)
            content = response.content

            # Parse JSON robusto
            return self._parse_json_response(content)

        except Exception as e:
            logger.error("knowledge_extraction_failed", error=str(e), exc_info=True)
            return {}

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """
        Tenta parsear a resposta do LLM como JSON, lidando com blocos de código markdown.
        """
        try:
            clean_content = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_content)

            # Validação básica de schema
            if not isinstance(data, dict):
                return {}

            if "entities" not in data:
                data["entities"] = []
            if "relationships" not in data:
                data["relationships"] = []

            return data
        except json.JSONDecodeError:
            logger.warning(
                "knowledge_extraction_json_parse_failed",
                content_length=len(content),
            )
            return {}


# Singleton helper
_instance = None


def get_knowledge_extraction_service():
    global _instance
    if _instance is None:
        _instance = KnowledgeExtractionService()
    return _instance
