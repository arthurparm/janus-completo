
import json
import logging

from langchain_openai import OpenAIEmbeddings  # Exemplo de modelo de embedding
from qdrant_client import QdrantClient, models

from app.db.vector_store import get_qdrant_client, get_or_create_collection
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

COLLECTION_NAME = "janus_episodic_memory"

# Inicializa a coleção no início para garantir que ela exista
try:
    get_or_create_collection(COLLECTION_NAME)
except ConnectionError as e:
    logger.error(f"Não foi possível inicializar a coleção do Qdrant: {e}")


def _sanitize_metadata(metadata: dict) -> dict:
    # Esta função continua útil para garantir que os metadados são compatíveis com JSON
    # e podem ser armazenados como payload no Qdrant.
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (dict, list)):
            # Qdrant pode lidar com objetos aninhados, mas serializar para JSON é mais seguro
            # para evitar problemas de compatibilidade de tipos.
            try:
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            except (TypeError, OverflowError):
                sanitized[key] = str(value)  # Fallback
        elif isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized

from collections import OrderedDict
import re
import base64
import time
from typing import Optional, List, Dict, Any, Tuple

from prometheus_client import Counter, Histogram

from app.config import settings


# Métricas
_MEM_HITS = Counter("memory_layer_hits_total", "Hits por camada de memória", ["layer"])  # short/long
_MEM_MISSES = Counter("memory_layer_misses_total", "Misses por camada de memória", ["layer"])  # short/long
_MEM_BYTES = Counter("memory_bytes_total", "Bytes processados pela memória", ["direction", "layer"])  # in/out, short/long
_MEM_OPS = Counter("memory_ops_total", "Operações de memória", ["op", "layer", "outcome"])  # memorize/recall
_MEM_LAT = Histogram("memory_latency_seconds", "Latência por operação de memória", ["op", "layer", "outcome"])  # memorize/recall


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
    return (len(types) > 0, types)


def _mask_pii(text: str) -> str:
    text = re.sub(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}", "***@***.***", text)
    text = re.sub(r"\b\+?\d[\d\s().-]{7,}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CC]", text)
    return text


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return bytes(out)


def encrypt_text(text: str) -> str:
    key = (settings.MEMORY_ENCRYPTION_KEY or "").encode("utf-8")
    if not key:
        return text
    raw = text.encode("utf-8")
    enc = _xor_bytes(raw, key)
    return "enc::" + base64.b64encode(enc).decode("ascii")


def decrypt_text(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    if not text.startswith("enc::"):
        return text
    key = (settings.MEMORY_ENCRYPTION_KEY or "").encode("utf-8")
    try:
        enc = base64.b64decode(text[len("enc::"):])
        dec = _xor_bytes(enc, key)
        return dec.decode("utf-8", errors="replace")
    except Exception:
        return text  # fallback


class ShortTermMemory:
    """Memória de curto prazo com TTL, LRU e embeddings em memória."""

    def __init__(self, ttl_seconds: int, max_items: int, encoder: Optional[OpenAIEmbeddings]):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.encoder = encoder
        # key: id, value: (ts, vector, content, metadata)
        self._store: "OrderedDict[str, Tuple[float, Optional[List[float]], str, dict]]" = OrderedDict()

    def _prune(self):
        now = _now()
        # remove expirados
        for k in list(self._store.keys()):
            ts, _, _, _ = self._store[k]
            if now - ts > self.ttl_seconds:
                self._store.pop(k, None)
        # aplica LRU se necessário
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def add(self, exp_id: str, content: str, metadata: dict):
        ts = _now()
        vec: Optional[List[float]] = None
        try:
            if self.encoder:
                vec = self.encoder.embed_query(content)
        except Exception:
            vec = None
        self._store[exp_id] = (ts, vec, content, metadata)
        self._store.move_to_end(exp_id)
        self._prune()

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        import math
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return (dot / (na * nb)) if na and nb else 0.0

    def search(self, query: str, n_results: int) -> List[dict]:
        self._prune()
        if not self._store:
            _MEM_MISSES.labels("short").inc()
            return []
        try:
            qv = self.encoder.embed_query(query) if self.encoder else None
        except Exception:
            qv = None
        scored: List[Tuple[str, float, str, dict]] = []
        for exp_id, (ts, vec, content, metadata) in self._store.items():
            score = 0.0
            if qv is not None and vec is not None:
                score = self._cosine(qv, vec)
            else:
                # fallback: substring heuristic
                score = 1.0 if query.lower() in content.lower() else 0.0
            scored.append((exp_id, score, content, metadata))
        # ordenar por score desc
        scored.sort(key=lambda x: x[1], reverse=True)
        top = []
        for exp_id, score, content, metadata in scored[:n_results]:
            top.append({
                "id": exp_id,
                "content": content,
                "metadata": metadata,
                "distance": 1 - min(max(score, 0.0), 1.0)
            })
        if top:
            _MEM_HITS.labels("short").inc()
        else:
            _MEM_MISSES.labels("short").inc()
        return top


class EpisodicMemory:
    def __init__(self):
        try:
            self.client: QdrantClient = get_qdrant_client()
            # Exemplo de como inicializar um modelo de embedding. Em um projeto real,
            # isso viria de um gerenciador centralizado.
            self.encoder = OpenAIEmbeddings()
            # Determina a dimensão do embedding para garantir que a coleção está alinhada
            try:
                probe_vec = self.encoder.embed_query("dimension_probe")
                vector_dim = len(probe_vec)
                get_or_create_collection(COLLECTION_NAME, vector_size=vector_dim)
                logger.info(f"Coleção '{COLLECTION_NAME}' verificada/criada com dimensão {vector_dim}.")
            except Exception as e:
                logger.warning(f"Não foi possível verificar a dimensão do embedding/coleção: {e}")
            logger.info(f"Memória episódica conectada ao Qdrant, coleção '{COLLECTION_NAME}'.")
        except Exception as e:
            self.client = None
            self.encoder = None
            logger.error(f"Falha ao inicializar a memória episódica com Qdrant: {e}", exc_info=True)
        # Short-term layer
        self.short = ShortTermMemory(
            ttl_seconds=settings.MEMORY_SHORT_TTL_SECONDS,
            max_items=settings.MEMORY_SHORT_MAX_ITEMS,
            encoder=self.encoder,
        )
        if self.encoder is None:
            logger.warning("OpenAIEmbeddings indisponível; caindo para heurística de substring (encoder=None).")
        # Quotas por origem
        self._quota_window_start = _now()
        self._per_origin_counts: Dict[str, int] = {}
        self._per_origin_bytes: Dict[str, int] = {}

    def _reset_window_if_needed(self):
        if _now() - self._quota_window_start > settings.MEMORY_QUOTA_WINDOW_SECONDS:
            self._quota_window_start = _now()
            self._per_origin_counts.clear()
            self._per_origin_bytes.clear()

    def _check_quota(self, origin: str, content: str) -> bool:
        self._reset_window_if_needed()
        count = self._per_origin_counts.get(origin, 0)
        bytes_ = self._per_origin_bytes.get(origin, 0)
        if count >= settings.MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN:
            logger.warning({"event": "memory_quota_items_exceeded", "origin": origin})
            return False
        if bytes_ + _approx_bytes(content) > settings.MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN:
            logger.warning({"event": "memory_quota_bytes_exceeded", "origin": origin})
            return False
        return True

    def _consume_quota(self, origin: str, content: str) -> None:
        self._per_origin_counts[origin] = self._per_origin_counts.get(origin, 0) + 1
        self._per_origin_bytes[origin] = self._per_origin_bytes.get(origin, 0) + _approx_bytes(content)

    def memorize(self, experience: Experience):
        """Salva uma experiência nas camadas short- e long-term com validações/quotas/PII."""
        start = time.perf_counter()
        try:
            if not isinstance(experience.content, str) or not experience.content.strip():
                raise ValueError("content não pode ser vazio")
            if len(experience.content) > settings.MEMORY_MAX_CONTENT_CHARS:
                # Trunca para evitar explosões
                experience.content = experience.content[: settings.MEMORY_MAX_CONTENT_CHARS]

            origin = str(experience.metadata.get("origin") or experience.metadata.get("source") or "unknown").lower()
            if not self._check_quota(origin, experience.content):
                _MEM_OPS.labels("memorize", "short", "denied").inc()
                return

            # PII handling
            pii, types = _detect_pii(experience.content)
            if pii:
                experience.metadata["pii"] = True
                experience.metadata["pii_types"] = types
                if settings.MEMORY_PII_REDACT:
                    experience.content = _mask_pii(experience.content)

            # Short-term sempre
            self.short.add(experience.id, experience.content, experience.metadata)
            _MEM_OPS.labels("memorize", "short", "success").inc()
            _MEM_BYTES.labels("in", "short").inc(_approx_bytes(experience.content))

            # Long-term somente se cliente/encoder disponíveis
            if self.client and self.encoder:
                try:
                    vector = self.encoder.embed_query(experience.content)
                    payload = experience.metadata.copy()
                    payload['type'] = experience.type
                    payload['timestamp'] = experience.timestamp
                    # criptografia opcional
                    stored_content = encrypt_text(experience.content)
                    payload['content'] = stored_content
                    safe_payload = _sanitize_metadata(payload)

                    self.client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[
                            models.PointStruct(
                                id=experience.id,
                                vector=vector,
                                payload=safe_payload
                            )
                        ],
                        wait=True
                    )
                    _MEM_OPS.labels("memorize", "long", "success").inc()
                    _MEM_BYTES.labels("in", "long").inc(_approx_bytes(experience.content))
                except Exception as e:
                    logger.error(f"Erro ao escrever no Qdrant: {e}", exc_info=True)
                    _MEM_OPS.labels("memorize", "long", "error").inc()
            else:
                _MEM_OPS.labels("memorize", "long", "skipped").inc()

            # Consome quota após persistência
            self._consume_quota(origin, experience.content)

            _MEM_LAT.labels("memorize", "combined", "success").observe(time.perf_counter() - start)
            logger.info(f"Experiência memorizada (short{' + long' if self.client and self.encoder else ''}). ID={experience.id}")
        except Exception as e:
            _MEM_LAT.labels("memorize", "combined", "error").observe(time.perf_counter() - start)
            _MEM_OPS.labels("memorize", "combined", "error").inc()
            logger.error(f"Erro ao memorizar a experiência {getattr(experience, 'id', '-')}: {e}", exc_info=True)

    def recall(self, query: str, n_results: int = 5) -> list[dict]:
        """Busca primeiro na memória de curto prazo e depois no Qdrant, com merge de resultados."""
        t0 = time.perf_counter()
        combined: List[dict] = []
        seen: set[str] = set()
        # Short-term
        try:
            st0 = time.perf_counter()
            short_res = self.short.search(query, n_results)
            combined.extend(short_res)
            seen.update([r["id"] for r in short_res])
            _MEM_LAT.labels("recall", "short", "success").observe(time.perf_counter() - st0)
        except Exception as e:
            _MEM_LAT.labels("recall", "short", "error").observe(time.perf_counter() - st0)
            logger.error(f"Erro na busca short-term: {e}")

        # Long-term
        try:
            lt0 = time.perf_counter()
            if self.client and self.encoder and len(combined) < n_results:
                query_vector = self.encoder.embed_query(query)
                limit = n_results * 2  # busca mais para margem de dedupe
                search_results = self.client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=query_vector,
                    limit=limit,
                    with_payload=True
                )
                long_items: List[dict] = []
                for sp in search_results:
                    cid = sp.id
                    if str(cid) in seen:
                        continue
                    raw_content = sp.payload.get('content', '')
                    content = decrypt_text(raw_content)
                    item = {
                        "id": str(cid),
                        "content": content,
                        "metadata": {k: v for k, v in sp.payload.items() if k != 'content'},
                        "distance": 1 - sp.score
                    }
                    long_items.append(item)
                    if len(combined) + len(long_items) >= n_results:
                        break
                if long_items:
                    _MEM_HITS.labels("long").inc()
                else:
                    _MEM_MISSES.labels("long").inc()
                combined.extend(long_items)
                _MEM_LAT.labels("recall", "long", "success").observe(time.perf_counter() - lt0)
            else:
                _MEM_MISSES.labels("long").inc()
        except Exception as e:
            _MEM_LAT.labels("recall", "long", "error").observe(time.perf_counter() - lt0)
            logger.error(f"Erro na busca long-term (Qdrant): {e}", exc_info=True)

        _MEM_BYTES.labels("out", "combined").inc(sum(_approx_bytes(i.get("content", "")) for i in combined))
        _MEM_OPS.labels("recall", "combined", "success").inc()
        _MEM_LAT.labels("recall", "combined", "success").observe(time.perf_counter() - t0)
        logger.info(f"Recordadas {len(combined)} experiências (short+long) para a consulta: '{query}'")
        return combined


# Instância única para ser usada na aplicação
memory_core = EpisodicMemory()
