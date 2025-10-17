import logging
import time
from collections import OrderedDict
from typing import List, Optional, Tuple

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

try:
    from langchain_openai import OpenAIEmbeddings  # type: ignore
except Exception:
    OpenAIEmbeddings = None  # type: ignore

# === Config Defaults ===
_DEFAULT_LOCAL_MODEL = getattr(settings, "EMBEDDINGS_LOCAL_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
_DEFAULT_OPENAI_MODEL = getattr(settings, "EMBEDDINGS_OPENAI_MODEL_NAME", "text-embedding-3-small")
_TARGET_VECTOR_SIZE = int(getattr(settings, "MEMORY_VECTOR_SIZE", 1536))
_PROVIDER_PREF = getattr(settings, "EMBEDDINGS_DEFAULT_PROVIDER", "local")  # "local" | "openai"
_CACHE_TTL = int(getattr(settings, "MEMORY_SHORT_TTL_SECONDS", 600))
_CACHE_MAX = int(getattr(settings, "MEMORY_SHORT_MAX_ITEMS", 512))


class _TTLCache:
    def __init__(self, max_items: int, ttl_seconds: int):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, Tuple[float, List[float]]] = OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
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

    def put(self, key: str, vec: List[float]) -> None:
        self._store[key] = (time.time(), vec)
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)


# Simple per-text cache to avoid re-embedding repeated inputs
_cache = _TTLCache(max_items=_CACHE_MAX, ttl_seconds=_CACHE_TTL)

_local_model: Optional[SentenceTransformer] = None
_openai_embedder: Optional[OpenAIEmbeddings] = None


def _load_local_model() -> SentenceTransformer:
    global _local_model
    if _local_model is not None:
        return _local_model
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers não está instalado")
    model_name = _DEFAULT_LOCAL_MODEL
    logger.info(f"Carregando modelo local de embeddings: {model_name}")
    _local_model = SentenceTransformer(model_name)
    return _local_model


def _load_openai_embedder() -> OpenAIEmbeddings:
    global _openai_embedder
    if _openai_embedder is not None:
        return _openai_embedder
    if OpenAIEmbeddings is None:
        raise RuntimeError("langchain_openai não está disponível para embeddings")
    # Se não houver API key, falhar cedo
    try:
        openai_key = settings.OPENAI_API_KEY.get_secret_value() if getattr(settings, "OPENAI_API_KEY", None) else None
    except Exception:
        openai_key = None
    if not openai_key:
        raise RuntimeError("OPENAI_API_KEY não configurada para embeddings OpenAI")
    model_name = _DEFAULT_OPENAI_MODEL
    logger.info(f"Inicializando OpenAIEmbeddings com modelo: {model_name}")
    _openai_embedder = OpenAIEmbeddings(model=model_name, api_key=openai_key)
    return _openai_embedder


def _pad_or_truncate(vec: List[float], size: int) -> List[float]:
    if len(vec) == size:
        return vec
    if len(vec) > size:
        return vec[:size]
    # pad com zeros
    return vec + [0.0] * (size - len(vec))


def _normalize_vectors(vectors: List[List[float]], size: int) -> List[List[float]]:
    return [_pad_or_truncate(list(map(float, v)), size) for v in vectors]


def _emb_local(texts: List[str]) -> List[List[float]]:
    model = _load_local_model()
    arr = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    if isinstance(arr, np.ndarray):
        vectors = arr.tolist()
    else:
        vectors = [list(map(float, x)) for x in arr]
    return _normalize_vectors(vectors, _TARGET_VECTOR_SIZE)


def _emb_openai(texts: List[str]) -> List[List[float]]:
    embedder = _load_openai_embedder()
    vectors = embedder.embed_documents(texts)
    return _normalize_vectors(vectors, _TARGET_VECTOR_SIZE)


def embed_text(text: str) -> List[float]:
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
            if p == "local":
                vec = _emb_local([text])[0]
            elif p == "openai":
                vec = _emb_openai([text])[0]
            else:
                continue
            _cache.put(key, vec)
            return vec
        except Exception as e:
            logger.warning(f"Embedding provider '{p}' falhou; tentando fallback. Erro: {e}")
            continue

    logger.error("Todos provedores de embeddings falharam; usando vetor nulo.")
    null_vec = [0.0] * _TARGET_VECTOR_SIZE
    _cache.put(key, null_vec)
    return null_vec


def embed_texts(texts: List[str]) -> List[List[float]]:
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
            if p == "local":
                return _emb_local(texts)
            elif p == "openai":
                return _emb_openai(texts)
        except Exception as e:
            logger.warning(f"Embedding provider batch '{p}' falhou; tentando fallback. Erro: {e}")
            continue

    logger.error("Batch embeddings: todos provedores falharam; retornando vetores nulos.")
    return [[0.0] * _TARGET_VECTOR_SIZE for _ in texts]