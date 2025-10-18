import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import time
import re
import asyncio
from collections import OrderedDict
import math

from qdrant_client import QdrantClient, models

from app.config import settings
from app.models.schemas import Experience, VectorCollection
from app.core.embeddings.embedding_manager import embed_text

# Métricas (fallback para no-op se prometheus não estiver disponível)
try:
    from prometheus_client import Counter, Gauge  # type: ignore
except Exception:
    class _Noop:
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
    Counter = Gauge = _Noop  # type: ignore

logger = structlog.get_logger(__name__)


class MemoryCore:
    """
    Gerencia a conexão e as operações com o banco de dados vetorial (Qdrant).
    """

    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = VectorCollection.EPISODIC_MEMORY.value
        self._vector_size = int(getattr(settings, "MEMORY_VECTOR_SIZE", 1536))
        # Short-term cache (LRU + TTL)
        self._short_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._short_ttl = int(getattr(settings, "MEMORY_SHORT_TTL_SECONDS", 600))
        self._short_max_items = int(getattr(settings, "MEMORY_SHORT_MAX_ITEMS", 512))
        self._cache_lock = asyncio.Lock()
        # Origin quotas
        self._quota: Dict[str, Dict[str, Any]] = {}
        self._quota_window_s = int(getattr(settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        self._quota_max_items = int(getattr(settings, "MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN", 200))
        self._quota_max_bytes = int(getattr(settings, "MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN", 5_000_000))
        # Metrics
        self._short_hits = Counter("memory_short_cache_hits_total", "Cache curto prazo: hits")
        self._short_misses = Counter("memory_short_cache_misses_total", "Cache curto prazo: misses")
        self._short_size = Gauge("memory_short_cache_size", "Itens no cache curto prazo")
        self._quota_rejections = Counter("memory_quota_rejections_total", "Rejeições por cota excedida")
        # Offline fallback flag
        self._offline = False

    async def initialize(self):
        """
        Garante que a coleção exista no Qdrant.
        """
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                logger.info(f"Coleção '{self.collection_name}' não encontrada. Criando nova coleção...")
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=self._vector_size, distance=models.Distance.COSINE),
                )
                logger.info("Coleção criada com sucesso.")
            else:
                logger.info(f"Coleção '{self.collection_name}' já existe.")
        except Exception as e:
            logger.warning("Qdrant indisponível; ativando modo offline.", exc_info=e)
            self._offline = True
            return

    async def amemorize(self, experience: Experience):
        """
        Adiciona uma experiência à memória (upsert) com: PII masking, quotas, criptografia
        e cache de curto prazo (LRU+TTL).
        """
        # 1) Validar tamanho do conteúdo
        max_chars = int(getattr(settings, "MEMORY_MAX_CONTENT_CHARS", 20000))
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
        if bool(getattr(settings, "MEMORY_PII_REDACT", True)) and isinstance(redacted_content, str):
            redacted_content, pii_detected = _redact_pii(redacted_content)

        # 4) Embedding (com conteúdo redigido)
        try:
            vector = embed_text(redacted_content)
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
                self.client.upsert(collection_name=self.collection_name, points=[point], wait=True)
            except Exception:
                logger.warning("Upsert no Qdrant falhou; armazenando apenas no cache.", exc_info=True)
                self._offline = True
        else:
            # Offline: skip Qdrant upsert
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

    async def arecall(self, query: str, limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Busca por experiências combinando cache de curto prazo (LRU+TTL) e Qdrant.
        """
        # 1) Vetor da consulta
        try:
            query_vector = embed_text(query)
        except Exception:
            logger.warning("Falha ao gerar embedding da consulta; usando vetor nulo.")
            query_vector = [0.0] * self._vector_size

        effective_limit = int(limit) if limit is not None else 10

        # 2) Buscar no cache curto prazo
        cache_results: List[Dict[str, Any]] = []
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
                # Similaridade coseno com todos os itens
                for k, v in list(self._short_cache.items()):
                    vec = v.get("vector")
                    if not isinstance(vec, list):
                        continue
                    score = _cosine_similarity(query_vector, vec)
                    cache_results.append({
                        "id": v.get("id"),
                        "content": decrypt_text(v.get("content"), v.get("metadata")),
                        "metadata": v.get("metadata") or {},
                        "score": float(score)
                    })
                    # LRU: move para o fim ao acessar
                    self._short_cache.move_to_end(k)
        except Exception:
            logger.debug("Falha ao consultar cache curto prazo", exc_info=True)

        # 3) Buscar no Qdrant
        qdrant_results: List[Dict[str, Any]] = []
        if not self._offline:
            try:
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=effective_limit,
                    with_payload=True,
                )
                qdrant_results = [{
                    "id": hit.id,
                    "content": decrypt_text(hit.payload.get('content'), hit.payload.get('metadata')),
                    "metadata": hit.payload.get('metadata'),
                    "score": hit.score
                } for hit in hits]
            except Exception:
                logger.warning("Busca Qdrant falhou; usando apenas cache.", exc_info=True)
                self._offline = True
        # 4) Combinar e deduplicar por ID
        combined: Dict[str, Dict[str, Any]] = {}
        for r in cache_results + qdrant_results:
            rid = str(r.get("id"))
            prev = combined.get(rid)
            if prev is None or float(r.get("score", 0.0)) > float(prev.get("score", 0.0)):
                combined[rid] = r

        results = sorted(combined.values(), key=lambda x: float(x.get("score", 0.0)), reverse=True)
        # 5) Filtro por min_score
        if min_score is not None:
            results = [r for r in results if float(r.get("score", 0.0)) >= float(min_score)]
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

    async def arecall_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Busca com filtros por payload (ex.: type, metadata.status, metadata.origin).
        """
        query_vector = [0.0] * self._vector_size
        if query:
            try:
                query_vector = embed_text(query)
            except Exception:
                logger.warning("Falha ao gerar embedding da consulta filtrada; usando vetor nulo.")
        eff_limit = limit or 10
        qfilter = self._build_filter(filters)
        if self._offline:
            # Offline: retorna vazio para buscas filtradas complexas
            return []
        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=eff_limit,
                with_payload=True,
                query_filter=qfilter,
            )
        except Exception:
            logger.warning("Busca filtrada no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [{
            "id": hit.id,
            "content": decrypt_text(hit.payload.get('content'), hit.payload.get('metadata')),
            "metadata": hit.payload.get('metadata'),
            "score": hit.score
        } for hit in hits]
        if min_score is not None:
            results = [r for r in results if float(r.get("score", 0.0)) >= float(min_score)]
        return results

    async def arecall_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Busca por janela temporal usando o campo auxiliar ts_ms.
        Se o período não puder ser aplicado no filtro, faz pós-filtragem em memória.
        """
        query_vector = [0.0] * self._vector_size
        if query:
            try:
                query_vector = embed_text(query)
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
            return []
        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=eff_limit,
                with_payload=True,
                query_filter=qfilter,
            )
        except Exception:
            logger.warning("Busca por janela no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [{
            "id": h.id,
            "content": decrypt_text(h.payload.get('content'), h.payload.get('metadata')),
            "metadata": h.payload.get('metadata'),
            "score": h.score,
            "ts_ms": h.payload.get('ts_ms'),
        } for h in hits]
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
            {"id": r["id"], "content": r["content"], "metadata": r["metadata"], "score": r["score"]}
            for r in results if within(r.get("ts_ms"))
        ]
        if min_score is not None:
            results = [r for r in results if float(r.get("score", 0.0)) >= float(min_score)]
        return results

    async def arecall_recent_failures(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Busca falhas recentes usando metadata.status == 'failure' dentro de uma janela.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        window = timeframe_seconds if timeframe_seconds is not None else int(getattr(settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        start_ms = now_ms - (window * 1000)

        qfilter = models.Filter(must=[
            models.FieldCondition(key="metadata.status", match=models.MatchValue(value="failure")),
            models.FieldCondition(key="ts_ms", range=models.Range(gte=start_ms, lte=now_ms)),
        ])
        if self._offline:
            return []
        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * self._vector_size,
                limit=limit or 10,
                with_payload=True,
                query_filter=qfilter,
            )
        except Exception:
            logger.warning("Busca de falhas recentes no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [{
            "id": h.id,
            "content": decrypt_text(h.payload.get('content'), h.payload.get('metadata')),
            "metadata": h.payload.get('metadata'),
            "score": h.score,
        } for h in hits]
        if min_score is not None:
            results = [r for r in results if float(r.get("score", 0.0)) >= float(min_score)]
        return results

    async def arecall_recent_lessons(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Busca lições recentes usando type == 'lessons_learned' dentro de uma janela.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        window = timeframe_seconds if timeframe_seconds is not None else int(getattr(settings, "MEMORY_QUOTA_WINDOW_SECONDS", 3600))
        start_ms = now_ms - (window * 1000)

        qfilter = models.Filter(must=[
            models.FieldCondition(key="type", match=models.MatchValue(value="lessons_learned")),
            models.FieldCondition(key="ts_ms", range=models.Range(gte=start_ms, lte=now_ms)),
        ])
        if self._offline:
            return []
        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=[0.0] * self._vector_size,
                limit=limit or 10,
                with_payload=True,
                query_filter=qfilter,
            )
        except Exception:
            logger.warning("Busca de lições recentes no Qdrant falhou; retornando vazio.", exc_info=True)
            self._offline = True
            return []
        results = [{
            "id": h.id,
            "content": decrypt_text(h.payload.get('content'), h.payload.get('metadata')),
            "metadata": h.payload.get('metadata'),
            "score": h.score,
        } for h in hits]
        if min_score is not None:
            results = [r for r in results if float(r.get("score", 0.0)) >= float(min_score)]
        return results


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_memory_db_instance: Optional[MemoryCore] = None


async def initialize_memory_db():
    global _memory_db_instance
    if _memory_db_instance is None:
        _memory_db_instance = MemoryCore()
        await _memory_db_instance.initialize()


async def close_memory_db():
    pass


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
