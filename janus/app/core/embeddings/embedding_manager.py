import hashlib
import logging
import time
from collections import OrderedDict

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore

    _EMB_REQ = Counter("emb_requests_total", "Requisições de embedding", ["provider", "outcome"])  # type: ignore
    _EMB_LAT = Histogram("emb_latency_seconds", "Latência de embeddings", ["provider", "outcome"])  # type: ignore
    _EMB_MODEL_LOADED = Gauge("emb_model_loaded", "Modelo de embeddings carregado", ["provider"])  # type: ignore
except Exception:

    class _NoopC:
        def labels(self, *a, **k):
            return self

        def inc(self, *a, **k):
            pass

    class _NoopH:
        def labels(self, *a, **k):
            return self

        def observe(self, *a, **k):
            pass

    class _NoopG:
        def labels(self, *a, **k):
            return self

        def set(self, *a, **k):
            pass

    _EMB_REQ = _NoopC()  # type: ignore
    _EMB_LAT = _NoopH()  # type: ignore
    _EMB_MODEL_LOADED = _NoopG()  # type: ignore

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

try:
    from langchain_openai import OpenAIEmbeddings  # type: ignore
except Exception:
    OpenAIEmbeddings = None  # type: ignore

# === Config Defaults ===
_DEFAULT_LOCAL_MODEL = getattr(
    settings,
    "EMBEDDINGS_LOCAL_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
_DEFAULT_OPENAI_MODEL = getattr(settings, "EMBEDDINGS_OPENAI_MODEL_NAME", "text-embedding-3-small")
_TARGET_VECTOR_SIZE = int(getattr(settings, "MEMORY_VECTOR_SIZE", 1536))
_PROVIDER_PREF = getattr(settings, "EMBEDDINGS_DEFAULT_PROVIDER", "local")  # "local" | "openai"
_CACHE_TTL = int(getattr(settings, "MEMORY_SHORT_TTL_SECONDS", 600))
_CACHE_MAX = int(getattr(settings, "MEMORY_SHORT_MAX_ITEMS", 512))


class _TTLCache:
    def __init__(self, max_items: int, ttl_seconds: int):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()

    def get(self, key: str) -> list[float] | None:
        now = time.time()
        val = self._store.get(key)
        if not val:
            return None
        ts, vec = val
        if now - ts > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return vec

    def put(self, key: str, vec: list[float]) -> None:
        self._store[key] = (time.time(), vec)
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)


# Simple per-text cache to avoid re-embedding repeated inputs
_cache = _TTLCache(max_items=_CACHE_MAX, ttl_seconds=_CACHE_TTL)

_local_model: SentenceTransformer | None = None
_local_model_failed: bool = False
_openai_embedder: OpenAIEmbeddings | None = None


def _load_local_model() -> SentenceTransformer:
    global _local_model, _local_model_failed
    if _local_model is not None:
        return _local_model
    if _local_model_failed:
        raise RuntimeError("Modelo local de embeddings está indisponível neste ambiente")
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers não está instalado")
    model_name = _DEFAULT_LOCAL_MODEL
    logger.info(f"Carregando modelo local de embeddings: {model_name}")
    try:
        _local_model = SentenceTransformer(model_name)
        try:
            _EMB_MODEL_LOADED.labels("local").set(1)
        except Exception:
            pass
        return _local_model
    except NotImplementedError:
        _local_model_failed = True
        logger.warning(
            "Falha ao inicializar modelo local de embeddings (meta tensor); "
            "desativando modelo local e usando fallback.",
        )
        raise
    except Exception as e:
        _local_model_failed = True
        logger.error("Erro ao carregar modelo local de embeddings.", exc_info=e)
        raise


def _load_openai_embedder() -> OpenAIEmbeddings:
    global _openai_embedder
    if _openai_embedder is not None:
        return _openai_embedder
    if OpenAIEmbeddings is None:
        raise RuntimeError("langchain_openai não está disponível para embeddings")
    # Se não houver API key, falhar cedo
    try:
        openai_key = (
            settings.OPENAI_API_KEY.get_secret_value()
            if getattr(settings, "OPENAI_API_KEY", None)
            else None
        )
    except Exception:
        openai_key = None
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY não configurada para embeddings OpenAI")
    model_name = _DEFAULT_OPENAI_MODEL
    logger.info(f"Inicializando OpenAIEmbeddings com modelo: {model_name}")
    _openai_embedder = OpenAIEmbeddings(model=model_name, api_key=openai_key)
    try:
        _EMB_MODEL_LOADED.labels("openai").set(1)
    except Exception:
        pass
    return _openai_embedder


def _pad_or_truncate(vec: list[float], size: int) -> list[float]:
    if len(vec) == size:
        return vec
    if len(vec) > size:
        return vec[:size]
    # pad com zeros
    return vec + [0.0] * (size - len(vec))


def _normalize_vectors(vectors: list[list[float]], size: int) -> list[list[float]]:
    return [_pad_or_truncate(list(map(float, v)), size) for v in vectors]


def _simple_local_embedding_single(text: str, size: int) -> list[float]:
    tokens = text.lower().split()
    vec = np.zeros(size, dtype=np.float32)
    for tok in tokens:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "little") % size
        sign = 1.0 if (h[4] & 1) else -1.0
        vec[idx] += sign
    norm = float(np.linalg.norm(vec)) or 1.0
    return (vec / norm).tolist()


def _simple_local_embedding(texts: list[str]) -> list[list[float]]:
    return [_simple_local_embedding_single(t, _TARGET_VECTOR_SIZE) for t in texts]


def _emb_local(texts: list[str]) -> list[list[float]]:
    try:
        model = _load_local_model()
        arr = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        if isinstance(arr, np.ndarray):
            vectors = arr.tolist()
        else:
            vectors = [list(map(float, x)) for x in arr]
        return _normalize_vectors(vectors, _TARGET_VECTOR_SIZE)
    except Exception as e:
        msg = str(e) if e else ""
        if isinstance(e, NotImplementedError) or "meta tensor" in msg:
            logger.warning(
                "Embedding local com sentence-transformers indisponível neste ambiente "
                "(meta tensor); usando fallback local baseado em hash.",
            )
        else:
            logger.error(
                "Embedding local com sentence-transformers falhou; usando fallback local baseado em hash.",
                exc_info=e,
            )
        return _simple_local_embedding(texts)


def _emb_openai(texts: list[str]) -> list[list[float]]:
    embedder = _load_openai_embedder()
    vectors = embedder.embed_documents(texts)
    return _normalize_vectors(vectors, _TARGET_VECTOR_SIZE)


def embed_text(text: str) -> list[float]:
    """
    Retorna embedding para um único texto, com fallback automático.

    - Tenta provedor preferido (local por padrão)
    - Se falhar, tenta o outro (OpenAI ou local)
    - Em caso de falha total, retorna vetor zero com tamanho alvo
    """
    key = f"emb:{_TARGET_VECTOR_SIZE}:{_DEFAULT_LOCAL_MODEL}:{_DEFAULT_OPENAI_MODEL}:{text.strip()[:4000]}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    providers = [(_PROVIDER_PREF or "local").lower()]
    # garante ordem de fallback
    if providers[0] == "local":
        providers.append("openai")
    else:
        providers.append("local")

    for p in providers:
        try:
            import time as _t

            _t0 = _t.perf_counter()
            if p == "local":
                vec = _emb_local([text])[0]
            elif p == "openai":
                vec = _emb_openai([text])[0]
            else:
                continue
            _cache.put(key, vec)
            try:
                _EMB_REQ.labels(p, "success").inc()
                _EMB_LAT.labels(p, "success").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return vec
        except Exception as e:
            logger.warning(f"Embedding provider '{p}' falhou; tentando fallback. Erro: {e}")
            try:
                _EMB_REQ.labels(p, "error").inc()
                _EMB_LAT.labels(p, "error").observe(0.0)
            except Exception:
                pass
            continue

    logger.error("Todos provedores de embeddings falharam; usando vetor nulo.")
    null_vec = [0.0] * _TARGET_VECTOR_SIZE
    _cache.put(key, null_vec)
    try:
        _EMB_REQ.labels("none", "error").inc()
        _EMB_LAT.labels("none", "error").observe(0.0)
    except Exception:
        pass
    return null_vec


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Versão em lote com fallback; usa o mesmo provedor escolhido que o embed_text."""
    if not texts:
        return []
    # Estratégia simples: tentar provider preferido, com fallback; sem cache por-item para lote
    providers = [(_PROVIDER_PREF or "local").lower()]
    if providers[0] == "local":
        providers.append("openai")
    else:
        providers.append("local")

    for p in providers:
        try:
            import time as _t

            _t0 = _t.perf_counter()
            if p == "local":
                res = _emb_local(texts)
            elif p == "openai":
                res = _emb_openai(texts)
            else:
                continue
            try:
                _EMB_REQ.labels(p, "success").inc()
                _EMB_LAT.labels(p, "success").observe(max(0.0, _t.perf_counter() - _t0))
            except Exception:
                pass
            return res
        except Exception as e:
            logger.warning(f"Embedding provider batch '{p}' falhou; tentando fallback. Erro: {e}")
            try:
                _EMB_REQ.labels(p, "error").inc()
                _EMB_LAT.labels(p, "error").observe(0.0)
            except Exception:
                pass
            continue

    logger.error("Batch embeddings: todos provedores falharam; retornando vetores nulos.")
    try:
        _EMB_REQ.labels("none", "error").inc()
        _EMB_LAT.labels("none", "error").observe(0.0)
    except Exception:
        pass
    return [[0.0] * _TARGET_VECTOR_SIZE for _ in texts]


async def aembed_text(text: str) -> list[float]:
    """Wrapper assíncrono para embed_text."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, embed_text, text)


async def aembed_texts(texts: list[str]) -> list[list[float]]:
    """Wrapper assíncrono para embed_texts."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(None, embed_texts, texts)
