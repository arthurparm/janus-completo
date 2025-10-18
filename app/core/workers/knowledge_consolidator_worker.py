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
from typing import Any, Dict, Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from prometheus_client import Counter, Histogram
from qdrant_client import QdrantClient

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker
from app.core.llm.llm_manager import ModelRole, ModelPriority, get_llm
from app.core.memory.memory_core import decrypt_text
from app.core.memory.graph_guardian import graph_guardian
from app.db.graph import get_graph_db
from app.db.vector_store import get_qdrant_client

logger = logging.getLogger(__name__)

# Métricas
CONSOLIDATION_COUNTER = Counter(
    "knowledge_consolidation_total",
    "Total de consolidações de conhecimento",
    ["outcome", "exception_type"]
)
CONSOLIDATION_LATENCY = Histogram(
    "knowledge_consolidation_latency_seconds",
    "Latência de consolidação de conhecimento",
    ["outcome"]
)
ENTITIES_EXTRACTED = Counter(
    "knowledge_entities_extracted_total",
    "Total de entidades extraídas"
)
RELATIONSHIPS_CREATED = Counter(
    "knowledge_relationships_created_total",
    "Total de relacionamentos criados no grafo"
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
        self.qdrant_client: Optional[QdrantClient] = None
        self.llm: Optional[BaseChatModel] = None
        self._initialized = False

    async def _initialize(self):
        """Inicializa componentes necessários."""
        if self._initialized:
            return

        try:
            # Cliente Qdrant
            self.qdrant_client = get_qdrant_client()
            logger.info("Cliente Qdrant inicializado para consolidação.")
        except Exception as e:
            logger.error(f"Falha ao inicializar cliente Qdrant: {e}")
            self.qdrant_client = None

        try:
            # LLM para extração
            self.llm = get_llm(
                role=ModelRole.KNOWLEDGE_CURATOR,
                priority=ModelPriority.FAST_AND_CHEAP
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

    async def _extract_knowledge_with_llm(
            self,
            experience_content: str,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            metadata=json.dumps(metadata, indent=2, ensure_ascii=False)[:500]
        )

        messages = [
            SystemMessage(content="Você é um especialista em extração de conhecimento."),
            HumanMessage(content=prompt_text)
        ]

        # Invoca LLM
        start = time.perf_counter()
        try:
            # Usa ainvoke se disponível, senão invoke
            if hasattr(self.llm, 'ainvoke'):
                response = await self.llm.ainvoke(messages)
            else:
                # Fallback síncrono
                response = await asyncio.to_thread(self.llm.invoke, messages)

            elapsed = time.perf_counter() - start
            logger.debug(f"Extração LLM concluída em {elapsed:.2f}s")

            # Parse JSON da resposta
            response_text = response.content if hasattr(response, 'content') else str(response)

            # Tenta extrair JSON da resposta (pode vir com markdown)
            response_text = response_text.strip()
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]

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
            self,
            experience_id: str,
            extracted_data: Dict[str, Any],
            source_metadata: Dict[str, Any]
    ) -> Tuple[int, int]:
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
                    "exp_type": source_metadata.get("type", "unknown")
                },
                operation="create_experience_node"
            )
        except Exception as e:
            logger.error(f"Erro ao criar nó de experiência: {e}")

        # Cria entidades (com normalização via Graph Guardian)
        for entity in extracted_data.get("entities", []):
            if not entity.get("name"):
                continue

            try:
                # GUARDIÃO DO GRAFO: Normaliza e valida entidade
                normalized_entity = graph_guardian.validate_and_normalize_entity(
                    name=entity["name"],
                    entity_type=entity.get("type", "CONCEPT"),
                    properties=entity.get("properties", {})
                )

                entity_name = normalized_entity["name"]
                entity_type = normalized_entity["type"]
                entity_props = normalized_entity["properties"]
                entity_props["original_name"] = normalized_entity.get("original_name", entity_name)
                await db.query(
                    f"""
                    MERGE (n:{entity_type} {{name: $name}})
                    SET n += $properties,
                        n.last_seen = datetime()
                    WITH n
                    MATCH (e:Experience {{id: $exp_id}})
                    MERGE (e)-[:MENTIONS]->(n)
                    """,
                    params={
                        "name": entity_name,
                        "properties": entity_props,
                        "exp_id": experience_id
                    },
                    operation="create_entity"
                )
                entities_created += 1
                ENTITIES_EXTRACTED.inc()
            except ValueError as ve:
                logger.warning(f"Entidade inválida ignorada: {entity.get('name')} - {ve}")
            except Exception as e:
                logger.error(f"Erro ao criar entidade {entity.get('name')}: {e}")

        # Cria relacionamentos (com normalização via Graph Guardian)
        for rel in extracted_data.get("relationships", []):
            if not rel.get("from") or not rel.get("to"):
                continue

            try:
                normalized_rel = graph_guardian.validate_and_normalize_relationship(
                    from_entity=rel["from"],
                    to_entity=rel["to"],
                    rel_type=rel.get("type", "RELATES_TO"),
                    properties=rel.get("properties", {})
                )
                if normalized_rel is None:
                    logger.debug(f"Relacionamento inválido ignorado: {rel}")
                    continue
                from_name = normalized_rel["from"]
                to_name = normalized_rel["to"]
                rel_type = normalized_rel["type"]
                rel_props = normalized_rel["properties"]
                rel_props["original_from"] = normalized_rel.get("original_from", from_name)
                rel_props["original_to"] = normalized_rel.get("original_to", to_name)
                await db.query(
                    f"""
                    MATCH (a {{name: $from_name}})
                    MATCH (b {{name: $to_name}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r += $properties,
                        r.discovered_at = datetime(),
                        r.source_experience = $exp_id
                    """,
                    params={
                        "from_name": from_name,
                        "to_name": to_name,
                        "properties": rel_props,
                        "exp_id": experience_id
                    },
                    operation="create_relationship"
                )
                relationships_created += 1
                RELATIONSHIPS_CREATED.inc()
            except Exception as e:
                logger.error(
                    f"Erro ao criar relacionamento {rel.get('from')} -> {rel.get('to')}: {e}"
                )

        insights = extracted_data.get("insights", [])
        if insights:
            try:
                insights_text = "\n".join([
                    f"- {ins.get('text')} (conf: {ins.get('confidence', 0.5)})"
                    for ins in insights[:5]  # Limita a 5 insights
                ])

                await db.query(
                    """
                    MATCH (e:Experience {id: $exp_id})
                    SET e.insights = $insights_text
                    """,
                    params={
                        "exp_id": experience_id,
                        "insights_text": insights_text
                    },
                    operation="store_insights"
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
        operation_name="knowledge_consolidation"
    )
    async def consolidate_experience(
            self,
            experience_id: str,
            experience_content: str,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Consolida uma experiência episódica em conhecimento semântico.
        """
        start = time.perf_counter()

        try:
            extracted = await self._extract_knowledge_with_llm(experience_content, metadata)
            num_entities, num_rels = await self._persist_to_neo4j(
                experience_id,
                extracted,
                metadata
            )
            elapsed = time.perf_counter() - start
            result = {
                "experience_id": experience_id,
                "entities_created": num_entities,
                "relationships_created": num_rels,
                "insights_count": len(extracted.get("insights", [])),
                "elapsed_seconds": elapsed,
                "status": "success"
            }
            CONSOLIDATION_COUNTER.labels("success", "").inc()
            CONSOLIDATION_LATENCY.labels("success").observe(elapsed)
            logger.info(
                f"Consolidação concluída para experiência {experience_id}: "
                f"{num_entities} entidades, {num_rels} relacionamentos em {elapsed:.2f}s"
            )
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start
            CONSOLIDATION_COUNTER.labels("error", type(e).__name__).inc()
            CONSOLIDATION_LATENCY.labels("error").observe(elapsed)
            logger.error(
                f"Erro na consolidação da experiência {experience_id}: {e}",
                exc_info=True
            )
            raise

    async def consolidate_batch(
            self,
            limit: int = 10,
            min_score: float = 0.0
    ) -> Dict[str, Any]:
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
            "elapsed_seconds": 0.0
        }

        try:
            logger.info(f"Buscando até {limit} experiências para consolidação...")
            scroll_result = self.qdrant_client.scroll(
                collection_name=settings.QDRANT_COLLECTION_EPISODIC,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            points, _ = scroll_result
            logger.info(f"Encontradas {len(points)} experiências para consolidar.")
            for point in points:
                stats["total_processed"] += 1
                try:
                    exp_id = str(point.id)
                    raw_content = point.payload.get("content", "")
                    try:
                        content = decrypt_text(raw_content, point.payload.get("metadata"))
                    except Exception as e:
                        logger.warning(f"Failed to decrypt experience {exp_id}: {e}. Using raw content.")
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
                operation="check_consolidated"
            )
            return result[0].get("consolidated", False) if result else False
        except Exception as e:
            logger.warning(f"Erro ao verificar consolidação: {e}")
            return False


# Instância global
knowledge_consolidator = KnowledgeConsolidator()
