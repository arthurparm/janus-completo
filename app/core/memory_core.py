
import base64
import json
import logging
import math
import re
import asyncio
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from langchain_openai import OpenAIEmbeddings
from prometheus_client import Counter, Histogram
from qdrant_client import models, AsyncQdrantClient

from app.config import settings
from app.db.vector_store import get_async_qdrant_client, aget_or_create_collection
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

# Constantes de timeout
_EMBEDDING_TIMEOUT = 30
_QDRANT_WRITE_TIMEOUT = 10
_QDRANT_SEARCH_TIMEOUT = 10

# Métricas
_MEM_HITS = Counter("memory_layer_hits_total", "Hits por camada de memória", ["layer"])
_MEM_MISSES = Counter("memory_layer_misses_total", "Misses por camada de memória", ["layer"])
_MEM_BYTES = Counter("memory_bytes_total", "Bytes processados pela memória", ["direction", "layer"])
_MEM_OPS = Counter("memory_ops_total", "Operações de memória", ["op", "layer", "outcome"])
_MEM_LAT = Histogram("memory_latency_seconds", "Latência por operação de memória", ["op", "layer", "outcome"])

def _now() -> float:
    return time.time()

def _approx_bytes(s: str) -> int:
    try:
        return len(s.encode("utf-8"))
    except Exception:
        return len(s)

def _detect_pii(text: str) -> Tuple[bool, List[str]]:
    types: List[str] = []
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        types.append("email")
    if re.search(r"\b\+?\d[\d\s().-]{7,}\b", text):
        types.append("phone")
    if re.search(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", text):
        types.append("cc")
    if re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text):
        types.append("cpf")
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        types.append("ssn")
    return (len(types) > 0, types)

def _mask_pii(text: str) -> str:
    text = re.sub(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}", "***@***.***", text)
    text = re.sub(r"\b\+?\d[\d\s().-]{7,}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CC]", text)
    text = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[REDACTED_CPF]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    return text

def _xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return bytes(out)

def encrypt_text(text: str) -> str:
    """
    Ofusca o texto usando uma cifra XOR simples.

    AVISO DE SEGURANÇA: Isto NÃO é criptografia real e não deve ser usado
    em ambientes de produção para proteger dados sensíveis. É apenas uma
    ofuscação para evitar que os dados sejam imediatamente legíveis.
    Use uma biblioteca criptográfica adequada (ex: `cryptography`) para
    segurança real.
    """
    key = (settings.MEMORY_ENCRYPTION_KEY or "").encode("utf-8")
    if not key:
        return text
    raw = text.encode("utf-8")
    enc = _xor_bytes(raw, key)
    return "enc::" + base64.b64encode(enc).decode("ascii")

def decrypt_text(text: str) -> str:
    """
    Desfaz a ofuscação do texto. Veja o aviso de segurança em `encrypt_text`.
    """
    if not isinstance(text, str):
        return str(text)
    if not text.startswith("enc::"):
        return text
    key = (settings.MEMORY_ENCRYPTION_KEY or "").encode("utf-8")
    try:
        enc = base64.b64decode(text[len("enc::"):])
        dec = _xor_bytes(enc, key)
        return dec.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"Falha ao descriptografar texto: {e}")
        return text

def _sanitize_metadata(metadata: dict) -> dict:
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            try:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            except (TypeError, OverflowError):
                sanitized[key] = str(value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized

class ShortTermMemory:
    def __init__(self, ttl_seconds: int, max_items: int, encoder: Optional[OpenAIEmbeddings]):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.encoder = encoder
        self._store: "OrderedDict[str, Tuple[float, Optional[List[float]], str, dict]]" = OrderedDict()
        self._lock = asyncio.Lock()

    async def _prune(self):
        async with self._lock:
            now = _now()
            keys_to_remove = [k for k, (ts, _, _, _) in self._store.items() if now - ts > self.ttl_seconds]
            for k in keys_to_remove:
                self._store.pop(k, None)
            while len(self._store) > self.max_items:
                self._store.popitem(last=False)

    async def aadd(self, exp_id: str, content: str, metadata: dict):
        ts = _now()
        vec: Optional[List[float]] = None
        try:
            if self.encoder:
                vec = await asyncio.wait_for(self.encoder.aembed_query(content), timeout=_EMBEDDING_TIMEOUT)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Erro ou timeout ao gerar embedding para STM: {e}")
            vec = None
        async with self._lock:
            self._store[exp_id] = (ts, vec, content, metadata)
            self._store.move_to_end(exp_id)
            await self._prune()

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b: return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return (dot / (na * nb)) if na and nb else 0.0

    async def asearch(self, query: str, n_results: int) -> List[dict]:
        await self._prune()
        async with self._lock:
            if not self._store:
                _MEM_MISSES.labels("short").inc()
                return []
        qv: Optional[List[float]] = None
        try:
            if self.encoder:
                qv = await asyncio.wait_for(self.encoder.aembed_query(query), timeout=_EMBEDDING_TIMEOUT)
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Erro ou timeout ao gerar embedding da query: {e}")
            qv = None
        scored: List[Tuple[str, float, str, dict]] = []
        async with self._lock:
            for exp_id, (ts, vec, content, metadata) in self._store.items():
                score = self._cosine(qv, vec) if qv and vec else (1.0 if query.lower() in content.lower() else 0.0)
                scored.append((exp_id, score, content, metadata))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [{"id": exp_id, "content": content, "metadata": metadata, "distance": 1 - min(max(score, 0.0), 1.0)} for exp_id, score, content, metadata in scored[:n_results]]
        if top: _MEM_HITS.labels("short").inc()
        else: _MEM_MISSES.labels("short").inc()
        return top

class EpisodicMemory:
    """Sistema de memória episódica com camadas short-term e long-term (Qdrant)."""

    def __init__(self):
        self.async_client: Optional[AsyncQdrantClient] = None
        self.encoder: Optional[OpenAIEmbeddings] = None
        self.short: Optional[ShortTermMemory] = None
        self._quota_lock = asyncio.Lock()
        self._quota_window_start = _now()
        self._per_origin_counts: Dict[str, int] = {}
        self._per_origin_bytes: Dict[str, int] = {}

    async def ainit(self):
        """Initializes all I/O-bound resources asynchronously."""
        logger.info("Inicializando EpisodicMemory de forma assíncrona...")
        self.async_client = get_async_qdrant_client()

        try:
            self.encoder = OpenAIEmbeddings()
            probe_vec = await self.encoder.aembed_query("dimension_probe")
            vector_dim = len(probe_vec)
            await aget_or_create_collection(
                collection_name=settings.QDRANT_COLLECTION_EPISODIC,
                vector_size=vector_dim
            )
            logger.info(f"Coleção '{settings.QDRANT_COLLECTION_EPISODIC}' verificada/criada com dimensão {vector_dim}.")
        except Exception as e:
            logger.warning(f"Falha ao inicializar OpenAIEmbeddings ou verificar coleção: {e}. Fallback para substring.")
            self.encoder = None

        self.short = ShortTermMemory(
            ttl_seconds=settings.MEMORY_SHORT_TTL_SECONDS,
            max_items=settings.MEMORY_SHORT_MAX_ITEMS,
            encoder=self.encoder,
        )
        logger.info("EpisodicMemory inicializada.")

    async def _reset_window_if_needed(self):
        async with self._quota_lock:
            if _now() - self._quota_window_start > settings.MEMORY_QUOTA_WINDOW_SECONDS:
                self._quota_window_start = _now()
                self._per_origin_counts.clear()
                self._per_origin_bytes.clear()

    async def _check_quota(self, origin: str, content: str) -> bool:
        await self._reset_window_if_needed()
        async with self._quota_lock:
            count = self._per_origin_counts.get(origin, 0)
            bytes_ = self._per_origin_bytes.get(origin, 0)
            if count >= settings.MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN:
                logger.warning({"event": "memory_quota_items_exceeded", "origin": origin})
                return False
            if bytes_ + _approx_bytes(content) > settings.MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN:
                logger.warning({"event": "memory_quota_bytes_exceeded", "origin": origin})
                return False
            return True

    async def _consume_quota(self, origin: str, content: str):
        async with self._quota_lock:
            self._per_origin_counts[origin] = self._per_origin_counts.get(origin, 0) + 1
            self._per_origin_bytes[origin] = self._per_origin_bytes.get(origin, 0) + _approx_bytes(content)

    async def amemorize(self, experience: Experience):
        start = time.perf_counter()
        if not self.short:
            logger.error("EpisodicMemory não inicializada. Chame ainit() primeiro.")
            return
        try:
            if not isinstance(experience.content, str) or not experience.content.strip():
                raise ValueError("content não pode ser vazio")
            if len(experience.content) > settings.MEMORY_MAX_CONTENT_CHARS:
                experience.content = experience.content[:settings.MEMORY_MAX_CONTENT_CHARS]

            origin = str(experience.metadata.get("origin") or experience.metadata.get("source") or "unknown").lower()
            if not await self._check_quota(origin, experience.content):
                _MEM_OPS.labels("memorize", "short", "denied").inc()
                return

            pii, types = _detect_pii(experience.content)
            if pii:
                experience.metadata["pii"] = True
                experience.metadata["pii_types"] = types
                if settings.MEMORY_PII_REDACT:
                    experience.content = _mask_pii(experience.content)

            await self.short.aadd(experience.id, experience.content, experience.metadata)
            _MEM_OPS.labels("memorize", "short", "success").inc()

            if self.async_client and self.encoder:
                try:
                    vector = await self.encoder.aembed_query(experience.content)
                    payload = experience.metadata.copy()
                    payload.update({'type': experience.type, 'timestamp': experience.timestamp, 'content': encrypt_text(experience.content)})
                    safe_payload = _sanitize_metadata(payload)

                    await self.async_client.upsert(
                        collection_name=settings.QDRANT_COLLECTION_EPISODIC,
                        points=[models.PointStruct(id=experience.id, vector=vector, payload=safe_payload)],
                        wait=True
                    )
                    _MEM_OPS.labels("memorize", "long", "success").inc()
                except Exception as e:
                    logger.error(f"Erro ao escrever no Qdrant: {e}", exc_info=True)
                    _MEM_OPS.labels("memorize", "long", "error").inc()
            else:
                _MEM_OPS.labels("memorize", "long", "skipped").inc()

            await self._consume_quota(origin, experience.content)
            _MEM_LAT.labels("memorize", "combined", "success").observe(time.perf_counter() - start)

        except Exception as e:
            logger.error(f"Erro ao memorizar a experiência {getattr(experience, 'id', '-')}: {e}", exc_info=True)

    async def arecall(self, query: str, n_results: int = 5) -> List[dict]:
        if not self.short:
            logger.error("EpisodicMemory não inicializada. Chame ainit() primeiro.")
            return []

        t0 = time.perf_counter()
        combined: List[dict] = []
        seen: set[str] = set()

        short_res = await self.short.asearch(query, n_results)
        combined.extend(short_res)
        seen.update([r["id"] for r in short_res])

        if self.async_client and self.encoder and len(combined) < n_results:
            try:
                query_vector = await self.encoder.aembed_query(query)
                limit = n_results * 2
                search_results = await self.async_client.search(
                    collection_name=settings.QDRANT_COLLECTION_EPISODIC,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True
                )
                long_items = []
                for sp in search_results:
                    if str(sp.id) not in seen:
                        content = decrypt_text(sp.payload.get('content', ''))
                        item = {"id": str(sp.id), "content": content, "metadata": {k: v for k, v in sp.payload.items() if k != 'content'}, "distance": 1 - sp.score}
                        long_items.append(item)
                        if len(combined) + len(long_items) >= n_results:
                            break
                combined.extend(long_items)
            except Exception as e:
                logger.error(f"Erro na busca long-term (Qdrant): {e}", exc_info=True)

        logger.info(f"Recordadas {len(combined)} experiências para a consulta: '{query[:100]}...'")
        return combined

    async def arecall_filtered(
        self,
        query: str,
        n_results: int = 5,
        filter_by_type: Optional[str] = None,
        filter_by_origin: Optional[str] = None,
        min_score: float = 0.0,
        time_range: Optional[tuple[float, float]] = None
    ) -> List[dict]:
        """
        Busca avançada com filtros por tipo, origem, score mínimo e intervalo de tempo.

        Args:
            query: Query de busca
            n_results: Número de resultados
            filter_by_type: Filtro por tipo de experiência
            filter_by_origin: Filtro por origem
            min_score: Score mínimo de similaridade (0.0 a 1.0)
            time_range: Tupla (timestamp_inicio, timestamp_fim)

        Returns:
            Lista de experiências filtradas
        """
        if not self.async_client or not self.encoder:
            logger.warning("Cliente Qdrant ou encoder não disponível para busca filtrada.")
            return await self.arecall(query, n_results)

        try:
            query_vector = await self.encoder.aembed_query(query)

            # Constrói filtros Qdrant
            filter_conditions = []

            if filter_by_type:
                filter_conditions.append(
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value=filter_by_type)
                    )
                )

            if filter_by_origin:
                filter_conditions.append(
                    models.FieldCondition(
                        key="origin",
                        match=models.MatchValue(value=filter_by_origin)
                    )
                )

            if time_range:
                start_ts, end_ts = time_range
                filter_conditions.append(
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(
                            gte=start_ts,
                            lte=end_ts
                        )
                    )
                )

            # Busca com filtros
            search_params = {
                "collection_name": settings.QDRANT_COLLECTION_EPISODIC,
                "query_vector": query_vector,
                "limit": n_results * 2,
                "with_payload": True,
                "score_threshold": min_score
            }

            if filter_conditions:
                search_params["query_filter"] = models.Filter(
                    must=filter_conditions
                )

            search_results = await self.async_client.search(**search_params)

            # Processa resultados
            results = []
            for sp in search_results[:n_results]:
                content = decrypt_text(sp.payload.get('content', ''))
                item = {
                    "id": str(sp.id),
                    "content": content,
                    "metadata": {k: v for k, v in sp.payload.items() if k != 'content'},
                    "distance": 1 - sp.score,
                    "score": sp.score
                }
                results.append(item)

            logger.info(f"Busca filtrada: {len(results)} resultados para '{query[:50]}...'")
            return results

        except Exception as e:
            logger.error(f"Erro na busca filtrada: {e}", exc_info=True)
            return await self.arecall(query, n_results)

    async def arecall_by_timeframe(
        self,
        query: str,
        hours_ago: int = 24,
        n_results: int = 5
    ) -> List[dict]:
        """
        Busca memórias dentro de um período de tempo específico.

        Args:
            query: Query de busca
            hours_ago: Quantas horas atrás buscar
            n_results: Número de resultados

        Returns:
            Lista de experiências no período
        """
        now = _now()
        start_time = now - (hours_ago * 3600)

        return await self.arecall_filtered(
            query=query,
            n_results=n_results,
            time_range=(start_time, now)
        )

    async def arecall_recent_failures(self, n_results: int = 10) -> List[dict]:
        """
        Busca especificamente por falhas recentes para análise.

        Args:
            n_results: Número de falhas a retornar

        Returns:
            Lista de experiências de falha
        """
        return await self.arecall_filtered(
            query="error failure exception falha erro",
            n_results=n_results,
            filter_by_type="action_failure"
        )

memory_core = EpisodicMemory()

async def initialize_memory_core():
    await memory_core.ainit()
