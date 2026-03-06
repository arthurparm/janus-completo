"""
Knowledge Consolidator Worker - Refactored Sprint 13

Responsável por transformar memória episódica (Qdrant) em memória semântica (Neo4j).
Agora atua como um orquestrador enxuto, delegando para KnowledgeExtractionService
e KnowledgeGraphService.
"""

import asyncio
import hashlib
import structlog
import time
import uuid
from datetime import datetime
from typing import Any

from prometheus_client import Counter, Histogram
from qdrant_client import models

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, resilient
from app.db.vector_store import get_async_qdrant_client
from app.models.schemas import VectorCollection
from app.services.knowledge_extraction_service import get_knowledge_extraction_service
from app.services.knowledge_graph_service import get_knowledge_graph_service

logger = structlog.get_logger(__name__)

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
        self.is_running = False
        self._task: asyncio.Task | None = None
        self._batch_lock = asyncio.Lock()
        self._last_llm_skip_log_ts: float | None = None

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

    def _normalize_point_id(self, experience_id: str | int) -> str | int:
        """
        Aplica o mesmo mapeamento usado na ingestão do MemoryCore:
        - mantém int quando possível;
        - mantém UUID válido sem alterar;
        - caso contrário, UUID5 determinístico baseado na string do ID.
        """
        try:
            return int(experience_id)
        except Exception:
            exp_id_str = str(experience_id)
            try:
                uuid.UUID(exp_id_str)
                return exp_id_str
            except Exception:
                return str(uuid.uuid5(uuid.NAMESPACE_DNS, exp_id_str))

    async def _initialize(self):
        """Inicializa componentes (lazy)."""
        if self._initialized:
            return

        try:
            self.qdrant_client = get_async_qdrant_client()
            self._initialized = True
            logger.info("KnowledgeConsolidator initialized.")
        except Exception as e:
            logger.error("knowledge_consolidator_init_failed", error=str(e))

    async def start(self, *, limit: int = 10, min_score: float = 0.0) -> None:
        """Inicia o ciclo periódico de consolidação em background."""
        await self._initialize()
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(
            self._consolidation_cycle(limit=limit, min_score=min_score)
        )
        logger.info("knowledge_consolidator_scheduler_started")

    async def stop(self) -> None:
        """Interrompe o ciclo periódico de consolidação."""
        if not self.is_running:
            return
        self.is_running = False
        task = self._task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None
        logger.info("knowledge_consolidator_scheduler_stopped")

    async def _consolidation_cycle(self, *, limit: int, min_score: float) -> None:
        """Loop periódico de consolidação em lote."""
        interval = getattr(settings, "KNOWLEDGE_CONSOLIDATOR_INTERVAL_SECONDS", 60)
        while self.is_running:
            try:
                stats = await self.consolidate_batch(limit=limit, min_score=min_score)
                extractor = get_knowledge_extraction_service()
                if extractor.is_llm_temporarily_unavailable():
                    now = time.time()
                    if self._last_llm_skip_log_ts is None or now - self._last_llm_skip_log_ts >= 60:
                        self._last_llm_skip_log_ts = now
                        logger.info(
                            "knowledge_consolidator_cycle_skipped_llm_unavailable",
                            cooldown_remaining_seconds=round(
                                extractor.llm_unavailable_remaining_seconds(), 1
                            ),
                            total_processed=stats.get("total_processed", 0),
                        )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("knowledge_consolidator_cycle_failed", error=str(e), exc_info=True)

            if not self.is_running:
                break

            await asyncio.sleep(interval)

    async def consolidate_batch(self, limit: int = 10, min_score: float = 0.0) -> dict[str, Any]:
        """
        Consolida um lote de experiências da memória episódica.
        Entry point principal do worker.
        """
        async with self._batch_lock:
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
                try:
                    pending_filter = models.Filter(
                        should=[
                            models.FieldCondition(
                                key="metadata.consolidation_status",
                                match=models.MatchValue(value="pending"),
                            ),
                            models.IsNullCondition(
                                is_null=models.PayloadField(key="metadata.consolidation_status")
                            ),
                            models.IsEmptyCondition(
                                is_empty=models.PayloadField(key="metadata.consolidation_status")
                            ),
                        ]
                    )
                    results = await self.qdrant_client.scroll(
                        collection_name=VectorCollection.EPISODIC_MEMORY.value,
                        scroll_filter=pending_filter,
                        limit=limit,
                        with_payload=True,
                        with_vectors=False,
                    )
                except Exception as e:
                    # Se a coleção não existir ou der erro de conexão
                    logger.warning("knowledge_consolidator_scroll_failed", error=str(e))
                    return stats

                points = results[0]  # scroll returns (points, next_page_offset)
                stats["total_processed"] = len(points)

                for point in points:
                    if not point.payload:
                        continue

                    exp_id = point.id
                    content = point.payload.get("content", "") or point.payload.get(
                        "page_content", ""
                    )
                    metadata = point.payload.get("metadata", {})

                    if (metadata.get("consolidation_status") or "pending") != "pending":
                        continue

                    try:
                        result = await self.consolidate_experience(str(exp_id), content, metadata)
                        if result:
                            stats["successful"] += 1
                            stats["total_entities"] += result.get("entities_created", 0)
                            stats["total_relationships"] += result.get(
                                "relationships_created", 0
                            )
                    except Exception:
                        # Individual failures logged in consolidate_experience
                        pass

                return stats

            except Exception as e:
                logger.error("knowledge_consolidator_batch_failed", error=str(e), exc_info=True)
                CONSOLIDATION_COUNTER.labels(
                    outcome="failure", exception_type=type(e).__name__
                ).inc()
                return stats

    @resilient(circuit_breaker=_consolidation_cb)
    async def consolidate_experience(
        self, experience_id: str, experience_content: str, metadata: dict[str, Any]
    ):
        """
        Consolida uma única experiência.
        """
        start_time = time.time()
        logger.info("knowledge_consolidator_experience_started", experience_id=experience_id)

        try:
            extractor = get_knowledge_extraction_service()
            consolidation_hash = str(metadata.get("consolidation_hash") or "").strip()
            if not consolidation_hash:
                consolidation_hash = self._build_consolidation_hash(experience_content, metadata)
                metadata = dict(metadata or {})
                metadata["consolidation_hash"] = consolidation_hash

            chunks = [experience_content]
            if str(metadata.get("content_kind") or "") != "code_summary":
                chunks = self._chunk_text(experience_content, chunk_size=3500, overlap=300) or [experience_content]

            extracted_data = {"entities": [], "relationships": []}
            for chunk in chunks:
                chunk_result = await extractor.extract_from_text(chunk, metadata)
                if not chunk_result:
                    continue
                extracted_data["entities"].extend(chunk_result.get("entities", []))
                extracted_data["relationships"].extend(chunk_result.get("relationships", []))

            if not extracted_data["entities"] and not extracted_data["relationships"]:
                if extractor.is_llm_temporarily_unavailable():
                    logger.debug(
                        "knowledge_consolidator_experience_skipped_llm_unavailable",
                        experience_id=experience_id,
                    )
                    return
                logger.warning(
                    "knowledge_consolidator_no_extraction",
                    experience_id=experience_id,
                )
                return

            num_entities = len(extracted_data.get("entities", []))
            num_rels = len(extracted_data.get("relationships", []))

            ENTITIES_EXTRACTED.inc(num_entities)

            graph_svc = get_knowledge_graph_service()
            created_ents, created_rels = await graph_svc.persist_extraction(
                experience_id, extracted_data, metadata
            )

            RELATIONSHIPS_CREATED.inc(created_rels)

            await self._mark_as_consolidated(
                experience_id,
                metadata,
                entities_created=created_ents,
                relationships_created=created_rels,
            )

            duration = time.time() - start_time
            CONSOLIDATION_LATENCY.labels(outcome="success").observe(duration)
            CONSOLIDATION_COUNTER.labels(outcome="success", exception_type="None").inc()

            logger.info(
                "knowledge_consolidator_experience_completed",
                experience_id=experience_id,
                entities_created=created_ents,
                relationships_created=created_rels,
            )

            # Retorna stats para o chamador
            return {"entities_created": created_ents, "relationships_created": created_rels}

        except Exception as e:
            duration = time.time() - start_time
            CONSOLIDATION_LATENCY.labels(outcome="error").observe(duration)
            CONSOLIDATION_COUNTER.labels(outcome="failure", exception_type=type(e).__name__).inc()
            logger.error(
                "knowledge_consolidator_experience_failed",
                experience_id=experience_id,
                error=str(e),
                exc_info=True,
            )
            raise  # Re-raise for circuit breaker

    def _build_consolidation_hash(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        metadata = dict(metadata or {})
        normalized = "|".join(
            [
                str(metadata.get("origin") or "").strip().lower(),
                str(metadata.get("source_kind") or "").strip().lower(),
                str(metadata.get("file_path") or "").strip().lower(),
                str(metadata.get("sha_after") or "").strip().lower(),
                str(content or "").strip(),
            ]
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def _mark_as_consolidated(
        self,
        experience_id: str,
        metadata: dict[str, Any] | None = None,
        *,
        entities_created: int = 0,
        relationships_created: int = 0,
    ):
        """Atualiza flag no Qdrant para evitar reprocessamento."""
        point_id = self._normalize_point_id(experience_id)
        collection = VectorCollection.EPISODIC_MEMORY.value
        try:
            payload_metadata = dict(metadata or {})
            payload_metadata["consolidated"] = True
            payload_metadata["consolidation_status"] = "done"
            payload_metadata["consolidated_at"] = int(time.time() * 1000)
            payload_metadata["neo4j_relationships_count"] = int(relationships_created)
            payload_metadata["neo4j_entities_count"] = int(entities_created)
            await self.qdrant_client.set_payload(
                collection_name=collection,
                payload={"metadata": payload_metadata},
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
                "knowledge_consolidator_mark_consolidated_failed",
                experience_id=experience_id,
                error=str(e),
                exc_info=True,
            )


# Instância global
knowledge_consolidator = KnowledgeConsolidator()
