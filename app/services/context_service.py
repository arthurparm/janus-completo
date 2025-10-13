import structlog
from typing import Optional, Dict, Any

from app.repositories.context_repository import context_repository, ContextRepositoryError
from app.core.infrastructure.context_manager import ContextInfo, WebSearchResult

logger = structlog.get_logger(__name__)


class ContextServiceError(Exception):
    """Base exception for context service errors."""
    pass


class ContextService:
    """
    Camada de serviço para operações de contexto ambiental.
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    def get_current_context(self) -> ContextInfo:
        """Delega a busca do contexto ambiental atual para o repositório."""
        logger.info("Buscando contexto atual via serviço.")
        try:
            return context_repository.get_current_context()
        except ContextRepositoryError as e:
            logger.error("Erro no repositório ao buscar contexto atual", exc_info=e)
            raise ContextServiceError("Falha ao buscar o contexto atual.") from e

    def perform_web_search(self, query: str, max_results: int, search_depth: str) -> WebSearchResult:
        """Delega a busca na web para o repositório."""
        logger.info("Realizando busca na web via serviço", query=query)
        try:
            return context_repository.search_web(query, max_results, search_depth)
        except ContextRepositoryError as e:
            logger.error("Erro no repositório ao realizar busca na web", exc_info=e)
            raise ContextServiceError("Falha ao realizar a busca na web.") from e

    def get_enriched_context(self, query: Optional[str], include_web_search: bool, max_web_results: int) -> Dict[
        str, Any]:
        """Delega a busca por contexto enriquecido para o repositório."""
        logger.info("Buscando contexto enriquecido via serviço", include_web_search=include_web_search)
        try:
            return context_repository.get_enriched_context(query, include_web_search, max_web_results)
        except ContextRepositoryError as e:
            logger.error("Erro no repositório ao buscar contexto enriquecido", exc_info=e)
            raise ContextServiceError("Falha ao buscar o contexto enriquecido.") from e

    def get_formatted_context_for_prompt(self, include_datetime: bool, include_system: bool,
                                         web_query: Optional[str]) -> str:
        """Orquestra a formatação do contexto para ser usado em um prompt de LLM."""
        logger.info("Formatando contexto para prompt via serviço", web_query=web_query)
        try:
            web_results = None
            if web_query:
                # A lógica de negócio de chamar a busca web antes de formatar fica no serviço
                web_results = self.perform_web_search(web_query, max_results=3, search_depth="basic")

            return context_repository.format_context_for_prompt(include_datetime, include_system, web_results)
        except ContextRepositoryError as e:
            logger.error("Erro no repositório ao formatar contexto para prompt", exc_info=e)
            raise ContextServiceError("Falha ao formatar o contexto para prompt.") from e


# Instância única do serviço
context_service = ContextService()
