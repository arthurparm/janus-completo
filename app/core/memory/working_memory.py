import time
import logging
from collections import OrderedDict
from typing import List, Dict, Optional
from datetime import datetime, timezone

from app.config import settings
from app.models.schemas import Experience

logger = logging.getLogger(__name__)


class WorkingMemory:
    """
    Memória de trabalho (curto prazo) em processo, com TTL e capacidade limitada.
    Armazena experiências leves para acesso rápido durante uma sessão de raciocínio.
    """

    def __init__(self, ttl_seconds: Optional[int] = None, max_items: Optional[int] = None):
        self.ttl_seconds = int(ttl_seconds if ttl_seconds is not None else getattr(settings, "MEMORY_SHORT_TTL_SECONDS", 600))
        self.max_items = int(max_items if max_items is not None else getattr(settings, "MEMORY_SHORT_MAX_ITEMS", 512))
        self._store: OrderedDict[str, Experience] = OrderedDict()

    def _now_ms(self) -> int:
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    def _expired(self, exp: Experience) -> bool:
        try:
            dt = datetime.fromisoformat(exp.timestamp)
            age = int(datetime.now(timezone.utc).timestamp() - dt.timestamp())
            return age > self.ttl_seconds
        except Exception:
            return False

    def _purge_expired(self) -> None:
        removed = 0
        for key in list(self._store.keys()):
            exp = self._store.get(key)
            if exp and self._expired(exp):
                self._store.pop(key, None)
                removed += 1
        if removed:
            logger.debug("WorkingMemory: removidas %d entradas expiradas", removed)

    def _trim_capacity(self) -> None:
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def add(self, type: str, content: str, metadata: Optional[Dict] = None) -> Experience:
        """Adiciona uma experiência efêmera à memória de trabalho."""
        self._purge_expired()
        meta = dict(metadata or {})
        meta.setdefault("origin", "working_memory")
        meta.setdefault("volatile", True)
        exp = Experience(type=type, content=content, metadata=meta)
        self._store[exp.id] = exp
        self._store.move_to_end(exp.id)
        self._trim_capacity()
        return exp

    def get_recent(self, limit: int = 5) -> List[Dict[str, any]]:
        """Retorna as entradas mais recentes."""
        self._purge_expired()
        items = list(self._store.values())[-limit:][::-1]
        return [{"id": e.id, "content": e.content, "metadata": e.metadata, "score": 1.0} for e in items]

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, any]]:
        """Busca ingênua por substring no conteúdo da memória de trabalho."""
        self._purge_expired()
        q = (query or "").strip().lower()
        scored: List[tuple] = []
        for e in self._store.values():
            text = e.content.lower()
            if not q:
                score = 0.5
            elif q in text:
                score = 1.0
            else:
                # score fraco por similaridade de comprimento sobre diferenças
                overlap = len(set(q.split()) & set(text.split()))
                score = 0.2 + 0.1 * overlap
            scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [e for _, e in scored[:limit]]
        return [{"id": e.id, "content": e.content, "metadata": e.metadata, "score": float(s)} for s, e in scored[:limit]]


# --- Singleton simples ---
_working_mem_instance: Optional[WorkingMemory] = None


def get_working_memory() -> WorkingMemory:
    global _working_mem_instance
    if _working_mem_instance is None:
        _working_mem_instance = WorkingMemory()
    return _working_mem_instance