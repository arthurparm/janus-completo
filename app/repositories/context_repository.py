import structlog
from typing import Optional

from app.core.infrastructure.context_manager import context_manager, ContextInfo, WebSearchResult

logger = structlog.get_logger(__name__)

class ContextRepositoryError(Exception):
    """Base exception for context repository errors."""
    pass

class ContextRepository:
    """
    Camada de Repositório para o Context Manager.
    Abstrai todas as interações diretas com a infraestrutura de contexto.
    """

    def get_current_context(self) -> ContextInfo:
        """Busca o contexto ambiental atual a partir do manager."""
        logger.debug("Buscando contexto atual no repositório.")
        try:
            return context_manager.get_current_context()
        except Exception as e:
            logger.error("Erro no repositório ao buscar contexto atual", exc_info=e)
            raise ContextRepositoryError("Falha ao buscar o contexto atual.") from e

    def search_web(self, query: str, max_results: int, search_depth: str) -> WebSearchResult:
        """Realiza uma busca na web através do manager."""
        logger.debug("Realizando busca na web no repositório", query=query)
        try:
            return context_manager.search_web(
                query=query,
                max_results=max_results,
                search_depth=search_depth
            )
        except Exception as e:
            logger.error("Erro no repositório ao realizar busca na web", exc_info=e)
            raise ContextRepositoryError("Falha ao realizar a busca na web.") from e

    def get_enriched_context(self, query: Optional[str], include_web_search: bool, max_web_results: int) -> dict:
        """Busca o contexto enriquecido através do manager."""
        logger.debug("Buscando contexto enriquecido no repositório", include_web_search=include_web_search)
        try:
            return context_manager.get_enriched_context(
                query=query,
                include_web_search=include_web_search,
                max_web_results=max_web_results
            )
        except Exception as e:
            logger.error("Erro no repositório ao buscar contexto enriquecido", exc_info=e)
            raise ContextRepositoryError("Falha ao buscar o contexto enriquecido.") from e

    def format_context_for_prompt(self, include_datetime: bool, include_system: bool,
                                  web_results: Optional[WebSearchResult]) -> str:
        """Formata o contexto para prompt através do manager."""
        logger.debug("Formatando contexto para prompt no repositório.")
        try:
            return context_manager.format_context_for_prompt(
                include_datetime=include_datetime,
                include_system=include_system,
                web_results=web_results
            )
        except Exception as e:
            logger.error("Erro no repositório ao formatar contexto para prompt", exc_info=e)
            raise ContextRepositoryError("Falha ao formatar o contexto para prompt.") from e


# Padrão de Injeção de Dependência: Getter para o repositório
def get_context_repository() -> ContextRepository:
    return ContextRepository()
