import structlog

from app.core.infrastructure.context_manager import ContextInfo, WebSearchResult, context_manager

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
                query=query, max_results=max_results, search_depth=search_depth
            )
        except Exception as e:
            logger.error("Erro no repositório ao realizar busca na web", exc_info=e)
            raise ContextRepositoryError("Falha ao realizar a busca na web.") from e

    def get_enriched_context(
        self, query: str | None, include_web_search: bool, max_web_results: int
    ) -> dict:
        """Busca o contexto enriquecido através do manager."""
        logger.debug(
            "Buscando contexto enriquecido no repositório", include_web_search=include_web_search
        )
        try:
            return context_manager.get_enriched_context(
                query=query, include_web_search=include_web_search, max_web_results=max_web_results
            )
        except Exception as e:
            logger.error("Erro no repositório ao buscar contexto enriquecido", exc_info=e)
            raise ContextRepositoryError("Falha ao buscar o contexto enriquecido.") from e

    def format_context_for_prompt(
        self, include_datetime: bool, include_system: bool, web_results: WebSearchResult | None
    ) -> str:
        """Formata o contexto para prompt através do manager."""
        logger.debug("Formatando contexto para prompt no repositório.")
        try:
            return context_manager.format_context_for_prompt(
                include_datetime=include_datetime,
                include_system=include_system,
                web_results=web_results,
            )
        except Exception as e:
            logger.error("Erro no repositório ao formatar contexto para prompt", exc_info=e)
            raise ContextRepositoryError("Falha ao formatar o contexto para prompt.") from e

    def get_web_cache_status(self) -> dict:
        """Obtém o status atual do cache de busca web."""
        logger.debug("Obtendo status do cache web no repositório.")
        try:
            return context_manager.get_web_cache_status()
        except Exception as e:
            logger.error("Erro no repositório ao obter status do cache web", exc_info=e)
            raise ContextRepositoryError("Falha ao obter status do cache web.") from e

    def invalidate_web_cache(self, query: str | None) -> dict:
        """Invalida entradas do cache web (por query ou completo)."""
        logger.debug("Invalidando cache web no repositório.", query=query)
        try:
            return context_manager.invalidate_web_cache(query=query)
        except Exception as e:
            logger.error("Erro no repositório ao invalidar cache web", exc_info=e)
            raise ContextRepositoryError("Falha ao invalidar cache web.") from e


# Padrão de Injeção de Dependência: Getter para o repositório
def get_context_repository() -> ContextRepository:
    return ContextRepository()
