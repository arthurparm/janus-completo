import logging
import json
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.llm.llm_manager import ModelPriority, ModelRole, get_llm

logger = logging.getLogger(__name__)


class KnowledgeExtractionService:
    """
    Serviço responsável por extrair conhecimento estruturado (entidades, relacionamentos)
    de texto bruto usando LLMs.
    """

    def __init__(self):
        self.llm: Optional[BaseChatModel] = None

    async def _ensure_llm(self):
        if not self.llm:
            try:
                self.llm = await get_llm(
                    role=ModelRole.KNOWLEDGE_CURATOR, priority=ModelPriority.FAST_AND_CHEAP
                )
            except Exception as e:
                logger.error(f"Failed to initialize LLM for knowledge extraction: {e}")
                raise

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
            # Obter prompt do sistema modular
            system_prompt = get_formatted_prompt("knowledge_extraction_system")

            # Se falhar o carregamento do prompt, usar fallback direto no código
            if not system_prompt:
                system_prompt = """
                You are a Knowledge Extraction Expert. 
                Extract entities and relationships from the provided text.
                Return ONLY valid JSON with keys: "entities" (list) and "relationships" (list).
                Entities schema: { "name": str, "type": str, "description": str }
                Relationships schema: { "source": str, "target": str, "relation": str, "weight": float }
                Allowed Types: Person, Organization, Technology, Concept, Event, Location, Resource.
                """

            user_content = f"Text to analyze:\n{text[:4000]}"  # Truncate safety
            if metadata:
                user_content += f"\n\nContext Metadata:\n{json.dumps(metadata)}"

            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]

            response = await self.llm.ainvoke(messages)
            content = response.content

            # Parse JSON robusto
            return self._parse_json_response(content)

        except Exception as e:
            logger.error(f"Error extracting knowledge: {e}", exc_info=True)
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
            logger.warning(f"Failed to parse JSON from LLM response. Raw length: {len(content)}")
            return {}


# Singleton helper
_instance = None


def get_knowledge_extraction_service():
    global _instance
    if _instance is None:
        _instance = KnowledgeExtractionService()
    return _instance
