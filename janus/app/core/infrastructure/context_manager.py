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
import threading
import time
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

import msgpack
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

# Métricas Prometheus (opcional)
try:
    from prometheus_client import Counter, Gauge  # type: ignore

    _PROM_ENABLED = True
except Exception:
    _PROM_ENABLED = False

if _PROM_ENABLED:
    _WEB_CACHE_HITS = Counter("context_web_cache_hits_total", "Total de hits no cache de busca web")
    _WEB_CACHE_MISSES = Counter(
        "context_web_cache_misses_total", "Total de misses no cache de busca web"
    )
    _WEB_CACHE_SIZE = Gauge(
        "context_web_cache_size", "Itens atualmente armazenados no cache de busca web"
    )


class ContextInfo(BaseModel):
    """Informações de contexto ambiental."""

    timestamp: str = Field(description="Timestamp UTC atual")
    datetime_info: dict[str, str] = Field(description="Informações detalhadas de data/hora")
    system_info: dict[str, str] = Field(description="Informações do sistema")
    environment: str = Field(description="Ambiente de execução")


class WebSearchResult(BaseModel):
    """Resultado de busca na web."""

    query: str = Field(description="Query utilizada")
    results: list[dict[str, Any]] = Field(description="Resultados da busca")
    timestamp: str = Field(description="Timestamp da busca")

    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @staticmethod
    def from_msgpack(data: bytes) -> "WebSearchResult":
        obj = msgpack.unpackb(data, raw=False)
        return WebSearchResult(**obj)


class ContextManager:
    """
    Gerenciador de contexto ambiental para enriquecer a percepção do agente.
    """

    def __init__(self):
        self._tavily_client: TavilySearchAPIWrapper | None = None
        self._init_web_search()

        # Cache de busca web (LRU + TTL)
        self._web_cache: OrderedDict[str, tuple[float, WebSearchResult]] = OrderedDict()
        self._web_cache_lock = threading.Lock()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_ttl = int(getattr(settings, "CONTEXT_WEB_CACHE_TTL_SECONDS", 1800))
        self._cache_max_items = int(getattr(settings, "CONTEXT_WEB_CACHE_MAX_ITEMS", 512))

    def _init_web_search(self):
        """Inicializa o cliente de busca web (Tavily)."""
        try:
            tavily_secret = getattr(settings, "TAVILY_API_KEY", None)
            # Extrai o valor da SecretStr se existir
            tavily_key = getattr(tavily_secret, "get_secret_value", lambda: tavily_secret)()
            if tavily_key and str(tavily_key).strip():
                self._tavily_client = TavilySearchAPIWrapper(tavily_api_key=str(tavily_key).strip())
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
        logger.info("[GET_CURRENT_CONTEXT] Iniciando obtenção de contexto atual")
        now = datetime.now(UTC)

        context = ContextInfo(
            timestamp=now.isoformat(),
            datetime_info={
                "utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "day_of_week": now.strftime("%A"),
                "month": now.strftime("%B"),
                "year": str(now.year),
                "unix_timestamp": str(int(now.timestamp())),
            },
            system_info={
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
            },
            environment=settings.ENVIRONMENT,
        )

        logger.info(
            f"[GET_CURRENT_CONTEXT] ✓ Contexto obtido - {context.datetime_info['utc']}, {context.system_info['platform']}"
        )
        return context

    def search_web(
        self, query: str, max_results: int = 5, search_depth: str = "basic"
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
        logger.info(
            f"[SEARCH_WEB] Iniciando busca - query='{query}', max_results={max_results}, depth={search_depth}"
        )

        # Verifica cache antes de chamar Tavily
        key = self._make_cache_key(query, max_results, search_depth)
        now = time.time()
        cached: WebSearchResult | None = None
        with self._web_cache_lock:
            item = self._web_cache.get(key)
            if item:
                ts, result = item
                if now - ts < self._cache_ttl:
                    self._cache_hits += 1
                    # move to fim (mais recente)
                    self._web_cache.move_to_end(key)
                    cached = result
                    if _PROM_ENABLED:
                        _WEB_CACHE_HITS.inc()
                else:
                    # expirado
                    self._web_cache.pop(key, None)
        if cached:
            logger.info(f"[SEARCH_WEB] ✓ Cache HIT para '{query}'")
            return cached
        else:
            logger.info(f"[SEARCH_WEB] Cache MISS para '{query}'")
            self._cache_misses += 1
            if _PROM_ENABLED:
                _WEB_CACHE_MISSES.inc()

        if not self._tavily_client:
            logger.warning("[SEARCH_WEB] ⚠️ Tavily não disponível. Retornando resultados vazios.")
            return WebSearchResult(query=query, results=[], timestamp=datetime.now(UTC).isoformat())

        try:
            logger.info(f"[SEARCH_WEB] Chamando Tavily API para '{query}'")
            # Tavily API call - usa método run() que retorna string formatada
            raw_results = self._tavily_client.raw_results(
                query=query, max_results=max_results, search_depth=search_depth
            )

            logger.info(f"[SEARCH_WEB] Tavily API respondeu - tipo: {type(raw_results)}")
            logger.info(
                f"[SEARCH_WEB] Raw results keys: {raw_results.keys() if isinstance(raw_results, dict) else 'N/A'}"
            )

            # Estrutura os resultados
            results = []
            if isinstance(raw_results, dict) and "results" in raw_results:
                logger.info(
                    f"[SEARCH_WEB] Encontrado campo 'results' com {len(raw_results['results'])} itens"
                )
                for item in raw_results["results"][:max_results]:
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "score": item.get("score", 0.0),
                        }
                    )
            else:
                logger.warning(
                    f"[SEARCH_WEB] ⚠️ Formato inesperado - tipo={type(raw_results)}, conteúdo={str(raw_results)[:200]}"
                )

            logger.info(f"[SEARCH_WEB] ✓ Busca concluída: '{query}' - {len(results)} resultados")

            result_obj = WebSearchResult(
                query=query, results=results, timestamp=datetime.now(UTC).isoformat()
            )

            # Armazenar no cache
            with self._web_cache_lock:
                self._web_cache[key] = (time.time(), result_obj)
                # LRU: manter tamanho máximo
                while len(self._web_cache) > self._cache_max_items:
                    self._web_cache.popitem(last=False)
                if _PROM_ENABLED:
                    _WEB_CACHE_SIZE.set(len(self._web_cache))

            return result_obj

        except Exception as e:
            logger.error(f"[SEARCH_WEB] ❌ Erro ao buscar na web: {e}", exc_info=True)
            return WebSearchResult(query=query, results=[], timestamp=datetime.now(UTC).isoformat())

    def _make_cache_key(self, query: str, max_results: int, search_depth: str) -> str:
        q = (query or "").strip().lower()
        return f"{q}|{max_results}|{search_depth}"

    def get_web_cache_status(self) -> dict[str, Any]:
        """Retorna status atual do cache de busca web."""
        with self._web_cache_lock:
            size = len(self._web_cache)
        status = {
            "size": size,
            "ttl_seconds": self._cache_ttl,
            "max_items": self._cache_max_items,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
        }
        return status

    def invalidate_web_cache(self, query: str | None = None) -> dict[str, Any]:
        """Invalida entradas do cache. Se query for None, limpa todo o cache."""
        removed = 0
        with self._web_cache_lock:
            if not query:
                removed = len(self._web_cache)
                self._web_cache.clear()
            else:
                prefix = (query or "").strip().lower()
                keys_to_remove = [k for k in self._web_cache.keys() if k.startswith(prefix)]
                for k in keys_to_remove:
                    self._web_cache.pop(k, None)
                removed = len(keys_to_remove)
            if _PROM_ENABLED:
                _WEB_CACHE_SIZE.set(len(self._web_cache))
        return {"removed": removed, "remaining": len(self._web_cache)}

    def get_enriched_context(
        self, query: str | None = None, include_web_search: bool = False, max_web_results: int = 3
    ) -> dict[str, Any]:
        """
        Retorna contexto enriquecido, opcionalmente incluindo busca na web.

        Args:
            query: Query opcional para busca na web
            include_web_search: Se deve incluir busca na web
            max_web_results: Número máximo de resultados da web

        Returns:
            Dict com contexto completo
        """
        logger.info(
            f"[GET_ENRICHED_CONTEXT] Iniciando - include_web={include_web_search}, query='{query}'"
        )

        logger.info("[GET_ENRICHED_CONTEXT] Obtendo contexto ambiental")
        context = {"environmental": self.get_current_context().model_dump(), "web_search": None}

        if include_web_search and query:
            logger.info(f"[GET_ENRICHED_CONTEXT] Incluindo busca web para '{query}'")
            web_results = self.search_web(query, max_results=max_web_results)
            context["web_search"] = web_results.model_dump()
            logger.info(
                f"[GET_ENRICHED_CONTEXT] ✓ Busca web incluída - {len(web_results.results)} resultados"
            )
        else:
            logger.info("[GET_ENRICHED_CONTEXT] Busca web não solicitada")

        logger.info("[GET_ENRICHED_CONTEXT] ✓ Contexto enriquecido completo")
        return context

    def format_context_for_prompt(
        self,
        include_datetime: bool = True,
        include_system: bool = False,
        web_results: WebSearchResult | None = None,
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
        logger.info(
            f"[FORMAT_CONTEXT] Iniciando formatação - datetime={include_datetime}, system={include_system}, has_web={web_results is not None}"
        )

        parts = []

        if include_datetime:
            logger.info("[FORMAT_CONTEXT] Incluindo informações de data/hora")
            ctx = self.get_current_context()
            parts.append(f"Data/Hora Atual: {ctx.datetime_info['utc']}")
            parts.append(f"Dia da Semana: {ctx.datetime_info['day_of_week']}")

        if include_system:
            logger.info("[FORMAT_CONTEXT] Incluindo informações do sistema")
            ctx = self.get_current_context()
            parts.append(f"Sistema: {ctx.system_info['platform']}")
            parts.append(f"Ambiente: {ctx.environment}")

        if web_results and web_results.results:
            logger.info(
                f"[FORMAT_CONTEXT] Incluindo {len(web_results.results)} resultados de busca web"
            )
            parts.append(f"\nResultados da Busca Web ('{web_results.query}'):")
            for i, result in enumerate(web_results.results, 1):
                parts.append(f"{i}. {result['title']}")
                parts.append(f"   {result['content'][:200]}...")
                parts.append(f"   URL: {result['url']}")

        formatted = "\n".join(parts)
        logger.info(f"[FORMAT_CONTEXT] ✓ Contexto formatado - {len(formatted)} caracteres")
        return formatted


# Instância global
context_manager = ContextManager()
