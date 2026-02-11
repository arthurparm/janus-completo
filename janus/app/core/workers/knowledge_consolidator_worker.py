"""
Knowledge Consolidator Worker - Refactored Sprint 13

Responsável por transformar memória episódica (Qdrant) em memória semântica (Neo4j).
Agora atua como um orquestrador enxuto, delegando para KnowledgeExtractionService
e KnowledgeGraphService.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from prometheus_client import Counter, Histogram

from app.core.infrastructure.resilience import CircuitBreaker, resilient
from app.db.vector_store import get_async_qdrant_client
from app.models.schemas import VectorCollection
from app.services.knowledge_extraction_service import get_knowledge_extraction_service
from app.services.knowledge_graph_service import get_knowledge_graph_service

logger = logging.getLogger(__name__)

# Métricas
CONSOLIDATION_COUNTER = Counter(
    "knowledge_consolidation_total",
    "Total de consolidações de conhecimento",
    ["outcome", "exception_type"],
)
CONSOLIDATION_LATENCY = Histogram(
    "knowledge_consolidation_latency_seconds",
    "Latência de consolidação de conhecimento",
    ["outcome"],
)
ENTITIES_EXTRACTED = Counter("knowledge_entities_extracted_total", "Total de entidades extraídas")
RELATIONSHIPS_CREATED = Counter(
    "knowledge_relationships_created_total", "Total de relacionamentos criados no grafo"
)

# Circuit Breaker para operações de consolidação
_consolidation_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


class KnowledgeConsolidator:
    """Worker orquestrador que consolida memória episódica em memória semântica."""

    def __init__(self):
        self.qdrant_client = None
        self._initialized = False

    def _chunk_text(
        self, text: Any, chunk_size: int = 1000, overlap: int = 200
    ) -> list[str]:
        """Divide texto em chunks com sobreposição. Retorna lista vazia para inputs inválidos."""
        if not isinstance(text, str):
            return []
        if not text:
            return []
        if chunk_size <= 0:
            return [text]

        if len(text) <= chunk_size:
            return [text]

        safe_overlap = max(0, min(int(overlap), int(chunk_size) - 1))
        chunks: list[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            if end >= text_len:
                break
            start = end - safe_overlap
            if start < 0:
                start = 0

        return chunks

    def _normalize_point_id(self, experience_id: str) -> str | int:
        """
        Aplica o mesmo mapeamento usado na ingestão do MemoryCore:
        - tenta converter para int;
        - caso contrário, UUID5 determinístico baseado na string do ID.
        """
        try:
            return int(experience_id)
        except Exception:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(experience_id)))

    async def _initialize(self):
        """Inicializa componentes (lazy)."""
        if self._initialized:
            return

        try:
            self.qdrant_client = get_async_qdrant_client()
            self._initialized = True
            logger.info("KnowledgeConsolidator initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeConsolidator: {e}")

    async def consolidate_batch(self, limit: int = 10, min_score: float = 0.0) -> dict[str, Any]:
        """
        Consolida um lote de experiências da memória episódica.
        Entry point principal do worker.
        """
        stats = {
            "successful": 0,
            "total_processed": 0,
            "total_entities": 0,
            "total_relationships": 0,
        }

        await self._initialize()
        if not self.qdrant_client:
            logger.warning("Qdrant client unavailable, returning empty stats")
            return stats

        try:
            # 1. Buscar experiências não consolidadas
            # Nota: Em um sistema real, teríamos um flag 'consolidated' no payload ou uma coleção separada
            # Para este exemplo, vamos assumir que buscamos as mais recentes e verificamos se já existem no grafo

            # Filtro simplificado: buscar ultimas memories
            # Idealmente: filter={"must_not": [{"key": "metadata.consolidated", "match": {"value": True}}]}
            try:
                results = await self.qdrant_client.scroll(
                    collection_name=VectorCollection.EPISODIC_MEMORY.value,  # Nome hipotético da coleção de memória
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception as e:
                # Se a coleção não existir ou der erro de conexão
                logger.warning(f"Failed to scroll episodes collection: {e}")
                return stats

            points = results[0]  # scroll returns (points, next_page_offset)
            stats["total_processed"] = len(points)

            for point in points:
                if not point.payload:
                    continue

                exp_id = point.id
                content = point.payload.get("content", "") or point.payload.get("page_content", "")
                metadata = point.payload.get("metadata", {})

                # Skip se já consolidado (verificação otimizada seria no filtro do qdrant)
                if metadata.get("consolidated"):
                    continue

                try:
                    result = await self.consolidate_experience(str(exp_id), content, metadata)
                    if result:
                        stats["successful"] += 1
                        stats["total_entities"] += result.get("entities_created", 0)
                        stats["total_relationships"] += result.get("relationships_created", 0)
                except Exception:
                    # Individual failures logged in consolidate_experience
                    pass

            return stats

        except Exception as e:
            logger.error(f"Batch consolidation failed: {e}", exc_info=True)
            CONSOLIDATION_COUNTER.labels(outcome="failure", exception_type=type(e).__name__).inc()
            return stats

    @resilient(circuit_breaker=_consolidation_cb)
    async def consolidate_experience(
        self, experience_id: str, experience_content: str, metadata: dict[str, Any]
    ):
        """
        Consolida uma única experiência.
        """
        start_time = time.time()
        logger.info(f"Consolidating experience {experience_id}...")

        try:
            # 1. Extração
            extractor = get_knowledge_extraction_service()
            extracted_data = await extractor.extract_from_text(experience_content, metadata)

            if not extracted_data:
                logger.warning(f"No knowledge extracted for experience {experience_id}")
                return

            num_entities = len(extracted_data.get("entities", []))
            num_rels = len(extracted_data.get("relationships", []))

            ENTITIES_EXTRACTED.inc(num_entities)

            # 2. Persistência
            graph_svc = get_knowledge_graph_service()
            created_ents, created_rels = await graph_svc.persist_extraction(
                experience_id, extracted_data, metadata
            )

            RELATIONSHIPS_CREATED.inc(created_rels)

            # 3. Marcar como consolidado (Atualizar Qdrant)
            await self._mark_as_consolidated(experience_id, metadata)

            duration = time.time() - start_time
            CONSOLIDATION_LATENCY.labels(outcome="success").observe(duration)
            CONSOLIDATION_COUNTER.labels(outcome="success", exception_type="None").inc()

            logger.info(
                f"Consolidated experience {experience_id}: {created_ents} entities, {created_rels} relationships."
            )

            # Retorna stats para o chamador
            return {"entities_created": created_ents, "relationships_created": created_rels}

        except Exception as e:
            duration = time.time() - start_time
            CONSOLIDATION_LATENCY.labels(outcome="error").observe(duration)
            CONSOLIDATION_COUNTER.labels(outcome="failure", exception_type=type(e).__name__).inc()
            logger.error(f"Failed to consolidate experience {experience_id}: {e}", exc_info=True)
            raise  # Re-raise for circuit breaker

    async def _mark_as_consolidated(self, experience_id: str, metadata: dict[str, Any] | None = None):
        """Atualiza flag no Qdrant para evitar reprocessamento."""
        point_id = self._normalize_point_id(experience_id)
        collection = VectorCollection.EPISODIC_MEMORY.value
        try:
            await self.qdrant_client.set_payload(
                collection_name=collection,
                payload={"metadata": {"consolidated": True}},
                points=[point_id],
            )
        except Exception as e:
            msg = str(e).lower()
            if "not found" in msg or "404" in msg:
                # ExperiÇõÇœa nÇœo estÇü na coleÇõÇœo (chats indexados em coleÇõÇæes user_* usam IDs prÇüprios)
                logger.info(
                    "Skipping consolidated flag because point was not found in Qdrant "
                    f"(experience_id={experience_id}, collection={collection})"
                )
                return
            logger.warning(
                f"Failed to mark experience {experience_id} as consolidated: {e}", exc_info=True
            )


# Instância global
knowledge_consolidator = KnowledgeConsolidator()
