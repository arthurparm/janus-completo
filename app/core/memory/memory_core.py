import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from qdrant_client import QdrantClient, models

from app.config import settings
from app.models.schemas import Experience, VectorCollection
from app.core.embeddings.embedding_manager import embed_text

logger = structlog.get_logger(__name__)


class MemoryCore:
    """
    Gerencia a conexão e as operações com o banco de dados vetorial (Qdrant).
    """

    def __init__(self):
        self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = VectorCollection.EPISODIC_MEMORY.value
        self._vector_size = int(getattr(settings, "MEMORY_VECTOR_SIZE", 1536))

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
            logger.error("Falha ao inicializar o MemoryCore (Qdrant)", exc_info=e)
            raise

    async def amemorize(self, experience: Experience):
        """
        Adiciona uma experiência à memória (upsert).
        Gera embedding do conteúdo e adiciona metadados auxiliares (ts_ms) para filtros.
        """
        try:
            vector = embed_text(experience.content)
        except Exception:
            logger.warning("Falha ao gerar embedding; usando vetor nulo.")
            vector = [0.0] * self._vector_size

        # auxiliar: timestamp numérico em milissegundos para filtros de janela
        try:
            # Experience.timestamp é string ISO
            dt = datetime.fromisoformat(experience.timestamp)
            ts_ms = int(dt.timestamp() * 1000)
        except Exception:
            ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        payload = experience.dict()
        payload["ts_ms"] = ts_ms

        point = models.PointStruct(
            id=experience.id,
            payload=payload,
            vector=vector,
        )
        self.client.upsert(collection_name=self.collection_name, points=[point], wait=True)

    async def arecall(self, query: str, limit: Optional[int] = 10, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Busca por experiências na memória usando embeddings do texto de consulta.
        """
        try:
            query_vector = embed_text(query)
        except Exception:
            logger.warning("Falha ao gerar embedding da consulta; usando vetor nulo.")
            query_vector = [0.0] * self._vector_size

        effective_limit = limit if limit is not None else 10
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=effective_limit,
            with_payload=True,
        )
        results = [{
            "id": hit.id,
            "content": hit.payload.get('content'),
            "metadata": hit.payload.get('metadata'),
            "score": hit.score
        } for hit in hits]
        if min_score is not None:
            results = [r for r in results if float(r.get("score", 0.0)) >= float(min_score)]
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
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=eff_limit,
            with_payload=True,
            query_filter=qfilter,
        )
        results = [{
            "id": hit.id,
            "content": hit.payload.get('content'),
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

        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=eff_limit,
            with_payload=True,
            query_filter=qfilter,
        )
        results = [{
            "id": h.id,
            "content": h.payload.get('content'),
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
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=[0.0] * self._vector_size,
            limit=limit or 10,
            with_payload=True,
            query_filter=qfilter,
        )
        results = [{
            "id": h.id,
            "content": h.payload.get('content'),
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
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=[0.0] * self._vector_size,
            limit=limit or 10,
            with_payload=True,
            query_filter=qfilter,
        )
        results = [{
            "id": h.id,
            "content": h.payload.get('content'),
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


# --- Funções de criptografia (stub) ---
def decrypt_text(encrypted_text: str, key: str) -> str:
    """
    Stub para descriptografia de texto.
    """
    logger.warning("decrypt_text chamado mas não implementado - retornando texto sem descriptografia")
    return encrypted_text
