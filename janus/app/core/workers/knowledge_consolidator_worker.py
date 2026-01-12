"""
Knowledge Consolidator Worker - Sprint 8

Responsável por transformar memória episódica (Qdrant) em memória semântica (Neo4j).
Extrai entidades, relacionamentos e conhecimento estruturado das experiências brutas.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from prometheus_client import Counter, Histogram
from qdrant_client import AsyncQdrantClient

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, resilient
from app.core.llm.llm_manager import ModelPriority, ModelRole, get_llm
from app.core.memory.graph_guardian import graph_guardian
from app.core.memory.memory_core import decrypt_text, get_memory_db
from app.db.graph import get_graph_db
from app.db.graph import get_graph_db
from app.db.vector_store import get_async_qdrant_client
from app.models.schemas import Experience
from app.core.memory.graph_embeddings import GraphEmbeddingsManager

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

# Prompt para extração de conhecimento
EXTRACTION_PROMPT = """Você é um especialista em extração de conhecimento estruturado.

Analise a experiência abaixo e extraia:
1. **Entidades**: Conceitos, tecnologias, pessoas, lugares, ferramentas mencionadas
2. **Relacionamentos**: Como as entidades se relacionam entre si
3. **Insights**: Conhecimento-chave ou lições aprendidas

EXPERIÊNCIA:
{experience_content}

METADADOS:
{metadata}

Retorne APENAS um JSON válido com esta estrutura:
{{
  "entities": [
    {{"name": "nome_da_entidade", "type": "tipo", "properties": {{}}}},
    ...
  ],
  "relationships": [
    {{"from": "entidade_origem", "to": "entidade_destino", "type": "tipo_relacao", "properties": {{}}}},
    ...
  ],
  "insights": [
    {{"text": "insight descoberto", "confidence": 0.8}},
    ...
  ]
}}

Tipos comuns de entidades: CONCEPT, TECHNOLOGY, TOOL, PERSON, ERROR, SOLUTION, PATTERN
Tipos comuns de relacionamentos: USES, RELATES_TO, CAUSES, SOLVES, DEPENDS_ON, IMPLEMENTS

Seja conciso e preciso. Extraia apenas informações relevantes e verificáveis.
"""


class KnowledgeConsolidator:
    """Worker que consolida memória episódica em memória semântica."""

    def __init__(self):
        self.qdrant_client: AsyncQdrantClient | None = None
        self.llm: BaseChatModel | None = None
        self._initialized = False

    async def _initialize(self):
        """Inicializa componentes necessários."""
        if self._initialized:
            return

        try:
            # Cliente Qdrant (assíncrono)
            self.qdrant_client = get_async_qdrant_client()
            logger.info("Cliente Qdrant inicializado para consolidação.")
        except Exception as e:
            logger.error(f"Falha ao inicializar cliente Qdrant: {e}")
            self.qdrant_client = None

        try:
            # LLM para extração
            self.llm = await get_llm(
                role=ModelRole.KNOWLEDGE_CURATOR, priority=ModelPriority.FAST_AND_CHEAP
            )
            logger.info(f"LLM inicializado para consolidação: {self.llm.__class__.__name__}")
        except Exception as e:
            logger.error(f"Falha ao inicializar LLM: {e}")
            self.llm = None

        # Verifica health do Neo4j
        try:
            db = await get_graph_db()
            ok = await db.health_check()
            if not ok:
                logger.warning("Neo4j não está saudável. Consolidação pode falhar.")
        except Exception as e:
            logger.warning(f"Falha ao verificar saúde do Neo4j: {e}")

        self._initialized = True

    def _chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
        """Divide texto em chunks com overlap para extração robusta."""
        try:
            if not isinstance(text, str):
                return []
            t = text.strip()
            if len(t) <= chunk_size:
                return [t]
            chunks: list[str] = []
            start = 0
            end = chunk_size
            while start < len(t):
                chunk = t[start:end]
                chunks.append(chunk)
                if end >= len(t):
                    break
                start = max(0, end - overlap)
                end = start + chunk_size
            return chunks
        except Exception:
            return [text]

    async def _extract_knowledge_with_llm(
        self, experience_content: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Usa LLM para extrair conhecimento estruturado de uma experiência.

        Args:
            experience_content: Conteúdo da experiência
            metadata: Metadados da experiência

        Returns:
            Dicionário com entidades, relacionamentos e insights
        """
        if not self.llm:
            raise ValueError("LLM não inicializado para extração de conhecimento.")

        # Formata prompt
        prompt_text = EXTRACTION_PROMPT.format(
            experience_content=experience_content[:2000],  # Limita tamanho
            metadata=json.dumps(metadata, indent=2, ensure_ascii=False)[:500],
        )

        messages = [
            SystemMessage(content="Você é um especialista em extração de conhecimento."),
            HumanMessage(content=prompt_text),
        ]

        # Invoca LLM
        start = time.perf_counter()
        try:
            # Usa ainvoke se disponível, senão invoke
            if hasattr(self.llm, "ainvoke"):
                response = await self.llm.ainvoke(messages)
            else:
                # Fallback síncrono
                response = await asyncio.to_thread(self.llm.invoke, messages)

            elapsed = time.perf_counter() - start
            logger.debug(f"Extração LLM concluída em {elapsed:.2f}s")

            # Parse JSON da resposta
            response_text = response.content if hasattr(response, "content") else str(response)

            # Tenta extrair JSON da resposta (pode vir com markdown)
            response_text = response_text.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text)

            # Validação básica
            if not isinstance(result, dict):
                raise ValueError("Resposta LLM não é um dicionário")

            result.setdefault("entities", [])
            result.setdefault("relationships", [])
            result.setdefault("insights", [])

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Falha ao parsear JSON da resposta LLM: {e}")
            logger.debug(f"Resposta LLM: {response_text[:500]}")
            return {"entities": [], "relationships": [], "insights": []}
        except Exception as e:
            logger.error(f"Erro na extração de conhecimento com LLM: {e}", exc_info=True)
            return {"entities": [], "relationships": [], "insights": []}

    async def _persist_to_neo4j(
        self, experience_id: str, extracted_data: dict[str, Any], source_metadata: dict[str, Any]
    ) -> tuple[int, int]:
        """
        Persiste entidades e relacionamentos extraídos no Neo4j.

        Args:
            experience_id: ID da experiência origem
            extracted_data: Dados extraídos (entidades, relacionamentos, insights)
            source_metadata: Metadados da experiência

        Returns:
            Tupla (num_entidades, num_relacionamentos) criados
        """
        entities_created = 0
        relationships_created = 0

        db = await get_graph_db()

        # Cria nó da experiência
        try:
            await db.query(
                """
                MERGE (e:Experience {id: $exp_id})
                SET e.timestamp = $timestamp,
                    e.type = $exp_type,
                    e.consolidated_at = datetime()
                """,
                params={
                    "exp_id": experience_id,
                    "timestamp": source_metadata.get("timestamp", datetime.utcnow().isoformat()),
                    "exp_type": source_metadata.get("type", "unknown"),
                },
                operation="create_experience_node",
            )
        except Exception as e:
            logger.error(f"Erro ao criar nó de experiência: {e}")

        # Cria entidades (com normalização via Graph Guardian) em lote por tipo
        normalized_entities = []
        for entity in extracted_data.get("entities", []):
            if not entity.get("name"):
                continue
            try:
                ne = graph_guardian.validate_and_normalize_entity(
                    name=entity["name"],
                    entity_type=entity.get("type", "CONCEPT"),
                    properties=entity.get("properties", {}),
                )
                props = ne["properties"]
                props["original_name"] = ne.get("original_name", ne["name"])
                normalized_entities.append(
                    {
                        "name": ne["name"],
                        "type": ne["type"],
                        "properties": props,
                    }
                )
            except ValueError as ve:
                logger.warning(f"Entidade inválida ignorada: {entity.get('name')} - {ve}")
            except Exception as e:
                logger.error(f"Erro ao normalizar entidade {entity.get('name')}: {e}")

        # --- EVOLUTION: Pre-calculate Embeddings for Real-time consistency ---
        concepts_to_embed = []
        indices_map = {} # map normalized entity index to 'normalized_entities' list index
        
        for idx, ne in enumerate(normalized_entities):
            # Only embed Concepts, Technologies, Tools, etc. (Skip specialized types if needed)
            # For robustness, we embed mostly everything that is useful for search
            if ne["type"] in ("CONCEPT", "TECHNOLOGY", "TOOL", "PERSON", "PATTERN", "SOLUTION", "ERROR"):
                concepts_to_embed.append(ne["name"])
                indices_map[len(concepts_to_embed)-1] = idx
        
        if concepts_to_embed:
            try:
                emb_manager = GraphEmbeddingsManager()
                vectors = await emb_manager.embed_batch(concepts_to_embed)
                for i, vec in enumerate(vectors):
                    original_idx = indices_map[i]
                    # Inject embedding directly into properties to be picked up by Cypher
                    normalized_entities[original_idx]["embedding"] = vec
            except Exception as e:
                logger.warning(f"Falha ao gerar embeddings em tempo real na consolidação: {e}")

        # Executa MERGE de entidades em transação única, agrupando por label
        if normalized_entities:
            try:
                async with await db.get_session() as session:
                    tx = await session.begin_transaction()
                    try:
                        from collections import defaultdict

                        groups = defaultdict(list)
                        for ne in normalized_entities:
                            groups[ne["type"]].append(ne)
                        try:
                            await db.register_relationship_type(tx, "MENTIONS")
                        except Exception:
                            pass
                        for label, batch in groups.items():
                            await tx.run(
                                f"""
                                UNWIND $batch AS ent
                                MERGE (n:{label} {{name: ent.name}})
                                SET n += ent.properties,
                                    n.last_seen = datetime()
                                FOREACH (ignoreMe IN CASE WHEN ent.embedding IS NOT NULL THEN [1] ELSE [] END |
                                    SET n.embedding = ent.embedding
                                )
                                WITH n
                                MATCH (e:Experience {{id: $exp_id}})
                                MERGE (e)-[:MENTIONS]->(n)
                                """,
                                batch=batch,
                                exp_id=experience_id,
                            )
                            entities_created += len(batch)
                        await tx.commit()
                        try:
                            ENTITIES_EXTRACTED.inc(entities_created)
                        except Exception:
                            pass
                    finally:
                        await tx.close()
            except Exception as e:
                logger.error(f"Erro em transação de entidades: {e}")

        # Cria relacionamentos (com normalização via Graph Guardian) em lote por tipo
        normalized_rels = []
        for rel in extracted_data.get("relationships", []):
            if not rel.get("from") or not rel.get("to"):
                continue
            try:
                nr = graph_guardian.validate_and_normalize_relationship(
                    from_entity=rel["from"],
                    to_entity=rel["to"],
                    rel_type=rel.get("type", "RELATES_TO"),
                    properties=rel.get("properties", {}),
                )
                if nr is None:
                    logger.debug(f"Relacionamento inválido ignorado: {rel}")
                    continue
                props = nr["properties"]
                if "confidence" not in props:
                    props["confidence"] = 0.5
                props["original_from"] = nr.get("original_from", nr["from"])
                props["original_to"] = nr.get("original_to", nr["to"])
                if source_metadata.get("source_snippet"):
                    props["source_snippet"] = source_metadata.get("source_snippet")
                normalized_rels.append(
                    {
                        "from_name": nr["from"],
                        "to_name": nr["to"],
                        "type": nr["type"],
                        "properties": props,
                    }
                )
            except Exception as e:
                logger.error(
                    f"Erro ao normalizar relacionamento {rel.get('from')} -> {rel.get('to')}: {e}"
                )

        def _should_quarantine(rel: dict[str, Any]) -> bool:
            t = rel.get("type")
            a = rel.get("from_name", "")
            b = rel.get("to_name", "")
            if not a or not b:
                return True
            if a == b:
                return True
            if t == "RELATES_TO" and len(a) < 3 and len(b) < 3:
                return True
            try:
                conf = float(rel.get("properties", {}).get("confidence", 1.0))
                if conf < 0.6:
                    return True
            except Exception:
                pass
            return False

        quarantined: list[dict[str, Any]] = []
        valid_rels: list[dict[str, Any]] = []
        for nr in normalized_rels:
            if _should_quarantine(nr):
                quarantined.append(nr)
            else:
                valid_rels.append(nr)

        if valid_rels:
            try:
                async with await db.get_session() as session:
                    tx = await session.begin_transaction()
                    try:
                        from collections import defaultdict

                        groups = defaultdict(list)
                        for nr in valid_rels:
                            groups[nr["type"]].append(nr)
                        for rel_type, batch in groups.items():
                            try:
                                await db.register_relationship_type(tx, rel_type)
                            except Exception:
                                pass
                            await tx.run(
                                f"""
                                UNWIND $batch AS rel
                                MATCH (a {{name: rel.from_name}})
                                MATCH (b {{name: rel.to_name}})
                                MERGE (a)-[r:{rel_type}]->(b)
                                ON CREATE SET r += rel.properties,
                                    r.discovered_at = datetime(),
                                    r.first_seen = datetime(),
                                    r.occurrences = 1,
                                    r.source_experience = $exp_id
                                ON MATCH SET r += rel.properties,
                                    r.last_seen = datetime(),
                                    r.occurrences = coalesce(r.occurrences, 0) + 1,
                                    r.source_experience = $exp_id
                                """,
                                batch=batch,
                                exp_id=experience_id,
                            )
                            relationships_created += len(batch)
                        await tx.commit()
                        try:
                            RELATIONSHIPS_CREATED.inc(relationships_created)
                        except Exception:
                            pass
                    finally:
                        await tx.close()
            except Exception as e:
                logger.error(f"Erro em transação de relacionamentos: {e}")

        if quarantined:
            try:
                async with await db.get_session() as session:
                    tx = await session.begin_transaction()
                    try:
                        try:
                            await db.register_relationship_type(tx, "EXTRACTED_FROM")
                        except Exception:
                            pass
                        for q in quarantined:
                            await tx.run(
                                """
                                MERGE (q:Quarantine {reason: $reason, type: $type})
                                SET q.from_name = $from_name,
                                    q.to_name = $to_name,
                                    q.created_at = datetime(),
                                    q.confidence = $confidence,
                                    q.source_snippet = $source_snippet
                                WITH q
                                MATCH (e:Experience {id: $exp_id})
                                MERGE (q)-[:EXTRACTED_FROM]->(e)
                                """,
                                reason="low_quality",
                                type=q.get("type"),
                                from_name=q.get("from_name"),
                                to_name=q.get("to_name"),
                                confidence=float(q.get("properties", {}).get("confidence", 0.0))
                                if isinstance(q.get("properties"), dict)
                                else 0.0,
                                source_snippet=(
                                    q.get("properties", {}).get("source_snippet")
                                    if isinstance(q.get("properties"), dict)
                                    else None
                                ),
                                exp_id=experience_id,
                            )
                        await tx.commit()
                    finally:
                        await tx.close()
            except Exception:
                pass

        insights = extracted_data.get("insights", [])
        if insights:
            try:
                insights_text = "\n".join(
                    [
                        f"- {ins.get('text')} (conf: {ins.get('confidence', 0.5)})"
                        for ins in insights[:5]  # Limita a 5 insights
                    ]
                )

                await db.query(
                    """
                    MATCH (e:Experience {id: $exp_id})
                    SET e.insights = $insights_text
                    """,
                    params={"exp_id": experience_id, "insights_text": insights_text},
                    operation="store_insights",
                )
            except Exception as e:
                logger.error(f"Erro ao armazenar insights: {e}")

        return entities_created, relationships_created

    @resilient(
        max_attempts=3,
        initial_backoff=2.0,
        max_backoff=10.0,
        circuit_breaker=_consolidation_cb,
        retry_on=(Exception,),
        operation_name="knowledge_consolidation",
    )
    async def consolidate_experience(
        self, experience_id: str, experience_content: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Consolida uma experiência episódica em conhecimento semântico.
        """
        await self._initialize()
        start = time.perf_counter()

        # 1) Salvar na memória episódica (Qdrant), com robustez do MemoryCore
        try:
            db = await get_memory_db()
            exp_type = str((metadata or {}).get("type") or "knowledge_event")
            exp = Experience(
                id=experience_id, type=exp_type, content=experience_content, metadata=metadata
            )
            await db.amemorize(exp)
        except Exception:
            logger.debug("Falha ao salvar experiência na memória episódica", exc_info=True)

        # 2) Chunking do conteúdo para extração por partes
        chunk_size = int(getattr(settings, "CONSOLIDATION_CHUNK_SIZE", 2000))
        overlap = int(getattr(settings, "CONSOLIDATION_CHUNK_OVERLAP", 200))
        chunks = self._chunk_text(experience_content, chunk_size=chunk_size, overlap=overlap)

        total_entities = 0
        total_rels = 0
        total_insights = 0

        try:
            for idx, chunk in enumerate(chunks):
                # Enriquecer metadata com info de chunk
                md = dict(metadata or {})
                md["chunk_index"] = idx
                md["chunk_total"] = len(chunks)
                extracted = await self._extract_knowledge_with_llm(chunk, md)
                num_entities, num_rels = await self._persist_to_neo4j(experience_id, extracted, md)
                total_entities += num_entities
                total_rels += num_rels
                total_insights += len(extracted.get("insights", []))

            elapsed = time.perf_counter() - start
            result = {
                "experience_id": experience_id,
                "entities_created": total_entities,
                "relationships_created": total_rels,
                "insights_count": total_insights,
                "elapsed_seconds": elapsed,
                "status": "success",
            }
            CONSOLIDATION_COUNTER.labels("success", "").inc()
            CONSOLIDATION_LATENCY.labels("success").observe(elapsed)
            logger.info(
                f"Consolidação concluída para experiência {experience_id}: "
                f"{total_entities} entidades, {total_rels} relacionamentos em {elapsed:.2f}s"
            )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            CONSOLIDATION_COUNTER.labels("error", type(e).__name__).inc()
            CONSOLIDATION_LATENCY.labels("error").observe(elapsed)
            logger.error(f"Erro na consolidação da experiência {experience_id}: {e}", exc_info=True)
            raise

    async def consolidate_batch(self, limit: int = 10, min_score: float = 0.0) -> dict[str, Any]:
        """
        Consolida um lote de experiências da memória episódica.
        """
        await self._initialize()

        if not self.qdrant_client:
            raise ValueError("Cliente Qdrant não disponível para consolidação.")

        start_time = time.perf_counter()
        stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "total_entities": 0,
            "total_relationships": 0,
            "elapsed_seconds": 0.0,
        }

        offset = None

        try:
            while stats["total_processed"] < limit:
                remaining = limit - stats["total_processed"]
                logger.info(f"Buscando até {remaining} experiências para consolidação...")
                scroll_result = await self.qdrant_client.scroll(
                    collection_name=settings.QDRANT_COLLECTION_EPISODIC,
                    limit=remaining,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset,
                )
                if isinstance(scroll_result, tuple):
                    points = scroll_result[0]
                    offset = scroll_result[1]
                else:
                    points = getattr(scroll_result, "points", [])
                    offset = getattr(scroll_result, "next_page_offset", None)
                if not points:
                    break
                logger.info(f"Encontradas {len(points)} experiências para consolidar.")
                for point in points:
                    if stats["total_processed"] >= limit:
                        break
                    stats["total_processed"] += 1
                    try:
                        exp_id = str(point.id)
                        raw_content = point.payload.get("content", "")
                        try:
                            content = decrypt_text(raw_content, point.payload.get("metadata"))
                        except Exception as e:
                            logger.warning(
                                f"Failed to decrypt experience {exp_id}: {e}. Using raw content."
                            )
                            content = raw_content
                        if not content or len(content.strip()) < 10:
                            logger.debug(f"Ignorando experiência {exp_id} (conteúdo vazio).")
                            continue
                        already_consolidated = await self._check_if_consolidated(exp_id)
                        if already_consolidated:
                            logger.debug(f"Experiência {exp_id} já consolidada. Pulando.")
                            continue
                        metadata = {k: v for k, v in point.payload.items() if k != "content"}
                        result = await self.consolidate_experience(exp_id, content, metadata)
                        stats["successful"] += 1
                        stats["total_entities"] += result.get("entities_created", 0)
                        stats["total_relationships"] += result.get("relationships_created", 0)
                    except Exception as e:
                        stats["failed"] += 1
                        logger.error(f"Falha ao consolidar experiência {point.id}: {e}")
                        continue
                if not offset:
                    break
            stats["elapsed_seconds"] = time.perf_counter() - start_time
            logger.info(
                f"Consolidação em lote concluída: {stats['successful']}/{stats['total_processed']} "
                f"experiências consolidadas em {stats['elapsed_seconds']:.2f}s"
            )
            return stats
        except Exception as e:
            logger.error(f"Erro na consolidação em lote: {e}", exc_info=True)
            stats["elapsed_seconds"] = time.perf_counter() - start_time
            raise

    async def _check_if_consolidated(self, experience_id: str) -> bool:
        """Verifica se uma experiência já foi consolidada no Neo4j."""
        try:
            db = await get_graph_db()
            result = await db.query(
                """
                MATCH (e:Experience {id: $exp_id})
                RETURN e.consolidated_at IS NOT NULL AS consolidated
                """,
                params={"exp_id": experience_id},
                operation="check_consolidated",
            )
            return result[0].get("consolidated", False) if result else False
        except Exception as e:
            logger.warning(f"Erro ao verificar consolidação: {e}")
            return False

    async def consolidate_document(
        self, user_id: str, doc_id: str, limit: int = 50
    ) -> dict[str, Any]:
        await self._initialize()
        start_time = time.perf_counter()
        try:
            client = get_async_qdrant_client()
        except Exception as e:
            raise ValueError(f"Cliente Qdrant não disponível: {e}")

        try:
            from qdrant_client import models as _models

            qfilter = _models.Filter(
                must=[
                    _models.FieldCondition(
                        key="metadata.user_id", match=_models.MatchValue(value=user_id)
                    ),
                    _models.FieldCondition(
                        key="metadata.doc_id", match=_models.MatchValue(value=doc_id)
                    ),
                    _models.FieldCondition(
                        key="metadata.type", match=_models.MatchValue(value="doc_chunk")
                    ),
                ]
            )
        except Exception:
            qfilter = None

        coll_name = f"user_{user_id}"
        try:
            scroll_result = await client.scroll(
                collection_name=coll_name,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                filter=qfilter,
            )  # type: ignore
            points = (
                scroll_result[0]
                if isinstance(scroll_result, tuple)
                else getattr(scroll_result, "points", [])
            )
        except Exception as e:
            raise ValueError(f"Falha ao obter chunks do documento: {e}")

        entities_total = 0
        relationships_total = 0

        db = await get_graph_db()
        # Cria nó do Document
        try:
            await db.query(
                """
                MERGE (d:Document {id: $doc_id})
                SET d.file_name = $file_name,
                    d.user_id = $user_id,
                    d.discovered_at = datetime()
                """,
                params={
                    "doc_id": doc_id,
                    "file_name": points[0].payload.get("metadata", {}).get("file_name")
                    if points
                    else None,
                    "user_id": user_id,
                },
                operation="create_document_node",
            )
        except Exception:
            pass

        for p in points:
            payload = getattr(p, "payload", {}) or {}
            meta = payload.get("metadata") or {}
            content = payload.get("content") or ""
            if not content:
                continue
            md = dict(meta)
            md["source"] = "document_chunk"
            md["chunk_id"] = str(p.id)
            extracted = await self._extract_knowledge_with_llm(content, md)

            # Normaliza entidades
            normalized_entities = []
            for entity in extracted.get("entities", []):
                if not entity.get("name"):
                    continue
                try:
                    ne = graph_guardian.validate_and_normalize_entity(
                        name=entity["name"],
                        entity_type=entity.get("type", "CONCEPT"),
                        properties=entity.get("properties", {}),
                    )
                    props = ne["properties"]
                    props["original_name"] = ne.get("original_name", ne["name"])
                    normalized_entities.append(
                        {"name": ne["name"], "type": ne["type"], "properties": props}
                    )
                except Exception:
                    continue

            # Persiste entidades e MENTIONS a partir de Document
            if normalized_entities:
                try:
                    async with await db.get_session() as session:
                        tx = await session.begin_transaction()
                        from collections import defaultdict

                        groups = defaultdict(list)
                        for ne in normalized_entities:
                            groups[ne["type"]].append(ne)
                        try:
                            await db.register_relationship_type(tx, "MENTIONS")
                        except Exception:
                            pass
                        for label, batch in groups.items():
                            await tx.run(
                                f"""
                                UNWIND $batch AS ent
                                MERGE (n:{label} {{name: ent.name}})
                                SET n += ent.properties,
                                    n.last_seen = datetime()
                                WITH n
                                MATCH (d:Document {{id: $doc_id}})
                                MERGE (d)-[:MENTIONS]->(n)
                                """,
                                batch=batch,
                                doc_id=doc_id,
                            )
                            entities_total += len(batch)
                        await tx.commit()
                except Exception:
                    pass

            # Normaliza e persiste relacionamentos entre entidades
            normalized_rels = []
            for rel in extracted.get("relationships", []):
                if not rel.get("from") or not rel.get("to"):
                    continue
                try:
                    nr = graph_guardian.validate_and_normalize_relationship(
                        from_entity=rel["from"],
                        to_entity=rel["to"],
                        rel_type=rel.get("type", "RELATES_TO"),
                        properties=rel.get("properties", {}),
                    )
                    if nr is None:
                        continue
                    props = nr["properties"]
                    props["source_chunk"] = str(p.id)
                    normalized_rels.append(
                        {
                            "from_name": nr["from"],
                            "to_name": nr["to"],
                            "type": nr["type"],
                            "properties": props,
                        }
                    )
                except Exception:
                    continue

            if normalized_rels:
                try:
                    async with await db.get_session() as session:
                        tx = await session.begin_transaction()
                        from collections import defaultdict

                        groups = defaultdict(list)
                        for nr in normalized_rels:
                            groups[nr["type"]].append(nr)
                        for rel_type, batch in groups.items():
                            try:
                                await db.register_relationship_type(tx, rel_type)
                            except Exception:
                                pass
                            await tx.run(
                                f"""
                                UNWIND $batch AS rel
                                MATCH (a {{name: rel.from_name}})
                                MATCH (b {{name: rel.to_name}})
                                MERGE (a)-[r:{rel_type}]->(b)
                                SET r += rel.properties,
                                    r.discovered_at = datetime(),
                                    r.source_document = $doc_id
                                """,
                                batch=batch,
                                doc_id=doc_id,
                            )
                            relationships_total += len(batch)
                        await tx.commit()
                except Exception:
                    pass

        elapsed = time.perf_counter() - start_time
        return {
            "doc_id": doc_id,
            "entities_created": entities_total,
            "relationships_created": relationships_total,
            "elapsed_seconds": elapsed,
            "status": "success",
        }


# Instância global
knowledge_consolidator = KnowledgeConsolidator()
