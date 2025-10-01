
import base64
import json
import logging
import math
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional, Tuple

from langchain_openai import OpenAIEmbeddings
from prometheus_client import Counter, Histogram
from qdrant_client import QdrantClient, models

from app.config import settings
from app.db.vector_store import get_qdrant_client, get_or_create_collection
from app.models.schemas import Experience

logger = logging.getLogger(__name__)

COLLECTION_NAME = "janus_episodic_memory"

# Constantes de timeout
_EMBEDDING_TIMEOUT = 30  # segundos
_QDRANT_WRITE_TIMEOUT = 10  # segundos
_QDRANT_SEARCH_TIMEOUT = 10  # segundos

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
    """
    Detecta PII (Personally Identifiable Information) em texto.

    Args:
        text: Texto a ser analisado

    Returns:
        Tupla (tem_pii, tipos_detectados)
    """
    types: List[str] = []

    # Email
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        types.append("email")

    # Telefone (vários formatos internacionais)
    if re.search(r"\b\+?\d[\d\s().-]{7,}\b", text):
        types.append("phone")

    # Cartão de crédito
    if re.search(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", text):
        types.append("cc")

    # CPF brasileiro (formato XXX.XXX.XXX-XX)
    if re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", text):
        types.append("cpf")

    # SSN americano
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        types.append("ssn")

    return (len(types) > 0, types)


def _mask_pii(text: str) -> str:
    """
    Mascara PII detectado no texto.

    Args:
        text: Texto original

    Returns:
        Texto com PII mascarado
    """
    text = re.sub(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}", "***@***.***", text)
    text = re.sub(r"\b\+?\d[\d\s().-]{7,}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_CC]", text)
    text = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[REDACTED_CPF]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    return text


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """
    Criptografia XOR simples.

    Args:
        data: Dados a serem criptografados/descriptografados
        key: Chave de criptografia

    Returns:
        Dados processados
    """
    if not key:
        return data
    out = bytearray()
    for i, b in enumerate(data):
        out.append(b ^ key[i % len(key)])
    return bytes(out)


def encrypt_text(text: str) -> str:
    """
    Criptografa texto usando chave de configuração.

    Args:
        text: Texto a ser criptografado

    Returns:
        Texto criptografado com prefixo "enc::"
    """
    key = (settings.MEMORY_ENCRYPTION_KEY or "").encode("utf-8")
    if not key:
        return text
    raw = text.encode("utf-8")
    enc = _xor_bytes(raw, key)
    return "enc::" + base64.b64encode(enc).decode("ascii")


def decrypt_text(text: str) -> str:
    """
    Descriptografa texto previamente criptografado.

    Args:
        text: Texto criptografado

    Returns:
        Texto original ou texto de entrada se não for criptografado
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
        return text  # fallback


def _sanitize_metadata(metadata: dict) -> dict:
    """
    Sanitiza metadados para compatibilidade com Qdrant.

    Args:
        metadata: Metadados originais

    Returns:
        Metadados sanitizados
    """
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
    """Memória de curto prazo com TTL, LRU e embeddings em memória."""

    def __init__(self, ttl_seconds: int, max_items: int, encoder: Optional[OpenAIEmbeddings]):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.encoder = encoder
        # key: id, value: (ts, vector, content, metadata)
        self._store: "OrderedDict[str, Tuple[float, Optional[List[float]], str, dict]]" = OrderedDict()
        self._lock = threading.RLock()

    def _prune(self):
        """Remove itens expirados e aplica LRU."""
        with self._lock:
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
        """
        Adiciona experiência à memória de curto prazo.

        Args:
            exp_id: ID da experiência
            content: Conteúdo textual
            metadata: Metadados associados
        """
        ts = _now()
        vec: Optional[List[float]] = None

        try:
            if self.encoder:
                # Gera embedding com timeout
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stm_embed")
                try:
                    future = executor.submit(self.encoder.embed_query, content)
                    vec = future.result(timeout=_EMBEDDING_TIMEOUT)
                except FuturesTimeoutError:
                    logger.warning(
                        f"Timeout ao gerar embedding para STM (id={exp_id}). "
                        f"Prosseguindo sem vetor."
                    )
                    vec = None
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.warning(f"Erro ao gerar embedding para STM: {e}")
            vec = None

        with self._lock:
            self._store[exp_id] = (ts, vec, content, metadata)
            self._store.move_to_end(exp_id)
            self._prune()

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        """Calcula similaridade de cosseno entre dois vetores."""
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return (dot / (na * nb)) if na and nb else 0.0

    def search(self, query: str, n_results: int) -> List[dict]:
        """
        Busca experiências na memória de curto prazo.

        Args:
            query: Query de busca
            n_results: Número máximo de resultados

        Returns:
            Lista de resultados ordenados por relevância
        """
        self._prune()

        with self._lock:
            if not self._store:
                _MEM_MISSES.labels("short").inc()
                return []

        # Gera embedding da query com timeout
        qv: Optional[List[float]] = None
        try:
            if self.encoder:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stm_query")
                try:
                    future = executor.submit(self.encoder.embed_query, query)
                    qv = future.result(timeout=_EMBEDDING_TIMEOUT)
                except FuturesTimeoutError:
                    logger.warning("Timeout ao gerar embedding da query. Usando fallback textual.")
                    qv = None
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.warning(f"Erro ao gerar embedding da query: {e}")
            qv = None

        scored: List[Tuple[str, float, str, dict]] = []
        with self._lock:
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
    """Sistema de memória episódica com camadas short-term e long-term (Qdrant)."""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.encoder: Optional[OpenAIEmbeddings] = None

        # Tenta inicializar componentes
        try:
            self.client = get_qdrant_client()
            logger.info(f"Cliente Qdrant inicializado com sucesso.")
        except Exception as e:
            logger.warning(
                f"Falha ao inicializar cliente Qdrant: {e}. "
                f"Memória long-term ficará indisponível."
            )
            self.client = None

        try:
            self.encoder = OpenAIEmbeddings()

            # Verifica dimensão do embedding
            if self.client:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem_probe")
                try:
                    future = executor.submit(self.encoder.embed_query, "dimension_probe")
                    probe_vec = future.result(timeout=_EMBEDDING_TIMEOUT)
                    vector_dim = len(probe_vec)

                    get_or_create_collection(COLLECTION_NAME, vector_size=vector_dim)
                    logger.info(
                        f"Coleção '{COLLECTION_NAME}' verificada/criada com dimensão {vector_dim}."
                    )
                except FuturesTimeoutError:
                    logger.error("Timeout ao verificar dimensão do embedding.")
                except Exception as e:
                    logger.warning(f"Não foi possível verificar a dimensão do embedding: {e}")
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

        except Exception as e:
            logger.warning(
                f"Falha ao inicializar OpenAIEmbeddings: {e}. "
                f"Caindo para heurística de substring."
            )
            self.encoder = None

        # Short-term layer
        self.short = ShortTermMemory(
            ttl_seconds=settings.MEMORY_SHORT_TTL_SECONDS,
            max_items=settings.MEMORY_SHORT_MAX_ITEMS,
            encoder=self.encoder,
        )

        # Quotas por origem (thread-safe)
        self._quota_lock = threading.RLock()
        self._quota_window_start = _now()
        self._per_origin_counts: Dict[str, int] = {}
        self._per_origin_bytes: Dict[str, int] = {}

    def _reset_window_if_needed(self):
        """Reseta janela de quota se necessário."""
        with self._quota_lock:
            if _now() - self._quota_window_start > settings.MEMORY_QUOTA_WINDOW_SECONDS:
                self._quota_window_start = _now()
                self._per_origin_counts.clear()
                self._per_origin_bytes.clear()

    def _check_quota(self, origin: str, content: str) -> bool:
        """
        Verifica se a origem ainda tem quota disponível.

        Args:
            origin: Origem da experiência
            content: Conteúdo da experiência

        Returns:
            True se dentro da quota
        """
        self._reset_window_if_needed()

        with self._quota_lock:
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
        """
        Consome quota para a origem.

        Args:
            origin: Origem da experiência
            content: Conteúdo da experiência
        """
        with self._quota_lock:
            self._per_origin_counts[origin] = self._per_origin_counts.get(origin, 0) + 1
            self._per_origin_bytes[origin] = self._per_origin_bytes.get(origin, 0) + _approx_bytes(content)

    def memorize(self, experience: Experience):
        """
        Salva uma experiência nas camadas short- e long-term com validações/quotas/PII.

        Args:
            experience: Experiência a ser memorizada
        """
        start = time.perf_counter()

        try:
            # Validação de entrada
            if not isinstance(experience.content, str) or not experience.content.strip():
                raise ValueError("content não pode ser vazio")

            if len(experience.content) > settings.MEMORY_MAX_CONTENT_CHARS:
                logger.warning(
                    f"Conteúdo truncado de {len(experience.content)} para "
                    f"{settings.MEMORY_MAX_CONTENT_CHARS} caracteres."
                )
                experience.content = experience.content[:settings.MEMORY_MAX_CONTENT_CHARS]

            # Verifica quota
            origin = str(
                experience.metadata.get("origin") or
                experience.metadata.get("source") or
                "unknown"
            ).lower()

            if not self._check_quota(origin, experience.content):
                _MEM_OPS.labels("memorize", "short", "denied").inc()
                logger.warning(f"Quota excedida para origem '{origin}'. Experiência rejeitada.")
                return

            # PII handling
            pii, types = _detect_pii(experience.content)
            if pii:
                experience.metadata["pii"] = True
                experience.metadata["pii_types"] = types
                if settings.MEMORY_PII_REDACT:
                    experience.content = _mask_pii(experience.content)
                    logger.info(f"PII mascarado na experiência {experience.id}: {types}")

            # Short-term sempre
            self.short.add(experience.id, experience.content, experience.metadata)
            _MEM_OPS.labels("memorize", "short", "success").inc()
            _MEM_BYTES.labels("in", "short").inc(_approx_bytes(experience.content))

            # Long-term somente se cliente/encoder disponíveis
            if self.client and self.encoder:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem_write")
                try:
                    def write_to_qdrant():
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

                    future = executor.submit(write_to_qdrant)
                    future.result(timeout=_QDRANT_WRITE_TIMEOUT)

                    _MEM_OPS.labels("memorize", "long", "success").inc()
                    _MEM_BYTES.labels("in", "long").inc(_approx_bytes(experience.content))

                except FuturesTimeoutError:
                    logger.error(f"Timeout ao escrever no Qdrant (id={experience.id}).")
                    _MEM_OPS.labels("memorize", "long", "timeout").inc()
                except Exception as e:
                    logger.error(f"Erro ao escrever no Qdrant: {e}", exc_info=True)
                    _MEM_OPS.labels("memorize", "long", "error").inc()
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            else:
                _MEM_OPS.labels("memorize", "long", "skipped").inc()

            # Consome quota após persistência
            self._consume_quota(origin, experience.content)

            _MEM_LAT.labels("memorize", "combined", "success").observe(time.perf_counter() - start)
            logger.info(
                f"Experiência memorizada "
                f"(short{' + long' if self.client and self.encoder else ''}). "
                f"ID={experience.id}"
            )

        except ValueError as e:
            _MEM_LAT.labels("memorize", "combined", "error").observe(time.perf_counter() - start)
            _MEM_OPS.labels("memorize", "combined", "validation_error").inc()
            logger.error(f"Erro de validação ao memorizar: {e}")
        except Exception as e:
            _MEM_LAT.labels("memorize", "combined", "error").observe(time.perf_counter() - start)
            _MEM_OPS.labels("memorize", "combined", "error").inc()
            logger.error(
                f"Erro ao memorizar a experiência {getattr(experience, 'id', '-')}: {e}",
                exc_info=True
            )

    def recall(self, query: str, n_results: int = 5) -> List[dict]:
        """
        Busca primeiro na memória de curto prazo e depois no Qdrant, com merge de resultados.

        Args:
            query: Query de busca
            n_results: Número máximo de resultados

        Returns:
            Lista de experiências encontradas
        """
        t0 = time.perf_counter()
        combined: List[dict] = []
        seen: set[str] = set()

        # Short-term
        st0 = time.perf_counter()
        try:
            short_res = self.short.search(query, n_results)
            combined.extend(short_res)
            seen.update([r["id"] for r in short_res])
            _MEM_LAT.labels("recall", "short", "success").observe(time.perf_counter() - st0)
        except Exception as e:
            _MEM_LAT.labels("recall", "short", "error").observe(time.perf_counter() - st0)
            logger.error(f"Erro na busca short-term: {e}", exc_info=True)

        # Long-term
        lt0 = time.perf_counter()
        try:
            if self.client and self.encoder and len(combined) < n_results:
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mem_search")
                try:
                    def search_qdrant():
                        query_vector = self.encoder.embed_query(query)
                        limit = n_results * 2  # busca mais para margem de dedupe

                        search_results = self.client.search(
                            collection_name=COLLECTION_NAME,
                            query_vector=query_vector,
                            limit=limit,
                            with_payload=True
                        )
                        return search_results

                    future = executor.submit(search_qdrant)
                    search_results = future.result(timeout=_QDRANT_SEARCH_TIMEOUT)

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

                except FuturesTimeoutError:
                    logger.error(f"Timeout na busca long-term após {_QDRANT_SEARCH_TIMEOUT}s.")
                    _MEM_LAT.labels("recall", "long", "timeout").observe(time.perf_counter() - lt0)
                    _MEM_MISSES.labels("long").inc()
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            else:
                _MEM_MISSES.labels("long").inc()

        except Exception as e:
            _MEM_LAT.labels("recall", "long", "error").observe(time.perf_counter() - lt0)
            logger.error(f"Erro na busca long-term (Qdrant): {e}", exc_info=True)

        _MEM_BYTES.labels("out", "combined").inc(
            sum(_approx_bytes(i.get("content", "")) for i in combined)
        )
        _MEM_OPS.labels("recall", "combined", "success").inc()
        _MEM_LAT.labels("recall", "combined", "success").observe(time.perf_counter() - t0)

        logger.info(
            f"Recordadas {len(combined)} experiências (short+long) para a consulta: '{query[:100]}...'"
        )

        return combined


# Instância única para ser usada na aplicação
memory_core = EpisodicMemory()
