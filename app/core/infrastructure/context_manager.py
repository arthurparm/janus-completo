"""
Módulo de Contexto Ambiental - Sprint 3
Responsável por enriquecer o contexto do agente com informações sobre o ambiente:
- Data/hora atual
- Busca na web (Tavily)
- Informações do sistema
- Contexto de execução
"""

import logging
import platform
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class ContextInfo(BaseModel):
    """Informações de contexto ambiental."""
    timestamp: str = Field(description="Timestamp UTC atual")
    datetime_info: Dict[str, str] = Field(description="Informações detalhadas de data/hora")
    system_info: Dict[str, str] = Field(description="Informações do sistema")
    environment: str = Field(description="Ambiente de execução")


class WebSearchResult(BaseModel):
    """Resultado de busca na web."""
    query: str = Field(description="Query utilizada")
    results: List[Dict[str, Any]] = Field(description="Resultados da busca")
    timestamp: str = Field(description="Timestamp da busca")


class ContextManager:
    """
    Gerenciador de contexto ambiental para enriquecer a percepção do agente.
    """

    def __init__(self):
        self._tavily_client: Optional[TavilySearchAPIWrapper] = None
        self._init_web_search()

    def _init_web_search(self):
        """Inicializa o cliente de busca web (Tavily)."""
        try:
            # Verifica se a API key está configurada
            tavily_key = getattr(settings, "TAVILY_API_KEY", None)
            if tavily_key and str(tavily_key).strip():
                self._tavily_client = TavilySearchAPIWrapper()
                logger.info("Cliente Tavily inicializado com sucesso.")
            else:
                logger.warning("TAVILY_API_KEY não configurada. Busca web desabilitada.")
        except Exception as e:
            logger.error(f"Erro ao inicializar Tavily: {e}")
            self._tavily_client = None

    def get_current_context(self) -> ContextInfo:
        """
        Retorna o contexto ambiental atual.

        Returns:
            ContextInfo com timestamp, data/hora e informações do sistema
        """
        now = datetime.now(timezone.utc)

        return ContextInfo(
            timestamp=now.isoformat(),
            datetime_info={
                "utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "month": now.strftime("%B"),
                "year": str(now.year),
                "unix_timestamp": str(int(now.timestamp()))
            },
            system_info={
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "python_version": platform.python_version()
            },
            environment=settings.ENVIRONMENT
        )

    def search_web(
            self,
            query: str,
            max_results: int = 5,
            search_depth: str = "basic"
    ) -> WebSearchResult:
        """
        Realiza busca na web usando Tavily.

        Args:
            query: Query de busca
            max_results: Número máximo de resultados
            search_depth: Profundidade da busca ("basic" ou "advanced")

        Returns:
            WebSearchResult com os resultados da busca

        Raises:
            RuntimeError: Se o cliente Tavily não estiver disponível
        """
        if not self._tavily_client:
            logger.warning("Tavily não disponível. Retornando resultados vazios.")
            return WebSearchResult(
                query=query,
                results=[],
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        try:
            # Tavily API call
            raw_results = self._tavily_client.results(
                query=query,
                max_results=max_results,
                search_depth=search_depth
            )

            # Estrutura os resultados
            results = []
            if isinstance(raw_results, dict) and "results" in raw_results:
                for item in raw_results["results"][:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0)
                    })

            logger.info(f"Busca web concluída: '{query}' - {len(results)} resultados")

            return WebSearchResult(
                query=query,
                results=results,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        except Exception as e:
            logger.error(f"Erro ao buscar na web: {e}", exc_info=True)
            return WebSearchResult(
                query=query,
                results=[],
                timestamp=datetime.now(timezone.utc).isoformat()
            )

    def get_enriched_context(
            self,
            query: Optional[str] = None,
            include_web_search: bool = False,
            max_web_results: int = 3
    ) -> Dict[str, Any]:
        """
        Retorna contexto enriquecido, opcionalmente incluindo busca na web.

        Args:
            query: Query opcional para busca na web
            include_web_search: Se deve incluir busca na web
            max_web_results: Número máximo de resultados da web

        Returns:
            Dict com contexto completo
        """
        context = {
            "environmental": self.get_current_context().model_dump(),
            "web_search": None
        }

        if include_web_search and query:
            web_results = self.search_web(query, max_results=max_web_results)
            context["web_search"] = web_results.model_dump()

        return context

    def format_context_for_prompt(
            self,
            include_datetime: bool = True,
            include_system: bool = False,
            web_results: Optional[WebSearchResult] = None
    ) -> str:
        """
        Formata o contexto como string para inclusão em prompts.

        Args:
            include_datetime: Se deve incluir informações de data/hora
            include_system: Se deve incluir informações do sistema
            web_results: Resultados opcionais de busca web

        Returns:
            String formatada com o contexto
        """
        parts = []

        if include_datetime:
            ctx = self.get_current_context()
            parts.append(f"Data/Hora Atual: {ctx.datetime_info['utc']}")
            parts.append(f"Dia da Semana: {ctx.datetime_info['day_of_week']}")

        if include_system:
            ctx = self.get_current_context()
            parts.append(f"Sistema: {ctx.system_info['platform']}")
            parts.append(f"Ambiente: {ctx.environment}")

        if web_results and web_results.results:
            parts.append(f"\nResultados da Busca Web ('{web_results.query}'):")
            for i, result in enumerate(web_results.results, 1):
                parts.append(f"{i}. {result['title']}")
                parts.append(f"   {result['content'][:200]}...")
                parts.append(f"   URL: {result['url']}")

        return "\n".join(parts)


# Instância global
context_manager = ContextManager()
