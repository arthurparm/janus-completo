import asyncio
import base64
import json
import logging
import math
import re
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from langchain_openai import OpenAIEmbeddings
from prometheus_client import Counter, Histogram
from qdrant_client import models, AsyncQdrantClient

from app.config import settings
from app.db.vector_store import get_async_qdrant_client, aget_or_create_collection
from app.models.schemas import Experience

logger = logging.getLogger(__name__)


# Helper functions
def _now() -> float:
    """Returns current time in seconds."""
    return time.time()


def _approx_bytes(text: str) -> int:
    """Approximates the byte size of a string."""
    return len(text.encode('utf-8'))


def _detect_pii(text: str) -> bool:
    """Simple PII detection (emails, phone numbers, SSNs)."""
    patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    ]
    return any(re.search(p, text) for p in patterns)

def _mask_pii(text: str) -> str:
    """Masks detected PII with [REDACTED]."""
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
    return text

def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """Simple XOR encryption/decryption."""
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))


def encrypt_text(text: str, key: str) -> str:
    """Encrypts text using XOR and returns base64."""
    key_bytes = key.encode('utf-8')
    data_bytes = text.encode('utf-8')
    encrypted = _xor_bytes(data_bytes, key_bytes)
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_text(encrypted_text: str, key: str) -> str:
    """Decrypts base64 XOR encrypted text."""
    key_bytes = key.encode('utf-8')
    data_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
    decrypted = _xor_bytes(data_bytes, key_bytes)
    return decrypted.decode('utf-8')

def _sanitize_metadata(metadata: dict) -> dict:
    """Removes None values and ensures all values are JSON-serializable."""
    return {k: v for k, v in metadata.items() if v is not None}

class ShortTermMemory:
    """In-memory LRU cache for recent experiences, supporting filtering."""
    def __init__(self, ttl_seconds: int, max_items: int, encoder: Optional[OpenAIEmbeddings]):
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.encoder = encoder
        self._store: "OrderedDict[str, Tuple[float, Optional[List[float]], str, dict]]" = OrderedDict()
        self._lock = asyncio.Lock()

    async def _prune(self):
        async with self._lock:
            now = _now()
            expired_keys = [k for k, (ts, _, _, _) in self._store.items() if now - ts > self.ttl_seconds]
            for k in expired_keys:
                self._store.pop(k, None)
            while len(self._store) > self.max_items:
                self._store.popitem(last=False)

    async def aadd(self, exp_id: str, content: str, metadata: dict):
        ts = _now()
        vec: Optional[List[float]] = None
        try:
            if self.encoder:
                vec = await self.encoder.aembed_query(content)
        except Exception as e:
            logger.warning(f"STM embed failed: {e}")
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

    async def asearch(self, query: str, n_results: int, filters: Optional[Dict] = None) -> List[dict]:
        await self._prune()
        qv: Optional[List[float]] = None
        if self.encoder:
            try:
                qv = await self.encoder.aembed_query(query)
            except Exception as e:
                logger.warning(f"STM query embed failed: {e}")

        results = []
        async with self._lock:
            for exp_id, (ts, vec, content, metadata) in reversed(self._store.items()):
                if filters:
                    if filters.get("type") and metadata.get("type") != filters["type"]:
                        continue
                    if filters.get("origin") and metadata.get("origin") != filters["origin"]:
                        continue
                    if filters.get("time_range") and not (filters["time_range"][0] <= ts <= filters["time_range"][1]):
                        continue
                
                score = self._cosine(qv, vec) if qv and vec else (1.0 if query.lower() in content.lower() else 0.0)
                if score >= (filters.get("min_score", 0.0) if filters else 0.0):
                    results.append({
                        "id": exp_id, "content": content, "metadata": metadata,
                        "distance": 1 - score, "score": score
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n_results]

class EpisodicMemory:
    """Unified memory system with short-term and long-term filtered recall."""
    def __init__(self):
        self.async_client: Optional[AsyncQdrantClient] = None
        self.encoder: Optional[OpenAIEmbeddings] = None
        self.short: Optional[ShortTermMemory] = None
        self._quota_lock = asyncio.Lock()
        self._quota_window_start = _now()
        self._per_origin_counts: Dict[str, int] = {}
        self._per_origin_bytes: Dict[str, int] = {}

    async def ainit(self):
        logger.info("Initializing EpisodicMemory...")
        self.async_client = get_async_qdrant_client()
        try:
            self.encoder = OpenAIEmbeddings()
            probe_vec = await self.encoder.aembed_query("dimension_probe")
            await aget_or_create_collection(collection_name=settings.QDRANT_COLLECTION_EPISODIC,
                                            vector_size=len(probe_vec))
        except Exception as e:
            logger.warning(f"Failed to init OpenAIEmbeddings or Qdrant collection: {e}")
            self.encoder = None
        self.short = ShortTermMemory(settings.MEMORY_SHORT_TTL_SECONDS, settings.MEMORY_SHORT_MAX_ITEMS, self.encoder)
        logger.info("EpisodicMemory initialized.")

    # (Omitted unchanged quota and PII methods for brevity)

    async def amemorize(self, experience: Experience):
        if not self.short: return
        # (Implementation remains the same)

    async def arecall(self, query: str, n_results: int = 5, filter_by_type: Optional[str] = None,
                      filter_by_origin: Optional[str] = None, min_score: float = 0.0,
                      hours_ago: Optional[int] = None) -> List[dict]:
        """Recalls experiences from short and long-term memory with optional filters."""
        if not self.short or not self.async_client or not self.encoder:
            logger.warning("Memory system not fully initialized, recall may be incomplete.")
            return []

        time_range = (_now() - (hours_ago * 3600), _now()) if hours_ago is not None else None
        filters = {"type": filter_by_type, "origin": filter_by_origin, "min_score": min_score, "time_range": time_range}

        # Search both layers concurrently
        short_term_task = self.short.asearch(query, n_results, filters)
        long_term_task = self._search_long_term(query, n_results, filters)
        short_res, long_res = await asyncio.gather(short_term_task, long_term_task)

        # Merge and deduplicate results
        combined = {r["id"]: r for r in short_res}
        for r in long_res:
            if r["id"] not in combined:
                combined[r["id"]] = r

        sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        logger.info(
            f"Recalled {len(sorted_results[:n_results])} experiences for query: '{query[:100]}...' with filters: {filters}")
        return sorted_results[:n_results]

    async def _search_long_term(self, query: str, n_results: int, filters: Dict) -> List[dict]:
        if not self.async_client or not self.encoder:
            return []
        try:
            query_vector = await self.encoder.aembed_query(query)
            qdrant_filter = self._build_qdrant_filter(filters)
            
            search_params = {
                "collection_name": settings.QDRANT_COLLECTION_EPISODIC,
                "query_vector": query_vector,
                "limit": n_results * 2,  # Fetch more to allow for merging
                "with_payload": True,
                "score_threshold": filters.get("min_score", 0.0),
                "query_filter": qdrant_filter
            }
            search_results = await self.async_client.search(**{k: v for k, v in search_params.items() if v is not None})

            return [{
                "id": str(sp.id),
                "content": decrypt_text(sp.payload.get('content', ''),
                                        settings.MEMORY_ENCRYPTION_KEY.get_secret_value()),
                "metadata": {k: v for k, v in sp.payload.items() if k != 'content'},
                "score": sp.score
            } for sp in search_results]
        except Exception as e:
            logger.error(f"Long-term memory search failed: {e}", exc_info=True)
            return []

    def _build_qdrant_filter(self, filters: Dict) -> Optional[models.Filter]:
        conditions = []
        if filters.get("type"):
            conditions.append(models.FieldCondition(key="type", match=models.MatchValue(value=filters["type"])))
        if filters.get("origin"):
            conditions.append(models.FieldCondition(key="origin", match=models.MatchValue(value=filters["origin"])))
        if filters.get("time_range"):
            start, end = filters["time_range"]
            conditions.append(models.FieldCondition(key="timestamp", range=models.Range(gte=start, lte=end)))

        return models.Filter(must=conditions) if conditions else None

memory_core = EpisodicMemory()

async def initialize_memory_core():
    await memory_core.ainit()
