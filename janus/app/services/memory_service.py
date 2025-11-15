import structlog
import time
try:
    from prometheus_client import Histogram, Counter
except Exception:
    class _Noop:
        def labels(self, *args, **kwargs):
            return self
        def observe(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
    Histogram = Counter = _Noop
from typing import List, Dict, Any, Optional  # Added Optional
from fastapi import Request

from app.core.protocols import MemoryRepositoryProtocol
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)
_MEMORY_SERVICE_LATENCY = Histogram("memory_service_latency_seconds", "Latência por operação do serviço de memória", ["operation"])
_MEMORY_SERVICE_ERRORS = Counter("memory_service_errors_total", "Erros no serviço de memória", ["operation","exception"])

class MemoryServiceError(Exception):
    """Base exception for memory service errors."""
    pass

class MemoryService:
    """
    Camada de serviço para operações relacionadas à memória episódica.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: MemoryRepositoryProtocol):
        self._repo = repo

    async def add_experience(self, type: str, content: str, metadata: Dict[str, Any]) -> Experience:
        """
        Cria uma nova experiência e a delega para o repositório salvar.
        """
        logger.info("Criando e salvando nova experiência via serviço", type=type)
        start = time.perf_counter()
        try:
            experience = Experience(
                type=type,
                content=content,
                metadata=metadata
            )
            await self._repo.save_experience(experience)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("add_experience").observe(elapsed)
            return experience
        except Exception as e:
            logger.error("Erro no serviço de memória ao adicionar experiência", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("add_experience", type(e).__name__).inc()
            raise MemoryServiceError("Falha ao adicionar experiência.") from e

    async def recall_experiences(self, query: str, limit: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Delega a busca por experiências para o repositório.
        """
        logger.info("Buscando experiências via serviço", query=query, limit=limit, min_score=min_score)
        start = time.perf_counter()
        try:
            result = await self._repo.search_experiences(query=query, limit=limit, min_score=min_score)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_experiences").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço de memória ao buscar experiências", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_experiences", type(e).__name__).inc()
            raise MemoryServiceError("Falha ao buscar experiências.") from e

    async def recall_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando experiências filtradas", query=query, filters=filters, limit=limit, min_score=min_score)
        start = time.perf_counter()
        try:
            result = await self._repo.search_filtered(query=query, filters=filters, limit=limit, min_score=min_score)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_filtered").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar filtrado", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_filtered", type(e).__name__).inc()
            raise MemoryServiceError("Falha na busca filtrada.") from e

    async def recall_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando por janela temporal", query=query, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, limit=limit, min_score=min_score)
        start = time.perf_counter()
        try:
            result = await self._repo.search_by_timeframe(query=query, start_ts_ms=start_ts_ms, end_ts_ms=end_ts_ms, limit=limit, min_score=min_score)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_by_timeframe").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar por janela temporal", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_by_timeframe", type(e).__name__).inc()
            raise MemoryServiceError("Falha na busca por janela temporal.") from e

    async def recall_recent_failures(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.debug("Service: recall_recent_failures", limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
        start = time.perf_counter()
        try:
            result = await self._repo.search_recent_failures(limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_recent_failures").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar falhas recentes", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_recent_failures", type(e).__name__).inc()
            raise MemoryServiceError(f"Erro ao buscar falhas recentes: {e}")

    async def recall_recent_lessons(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        logger.debug("Service: recall_recent_lessons", limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
        start = time.perf_counter()
        try:
            result = await self._repo.search_recent_lessons(limit=limit, timeframe_seconds=timeframe_seconds, min_score=min_score)
            elapsed = time.perf_counter() - start
            _MEMORY_SERVICE_LATENCY.labels("recall_recent_lessons").observe(elapsed)
            return result
        except Exception as e:
            logger.error("Erro no serviço ao buscar lições recentes", exc_info=e)
            _MEMORY_SERVICE_ERRORS.labels("recall_recent_lessons", type(e).__name__).inc()
            raise MemoryServiceError(f"Erro ao buscar lições recentes: {e}")

# Padrão de Injeção de Dependência: Getter para o serviço
def get_memory_service(request: Request) -> MemoryService:
    return request.app.state.memory_service
