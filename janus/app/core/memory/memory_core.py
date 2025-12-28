import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import time
import re
import asyncio
from collections import OrderedDict
import math

from qdrant_client import AsyncQdrantClient, models
from app.core.infrastructure.resilience import CircuitBreaker, resilient

from app.config import settings
from app.models.schemas import Experience, ScoredExperience, VectorCollection
from app.core.infrastructure.resilience import resilient, CircuitBreaker
from app.core.embeddings.embedding_manager import embed_text, aembed_text
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
try:
    from opentelemetry import trace  # type: ignore
    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext
    _tracer = None

# Metrics (singleton imports to avoid duplicate registration)
from app.core.memory.metrics import (
    memory_short_cache_hits_total,
    memory_short_cache_misses_total,
    memory_short_cache_size,
    memory_quota_rejections_total,
    memory_operations_total,
)
from app.core.monitoring.health_monitor import get_timeout_recommendation, record_latency


logger = structlog.get_logger(__name__)


class MemoryCore:
    """
    Gerencia a conexão e as operações com o banco de dados vetorial (Qdrant).
    """

    def __init__(
        self,
        client: Optional[AsyncQdrantClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        config: Any = None
    ):
        """
        Inicializa o núcleo de memória com suporte a Injeção de Dependência.
        
        Args:
            client: Cliente Qdrant opcional (usado para mocks/testes)
            circuit_breaker: Circuit Breaker opcional
            config: Objeto de configuração opcional (se None, usa app.config.settings)
        """
        self.settings = config if config is not None else settings
        
        if client:
            self.client = client
        else:
            self.client = AsyncQdrantClient(
                host=self.settings.QDRANT_HOST, 
                port=self.settings.QDRANT_PORT
            )
            
        self.collection_name = VectorCollection.EPISODIC_MEMORY.value
        self._vector_size = int(getattr(self.settings, "MEMORY_VECTOR_SIZE", 1536))
        # Short-term cache (LRU + TTL)
        self._short_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._short_ttl = int(getattr(self.settings, "MEMORY_SHORT_TTL_SECONDS", 600))
        self._short_max_items = int(getattr(self.settings, "MEMORY_SHORT_MAX_ITEMS", 512))
        self._cache_lock = asyncio.Lock()
        # Origin quotas
        self._quota: Dict[str, Dict[str, Any]] = {}
        self._quota_window_s = int(getattr(self.settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        self._quota_max_items = int(getattr(self.settings, "MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN", 200))
        self._quota_max_bytes = int(getattr(self.settings, "MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN", 5_000_000))
        # Metrics (singleton references)
        self._short_hits = memory_short_cache_hits_total
        self._short_misses = memory_short_cache_misses_total
        self._short_size = memory_short_cache_size
        self._quota_rejections = memory_quota_rejections_total
        self._ops_total = memory_operations_total
        # Offline fallback flag
        self._offline = False
        
        if circuit_breaker:
            self._cb = circuit_breaker
        else:
            self._cb = CircuitBreaker(
                failure_threshold=int(getattr(self.settings, "LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3) or 3),
                recovery_timeout=int(getattr(self.settings, "LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT", 30) or 30),
            )
        self._last_revive_attempt = 0.0

    async def _try_revive_connection(self) -> bool:
        """Tentativa de reviver a conexão se estiver offline, com debounce."""
        now = time.time()
        # Evita spam de reconexão (minimo 10s entre tentativas)
        if (now - self._last_revive_attempt) < 10.0:
            return False
            
        self._last_revive_attempt = now
        try:
            # Tenta operação leve
            await self.client.get_collection(self.collection_name)
            logger.info("Conexão com Qdrant restabelecida! Saindo do modo offline.")
            self._offline = False
            # Opcional: resetar circuit breaker se estiver aberto
            if self._cb.is_open():
                self._cb.reset()
            return True
        except Exception:
            # Ainda indisponível
            return False

    async def initialize(self):
        """
        Garante que a coleção exista no Qdrant (async).
        Adiciona retry logic para suportar race conditions de inicialização.
        """
        max_retries = 20
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                try:
                    await self.client.get_collection(collection_name=self.collection_name)
                    logger.info(f"Coleção '{self.collection_name}' já existe.")
                except Exception:
                    # Se não existe (ou erro ao pegar), tenta criar.
                    # Qdrant client lança exceção se 404, mas as vezes pode ser connection error.
                    # Mas aqui assumimos que se falhar get, tentamos create.
                    # Se for connection error, o create vai falhar e caímos no except externo.
                    logger.info(f"Coleção '{self.collection_name}' (provavelmente) não encontrada. Tentando criar...")
                    await self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(size=self._vector_size, distance=models.Distance.COSINE),
                    )
                    logger.info("Coleção criada com sucesso (async).")
                
                # Sucesso
                self._offline = False
                return

            except Exception as e:
                is_last = (attempt == max_retries - 1)
                if is_last:
                    logger.warning("Qdrant indisponível após várias tentativas; ativando modo offline.", exc_info=e)
                    self._offline = True
                    return
                else:
                    delay = base_delay * (1.5 ** attempt)  # exponential backoff suave
                    logger.warning(f"Falha de conexão com Qdrant (tentativa {attempt+1}/{max_retries}). Retentando em {delay:.1f}s...", error=str(e))
                    await asyncio.sleep(delay)

    async def amemorize(self, experience: Experience):
        """
        Adiciona uma experiência à memória (upsert) com: PII masking, quotas, criptografia
        e cache de curto prazo (LRU+TTL).
        """
        # 1) Validar tamanho do conteúdo
        max_chars = int(getattr(self.settings, "MEMORY_MAX_CONTENT_CHARS", 20000))
        if isinstance(experience.content, str) and len(experience.content) > max_chars:
            raise ValueError(f"Conteúdo excede limite de {max_chars} caracteres")

        # 2) Janela de cota por origem
        origin = None
        try:
            origin = str((experience.metadata or {}).get("origin") or "unknown")
        except Exception:
            origin = "unknown"
        content_bytes = len(experience.content.encode("utf-8")) if isinstance(experience.content, str) else 0
        now_s = time.time()
        q = self._quota.get(origin, {"window_start": now_s, "items": 0, "bytes": 0})
        # reset janela se necessário
        if now_s - float(q.get("window_start", now_s)) >= self._quota_window_s:
            q = {"window_start": now_s, "items": 0, "bytes": 0}
        # verificação de cotas
        if (q["items"] + 1) > self._quota_max_items or (q["bytes"] + content_bytes) > self._quota_max_bytes:
            try:
                self._quota_rejections.inc()
            except Exception:
                pass
            raise ValueError("Cota de memorização excedida para a origem")

        # 3) PII masking (opcional)
        redacted_content = experience.content
        pii_detected: List[str] = []
        # 3) PII masking (opcional)
        redacted_content = experience.content
        pii_detected: List[str] = []
        if bool(getattr(self.settings, "MEMORY_PII_REDACT", True)) and isinstance(redacted_content, str):
            redacted_content, pii_detected = _redact_pii(redacted_content)

        # 4) Embedding (com conteúdo redigido)
        try:
            vector = await aembed_text(redacted_content)
        except Exception:
            logger.warning("Falha ao gerar embedding; usando vetor nulo.")
            vector = [0.0] * self._vector_size

        # 5) Timestamp auxiliar em ms
        try:
            dt = datetime.fromisoformat(experience.timestamp)
            ts_ms = int(dt.timestamp() * 1000)
        except Exception:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        # 6) Criptografia (opcional)
        encrypted_content, enc_method = encrypt_text(redacted_content)

        # 7) Montar payload e upsert
        payload = experience.dict()
        payload["ts_ms"] = ts_ms
        payload["content"] = encrypted_content
        meta = payload.get("metadata", {}) or {}
        if enc_method:
            meta["enc"] = enc_method
        if pii_detected:
            meta["pii"] = pii_detected
            meta["pii_redacted"] = True
        # Preserve type inside metadata for offline filtering/use
        try:
            if "type" in payload and payload["type"] is not None:
                meta["type"] = payload["type"]
        except Exception:
            pass
        payload["metadata"] = meta

        point = models.PointStruct(id=experience.id, payload=payload, vector=vector)
        if not self._offline:
            try:
                cm = (_tracer.start_as_current_span("memory.upsert") if _OTEL else nullcontext())
                async with cm as span:  # type: ignore
                    if _OTEL and span is not None:
                        try:
                            sid = USER_ID.get()
                            tid = TRACE_ID.get()
                            if sid and sid != "-":
                                span.set_attribute("janus.user_id", sid)
                            if tid and tid != "-":
                                span.set_attribute("janus.trace_id", tid)
                            span.set_attribute("memory.collection", self.collection_name)
                            span.set_attribute("memory.point_id", str(experience.id))
                        except Exception:
                            pass
                    await self.client.upsert(collection_name=self.collection_name, points=[point], wait=True)
            except Exception:
                logger.warning("Upsert no Qdrant falhou; armazenando apenas no cache.", exc_info=True)
                self._offline = True
        else:
            pass

        # 8) Atualiza quota
        q["items"] += 1
        q["bytes"] += content_bytes
        self._quota[origin] = q

        # 9) Adiciona no cache curto (LRU+TTL)
        try:
            async with self._cache_lock:
                expires_at = now_s + self._short_ttl
                self._short_cache[experience.id] = {
                    "id": experience.id,
                    "content": encrypted_content,
                    "metadata": meta,
                    "type": meta.get("type"),
                    "vector": vector,
                    "expires_at": expires_at,
                    "ts_ms": ts_ms,
                }
                self._short_cache.move_to_end(experience.id)
                while len(self._short_cache) > self._short_max_items:
                    self._short_cache.popitem(last=False)
                try:
                    self._short_size.set(len(self._short_cache))
                except Exception:
                    pass
        except Exception:
            logger.debug("Falha ao adicionar item no cache curto prazo", exc_info=True)
        try:
            self._ops_total.labels(operation="memorize").inc()
        except Exception:
            pass

    async def arecall(self, query: str, limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[ScoredExperience]:
        """
        Busca por experiências combinando cache de curto prazo (LRU+TTL) e Qdrant.
        """
        # 1) Vetor da consulta
        try:
            query_vector = await aembed_text(query)
        except Exception:
            logger.warning("Falha ao gerar embedding da consulta; usando vetor nulo.")
            query_vector = [0.0] * self._vector_size

        effective_limit = int(limit) if limit is not None else 10

        # 2) Buscar no cache curto prazo
        cache_results: List[ScoredExperience] = []
        try:
            async with self._cache_lock:
                now_s = time.time()
                # Evict expirados primeiro
                expired_keys = [k for k, v in self._short_cache.items() if float(v.get("expires_at", 0)) <= now_s]
                for k in expired_keys:
                    self._short_cache.pop(k, None)
                if expired_keys:
                    try:
                        self._short_size.set(len(self._short_cache))
                    except Exception:
                        pass
                scan_limit = int(getattr(self.settings, "MEMORY_SHORT_SCAN_MAX_ITEMS", max(1, self._short_max_items // 4)))
                items = list(self._short_cache.items())
                if scan_limit < len(items):
                    items = items[-scan_limit:]
                for k, v in items:
                    vec = v.get("vector")
                    if not isinstance(vec, list):
                        continue
                    score = _cosine_similarity(query_vector, vec)
                    
                    # Create ScoredExperience from cache
                    cache_results.append(ScoredExperience(
                        id=v.get("id"),
                        content=decrypt_text(v.get("content"), v.get("metadata")),
                        type=v.get("type") or "unknown",
                        timestamp=datetime.now(timezone.utc).isoformat(), # Cache might allow approximate timestamp if not stored
                        metadata=v.get("metadata") or {},
                        score=float(score)
                    ))
                    # LRU: move para o fim ao acessar
                    self._short_cache.move_to_end(k)
        except Exception:
            logger.debug("Falha ao consultar cache curto prazo", exc_info=True)

        # 3) Buscar no Qdrant
        qdrant_results: List[Dict[str, Any]] = []
        
        # Tenta reviver se estiver offline
        if self._offline:
            await self._try_revive_connection()

        if not self._offline:
            try:
                import asyncio as _asyncio
                from app.core.monitoring.health_monitor import get_timeout_recommendation, record_latency
                @resilient(
                    max_attempts=int(getattr(self.settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
                    initial_backoff=float(getattr(self.settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
                    max_backoff=float(getattr(self.settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
                    circuit_breaker=self._cb,
                    operation_name="qdrant_search",
                )
                async def _search():
                    # Progressive timeout reduction for retries
                    base_timeout = get_timeout_recommendation(
                        "qdrant_search",
                        float(getattr(self.settings, "QDRANT_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
                    )
                    
                    # Get current attempt number from circuit breaker context if available
                    current_attempt = getattr(self._cb, '_current_attempt', 0)
                    
                    # Reduce timeout for subsequent attempts (but not below 5 seconds)
                    if current_attempt > 0:
                        progressive_timeout = max(5.0, base_timeout * (0.8 ** current_attempt))
                    else:
                        progressive_timeout = base_timeout
                    
                    logger.info(
                        "qdrant_search_attempt",
                        attempt=current_attempt + 1,
                        base_timeout=base_timeout,
                        progressive_timeout=progressive_timeout,
                        limit=effective_limit,
                        collection_name=self.collection_name,
                        circuit_breaker_state=self._cb.state.value,
                        failure_count=self._cb.failure_count
                    )
                    
                    result = await self.client.query_points(
                        collection_name=self.collection_name,
                        query=query_vector,
                        limit=effective_limit,
                        with_payload=True,
                        timeout=int(progressive_timeout)
                    )
                    return result.points
                
                _start = _asyncio.get_event_loop().time()
                
                cm = (_tracer.start_as_current_span("memory.search") if _OTEL else nullcontext())
                async with cm as span:  # type: ignore
                    if _OTEL and span is not None:
                        try:
                            sid = USER_ID.get()
                            tid = TRACE_ID.get()
                            if sid and sid != "-":
                                span.set_attribute("janus.user_id", sid)
                            if tid and tid != "-":
                                span.set_attribute("janus.trace_id", tid)
                            span.set_attribute("memory.collection", self.collection_name)
                            span.set_attribute("memory.limit", effective_limit)
                            span.set_attribute("memory.circuit_breaker_state", self._cb.state.value)
                            span.set_attribute("memory.failure_count", self._cb.failure_count)
                        except Exception:
                            pass
                    
                    # Execute search with timeout monitoring
                    try:
                        hits = await _search()
                    except asyncio.TimeoutError as timeout_error:
                        logger.error(
                            "qdrant_search_timeout",
                            timeout=getattr(timeout_error, 'timeout', 'unknown'),
                            collection_name=self.collection_name,
                            limit=effective_limit,
                            circuit_breaker_state=self._cb.state.value,
                            failure_count=self._cb.failure_count
                        )
                        raise
                    except Exception as search_error:
                        logger.error(
                            "qdrant_search_exception",
                            error_type=type(search_error).__name__,
                            error_message=str(search_error),
                            collection_name=self.collection_name,
                            limit=effective_limit,
                            circuit_breaker_state=self._cb.state.value,
                            failure_count=self._cb.failure_count
                        )
                        raise
                try:
                    record_latency("qdrant_search", _asyncio.get_event_loop().time() - _start)
                except Exception:
                    pass
                qdrant_results = [ScoredExperience(
                    id=hit.id if hit.id else str(uuid.uuid4()),
                    content=decrypt_text(hit.payload.get('content'), hit.payload.get('metadata')),
                    type=hit.payload.get('type') or "episodic",
                    timestamp=hit.payload.get('timestamp') or datetime.now(timezone.utc).isoformat(),
                    metadata=hit.payload.get('metadata') or {},
                    score=hit.score
                ) for hit in hits]
            except Exception as e:
                # Enhanced error logging with circuit breaker context
                error_context = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "circuit_breaker_state": "OPEN" if self._cb.is_open() else "CLOSED",
                    "circuit_breaker_failures": self._cb.failure_count,
                    "circuit_breaker_threshold": getattr(self._cb, 'failure_threshold', 'unknown'),
                    "offline_mode": self._offline,
                    "collection_name": self.collection_name,
                    "effective_limit": effective_limit,
                    "cache_results_count": len(cache_results),
                    "has_query_vector": bool(query_vector),
                    "query_vector_length": len(query_vector) if query_vector else 0
                }
                
                logger.error(
                    "qdrant_search_failed_fallback_to_cache",
                    **error_context,
                    exc_info=True
                )
                
                # Log specific circuit breaker state details
                if self._cb.is_open():
                    logger.critical(
                        "qdrant_search_blocked_by_open_circuit_breaker",
                        operation="qdrant_search",
                        circuit_breaker_failures=self._cb.failure_count,
                        circuit_breaker_threshold=getattr(self._cb, 'failure_threshold', 'unknown'),
                        recovery_timeout=getattr(self._cb, 'recovery_timeout', 'unknown'),
                        recommendation="Circuit breaker is open - Qdrant calls are blocked. Using cache fallback."
                    )
                else:
                    logger.warning(
                        "qdrant_search_failed_circuit_breaker_closed",
                        **error_context,
                        recommendation="Qdrant search failed but circuit breaker is closed - this failure will count toward threshold"
                    )
                
                self._offline = True
        # 4) Combinar e deduplicar por ID
        combined: Dict[str, ScoredExperience] = {}
        for r in cache_results + qdrant_results:
            rid = str(r.id)
            prev = combined.get(rid)
            if prev is None or (r.score or 0.0) > (prev.score or 0.0):
                combined[rid] = r

        results = sorted(combined.values(), key=lambda x: float(x.score or 0.0), reverse=True)
        # 5) Filtro por min_score
        if min_score is not None:
            results = [r for r in results if float(r.score or 0.0) >= float(min_score)]
        # 6) Limite
        results = results[:effective_limit]

        # 7) Métricas de cache
        try:
            if cache_results:
                self._short_hits.inc()
            else:
                self._short_misses.inc()
        except Exception:
            pass

        try:
            if cache_results:
                self._short_hits.inc()
            else:
                self._short_misses.inc()
        except Exception:
            pass
        try:
            self._ops_total.labels(operation="recall").inc()
        except Exception:
            pass
        return results

    def _build_filter(self, filters: Dict[str, Any]) -> Optional[models.Filter]:
        if not filters:
            return None
        must: List[models.FieldCondition] = []
        for k, v in filters.items():
            if v is None:
                continue
            key = k
            # suportar chaves de metadados via shorthand
            if k in ("origin", "status"):
                key = f"metadata.{k}"
            # condição de igualdade simples
            try:
                must.append(models.FieldCondition(key=key, match=models.MatchValue(value=v)))
            except Exception:
                # fallback: ignorar chaves não suportadas
                logger.debug("Ignorando filtro inválido", key=key, value=v)
        if not must:
            return None
        return models.Filter(must=must)

    async def arecall_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[ScoredExperience]:
        """
        Busca com filtros por payload (ex.: type, metadata.status, metadata.origin).
        """
        query_vector = [0.0] * self._vector_size
        if query:
            try:
                query_vector = await aembed_text(query)
            except Exception:
                logger.warning("Falha ao gerar embedding da consulta filtrada; usando vetor nulo.")
        eff_limit = limit or 10
        qfilter = self._build_filter(filters)
        if self._offline:
            # Tenta reviver
            if await self._try_revive_connection():
                pass # continua
            else:
                # Offline: retorna vazio para buscas filtradas complexas
                return []
        try:
            import asyncio as _asyncio
            @resilient(
                max_attempts=int(getattr(self.settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
                initial_backoff=float(getattr(self.settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
                max_backoff=float(getattr(self.settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
                circuit_breaker=self._cb,
                operation_name="qdrant_search_filtered",
            )
            async def _search_filtered():
                result = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=eff_limit,
                    with_payload=True,
                    query_filter=qfilter,
                )
                return result.points
            _start = _asyncio.get_event_loop().time()
            _timeout = get_timeout_recommendation(
                "qdrant_search",
                float(getattr(settings, "QDRANT_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
            )
            cm = (_tracer.start_as_current_span("memory.search_filtered") if _OTEL else nullcontext())
            async with cm as span:  # type: ignore
                if _OTEL and span is not None:
                    try:
                        sid = USER_ID.get()
                        tid = TRACE_ID.get()
                        if sid and sid != "-":
                            span.set_attribute("janus.user_id", sid)
                        if tid and tid != "-":
                            span.set_attribute("janus.trace_id", tid)
                        span.set_attribute("memory.collection", self.collection_name)
                        span.set_attribute("memory.limit", eff_limit)
                    except Exception:
                        pass
                hits = await _asyncio.wait_for(_search_filtered(), timeout=float(_timeout))
            try:
                record_latency("qdrant_search", _asyncio.get_event_loop().time() - _start)
            except Exception:
                pass
        except Exception:
            logger.warning("Busca filtrada no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [ScoredExperience(
            id=hit.id if hit.id else str(uuid.uuid4()),
            content=decrypt_text(hit.payload.get('content'), hit.payload.get('metadata')),
            type=hit.payload.get('type') or "episodic",
            timestamp=hit.payload.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            metadata=hit.payload.get('metadata') or {},
            score=hit.score
        ) for hit in hits]
        if min_score is not None:
            results = [r for r in results if float(r.score or 0.0) >= float(min_score)]
        try:
            self._ops_total.labels(operation="recall_filtered").inc()
        except Exception:
            pass
        return results

    async def arecall_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[ScoredExperience]:
        """
        Busca por janela temporal usando o campo auxiliar ts_ms.
        Se o período não puder ser aplicado no filtro, faz pós-filtragem em memória.
        """
        query_vector = [0.0] * self._vector_size
        if query:
            try:
                query_vector = await aembed_text(query)
            except Exception:
                logger.warning("Falha ao gerar embedding da consulta temporal; usando vetor nulo.")
        eff_limit = limit or 10

        qfilter: Optional[models.Filter] = None
        if start_ts_ms is not None or end_ts_ms is not None:
            try:
                rng = models.Range(
                    gte=start_ts_ms if start_ts_ms is not None else None,
                    lte=end_ts_ms if end_ts_ms is not None else None,
                )
                qfilter = models.Filter(must=[models.FieldCondition(key="ts_ms", range=rng)])
            except Exception:
                qfilter = None

        if self._offline:
            if not await self._try_revive_connection():
                return []
        try:
            import asyncio as _asyncio
            @resilient(
                max_attempts=int(getattr(self.settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
                initial_backoff=float(getattr(self.settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
                max_backoff=float(getattr(self.settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
                circuit_breaker=self._cb,
                operation_name="qdrant_search_timeframe",
            )
            async def _search_timeframe():
                result = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=eff_limit,
                    with_payload=True,
                    query_filter=qfilter,
                )
                return result.points
            _start = _asyncio.get_event_loop().time()
            _timeout = get_timeout_recommendation(
                "qdrant_search",
                float(getattr(settings, "QDRANT_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
            )
            cm = (_tracer.start_as_current_span("memory.search_timeframe") if _OTEL else nullcontext())
            async with cm as span:  # type: ignore
                if _OTEL and span is not None:
                    try:
                        sid = USER_ID.get()
                        tid = TRACE_ID.get()
                        if sid and sid != "-":
                            span.set_attribute("janus.user_id", sid)
                        if tid and tid != "-":
                            span.set_attribute("janus.trace_id", tid)
                        span.set_attribute("memory.collection", self.collection_name)
                        span.set_attribute("memory.limit", eff_limit)
                    except Exception:
                        pass
                hits = await _asyncio.wait_for(_search_timeframe(), timeout=float(_timeout))
            try:
                record_latency("qdrant_search", _asyncio.get_event_loop().time() - _start)
            except Exception:
                pass
        except Exception:
            logger.warning("Busca por janela no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [ScoredExperience(
            id=h.id if h.id else str(uuid.uuid4()),
            content=decrypt_text(h.payload.get('content'), h.payload.get('metadata')),
            type=h.payload.get('type') or "episodic",
            timestamp=h.payload.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            metadata=(h.payload.get('metadata') or {}) | {"ts_ms": h.payload.get('ts_ms')},
            score=h.score,
        ) for h in hits]
        # Pós-filtragem caso o filtro não tenha sido aplicado
        def within(ts: Optional[int]) -> bool:
            if ts is None:
                return True
            if start_ts_ms is not None and ts < start_ts_ms:
                return False
            if end_ts_ms is not None and ts > end_ts_ms:
                return False
            return True
        results = [
            r for r in results if within(r.metadata.get("ts_ms"))
        ]
        if min_score is not None:
            results = [r for r in results if float(r.score or 0.0) >= float(min_score)]
        try:
            self._ops_total.labels(operation="recall_timeframe").inc()
        except Exception:
            pass
        return results

    async def arecall_recent_failures(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[ScoredExperience]:
        """
        Busca falhas recentes usando metadata.status == 'failure' dentro de uma janela.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        window = timeframe_seconds if timeframe_seconds is not None else int(getattr(self.settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        start_ms = now_ms - (window * 1000)

        qfilter = models.Filter(must=[
            models.FieldCondition(key="metadata.status", match=models.MatchValue(value="failure")),
            models.FieldCondition(key="ts_ms", range=models.Range(gte=start_ms, lte=now_ms)),
        ])
        if self._offline:
            return []
        try:
            import asyncio as _asyncio
            @resilient(
                max_attempts=int(getattr(self.settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
                initial_backoff=float(getattr(self.settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
                max_backoff=float(getattr(self.settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
                circuit_breaker=self._cb,
                operation_name="qdrant_search_recent_failures",
            )
            async def _search_recent_failures():
                points, _ = await self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=qfilter,
                    limit=limit or 10,
                    with_payload=True,
                )
                return points
            _start = _asyncio.get_event_loop().time()
            _timeout = get_timeout_recommendation(
                "qdrant_search",
                float(getattr(settings, "QDRANT_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
            )
            cm = (_tracer.start_as_current_span("memory.search_recent_failures") if _OTEL else nullcontext())
            async with cm as span:  # type: ignore
                if _OTEL and span is not None:
                    try:
                        sid = USER_ID.get()
                        tid = TRACE_ID.get()
                        if sid and sid != "-":
                            span.set_attribute("janus.user_id", sid)
                        if tid and tid != "-":
                            span.set_attribute("janus.trace_id", tid)
                        span.set_attribute("memory.collection", self.collection_name)
                        span.set_attribute("memory.limit", limit or 10)
                    except Exception:
                        pass
                hits = await _asyncio.wait_for(_search_recent_failures(), timeout=float(_timeout))
            try:
                record_latency("qdrant_search", _asyncio.get_event_loop().time() - _start)
            except Exception:
                pass
        except Exception:
            logger.warning("Busca de falhas recentes no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [ScoredExperience(
            id=h.id if h.id else str(uuid.uuid4()),
            content=decrypt_text(h.payload.get('content'), h.payload.get('metadata')),
            type=h.payload.get('type') or "episodic",
            timestamp=h.payload.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            metadata=h.payload.get('metadata') or {},
            score=h.score
        ) for h in hits]
        if min_score is not None:
             results = [r for r in results if float(r.score or 0.0) >= float(min_score)]
        try:
            self._ops_total.labels(operation="recall_recent_failures").inc()
        except Exception:
            pass
        return results

    async def arecall_recent_lessons(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[ScoredExperience]:
        """
        Busca lições recentes usando type == 'lessons_learned' dentro de uma janela.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        window = timeframe_seconds if timeframe_seconds is not None else int(getattr(self.settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        start_ms = now_ms - (window * 1000)

        qfilter = models.Filter(must=[
            models.FieldCondition(key="type", match=models.MatchValue(value="lessons_learned")),
            models.FieldCondition(key="ts_ms", range=models.Range(gte=start_ms, lte=now_ms)),
        ])
        if self._offline:
            return []
        try:
            import asyncio as _asyncio
            @resilient(
                max_attempts=int(getattr(self.settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
                initial_backoff=float(getattr(self.settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
                max_backoff=float(getattr(self.settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
                circuit_breaker=self._cb,
                operation_name="qdrant_search_recent_lessons",
            )
            async def _search_recent_lessons():
                points, _ = await self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=qfilter,
                    limit=limit or 10,
                    with_payload=True,
                )
                return points
            _start = _asyncio.get_event_loop().time()
            _timeout = get_timeout_recommendation(
                "qdrant_search",
                float(getattr(settings, "QDRANT_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
            )
            cm = (_tracer.start_as_current_span("memory.search_recent_lessons") if _OTEL else nullcontext())
            async with cm as span:  # type: ignore
                if _OTEL and span is not None:
                    try:
                        sid = USER_ID.get()
                        tid = TRACE_ID.get()
                        if sid and sid != "-":
                            span.set_attribute("janus.user_id", sid)
                        if tid and tid != "-":
                            span.set_attribute("janus.trace_id", tid)
                        span.set_attribute("memory.collection", self.collection_name)
                        span.set_attribute("memory.limit", limit or 10)
                    except Exception:
                        pass
                hits = await _asyncio.wait_for(_search_recent_lessons(), timeout=float(_timeout))
            try:
                record_latency("qdrant_search", _asyncio.get_event_loop().time() - _start)
            except Exception:
                pass
        except Exception:
            logger.warning("Busca de lições recentes no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [ScoredExperience(
            id=h.id if h.id else str(uuid.uuid4()),
            content=decrypt_text(h.payload.get('content'), h.payload.get('metadata')),
            type=h.payload.get('type') or "episodic",
            timestamp=h.payload.get('timestamp') or datetime.now(timezone.utc).isoformat(),
            metadata=h.payload.get('metadata') or {},
            score=h.score
        ) for h in hits]
        if min_score is not None:
            results = [r for r in results if float(r.score or 0.0) >= float(min_score)]
        try:
            self._ops_total.labels(operation="recall_recent_lessons").inc()
        except Exception:
            pass
        return results

    def reset_circuit_breaker(self):
        """
        Reseta o circuit breaker para o estado CLOSED.
        Útil para recuperação manual após falhas de Qdrant.
        """
        try:
            self._cb.reset()
            self._offline = False
            logger.info("Circuit breaker resetado com sucesso")
        except Exception as e:
            logger.error("Erro ao resetar circuit breaker", exc_info=e)

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Obtém status detalhado do circuit breaker e métricas de saúde.
        
        Returns:
            Dict com status do circuit breaker, métricas e recomendações
        """
        try:
            # Get circuit breaker metrics
            cb_status = self._cb.get_health_status()
            
            # Get monitoring service status if available
            monitoring_status = None
            if hasattr(self, '_enhanced_client'):
                monitoring_service = get_qdrant_monitoring_service()
                if monitoring_service:
                    monitoring_status = monitoring_service.get_detailed_metrics()
            
            # Calculate system health
            is_healthy = not self._offline and not self._cb.is_open()
            health_score = 100.0
            
            if self._offline:
                health_score -= 50.0
            if self._cb.is_open():
                health_score -= 30.0
            if cb_status['metrics']['error_rate'] > 0.1:
                health_score -= 20.0
            
            health_score = max(0.0, health_score)
            
            # Generate recommendations
            recommendations = []
            if self._cb.is_open():
                recommendations.append("Circuit breaker is open - consider manual reset or wait for auto-recovery")
            if self._offline:
                recommendations.append("Qdrant is offline - check service availability")
            if cb_status['metrics']['error_rate'] > 0.2:
                recommendations.append("High error rate - investigate Qdrant performance")
            if cb_status['metrics']['average_response_time'] > 15.0:
                recommendations.append("High response times - consider scaling Qdrant")
            if not recommendations:
                recommendations.append("System appears healthy")
            
            return {
                "system_health": {
                    "is_healthy": is_healthy,
                    "health_score": health_score,
                    "offline": self._offline,
                    "circuit_breaker_open": self._cb.is_open(),
                    "last_check": datetime.now(timezone.utc).isoformat()
                },
                "circuit_breaker": cb_status,
                "monitoring": monitoring_status,
                "recommendations": recommendations,
                "configuration": {
                    "failure_threshold": RESILIENCE_CONFIG.circuit_breaker.failure_threshold,
                    "recovery_timeout": RESILIENCE_CONFIG.circuit_breaker.recovery_timeout,
                    "search_timeout": RESILIENCE_CONFIG.qdrant_timeouts.search_timeout,
                    "auto_recovery_enabled": RESILIENCE_CONFIG.enable_auto_recovery,
                    "auto_recovery_interval": RESILIENCE_CONFIG.auto_recovery_interval
                }
            }
            
        except Exception as e:
            logger.error("Erro ao obter status do circuit breaker", exc_info=e)
            return {
                "error": str(e),
                "system_health": {
                    "is_healthy": False,
                    "health_score": 0.0,
                    "offline": self._offline,
                    "circuit_breaker_open": self._cb.is_open() if hasattr(self, '_cb') else True,
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            }

    async def health_check(self) -> bool:
        try:
            # Use enhanced health check if available
            if hasattr(self, '_enhanced_client'):
                is_healthy = await self._enhanced_client.health_check(self.collection_name)
            else:
                # Fallback to basic health check
                await self.client.get_collection(collection_name=self.collection_name)
                is_healthy = True
            
            # Se Qdrant está funcionando, verifica se precisa resetar o circuit breaker
            if is_healthy and (self._offline or self._cb.is_open()):
                self.reset_circuit_breaker()
                logger.info("Qdrant health check passed - circuit breaker resetado")
            
            return is_healthy
            
        except Exception as e:
            logger.warning("Qdrant health check falhou", exc_info=e)
            return False


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_memory_db_instance: Optional[MemoryCore] = None


async def initialize_memory_db():
    global _memory_db_instance
    if _memory_db_instance is None:
        _memory_db_instance = MemoryCore()
        await _memory_db_instance.initialize()


async def close_memory_db():
    pass


async def check_memory_health() -> bool:
    """
    Função auxiliar para verificar a saúde do banco de dados de memória.
    Usada pelo KnowledgeService para health check integrado.
    """
    try:
        memory_db = await get_memory_db()
        return await memory_db.health_check()
    except Exception as e:
        logger.warning("Falha ao verificar saúde da memória", exc_info=e)
        return False


async def get_memory_db() -> MemoryCore:
    if _memory_db_instance is None:
        await initialize_memory_db()
    return _memory_db_instance


# --- Compatibilidade com código legado ---
memory_core = _memory_db_instance


# --- Utilitários: Similaridade, PII, Criptografia ---

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    try:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(dot / (na * nb))
    except Exception:
        return 0.0

_PII_PATTERNS = [
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE), "EMAIL", "[REDACTED_EMAIL]"),
    (re.compile(r"\+?\d[\d\-\s\(\)]{7,}\d"), "PHONE", "[REDACTED_PHONE]"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "CPF", "[REDACTED_CPF]"),
    (re.compile(r"\b\d{11}\b"), "CPF", "[REDACTED_CPF]"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "CNPJ", "[REDACTED_CNPJ]"),
    (re.compile(r"\b\d{14}\b"), "CNPJ", "[REDACTED_CNPJ]"),
    (re.compile(r"\b(?:\d[ \-]*?){13,16}\b"), "CARD", "[REDACTED_CARD]")
]

def _redact_pii(text: str) -> (str, List[str]):
    types: List[str] = []
    redacted = text
    for pat, name, repl in _PII_PATTERNS:
        if pat.search(redacted):
            types.append(name)
            redacted = pat.sub(repl, redacted)
    return redacted, types

# Criptografia usando Fernet (se disponível)
_fernet_obj = None

def _get_fernet():
    global _fernet_obj
    if _fernet_obj is not None:
        return _fernet_obj
    try:
        from cryptography.fernet import Fernet  # type: ignore
        key = getattr(settings, "MEMORY_ENCRYPTION_KEY", None)
        if not key:
            return None
        # Aceita chave Fernet URL-safe base64 ou frase secreta (deriva via SHA-256)
        k = str(key)
        if len(k) == 44:
            fkey = k
        else:
            import base64, hashlib
            digest = hashlib.sha256(k.encode("utf-8")).digest()
            fkey = base64.urlsafe_b64encode(digest).decode("utf-8")
        _fernet_obj = Fernet(fkey)
        return _fernet_obj
    except Exception:
        return None

_DEF_ENC = None

def encrypt_text(plain_text: str) -> (str, Optional[str]):
    f = _get_fernet()
    if f is None:
        return plain_text, None
    try:
        return f.encrypt(plain_text.encode("utf-8")).decode("utf-8"), "fernet"
    except Exception:
        return plain_text, None

# Atualiza assinatura: aceita metadata para decidir descriptografia

def decrypt_text(encrypted_text: Optional[str], metadata: Optional[Dict[str, Any]] = None) -> str:
    if encrypted_text is None:
        return ""
    enc_method = None
    try:
        if isinstance(metadata, dict):
            enc_method = metadata.get("enc")
    except Exception:
        enc_method = None
    if enc_method != "fernet":
        return encrypted_text
    f = _get_fernet()
    if f is None:
        # Sem chave disponível: retorna texto como está
        return encrypted_text
    try:
        return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Falha na decriptação: retorna o texto bruto
        return encrypted_text
