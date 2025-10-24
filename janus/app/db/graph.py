import asyncio
import logging
from typing import Set, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, AsyncTransaction
from prometheus_client import Counter, Histogram
from fastapi import Depends

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker
from app.models.schemas import GraphRelationship

logger = logging.getLogger(__name__)

# --- Métricas e Circuit Breaker ---
_DB_QUERIES = Counter("neo4j_queries_total", "Total de queries ao Neo4j", ["operation", "outcome"])
_DB_LATENCY = Histogram("neo4j_query_latency_seconds", "Latência por query ao Neo4j", ["operation"])
_DB_CB = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

class GraphDatabase:
    """
    Gerencia a conexão e as operações com o banco de dados Neo4j.
    Instanciada como um singleton gerenciado pelo ciclo de vida da aplicação.
    """
    _driver: Optional[AsyncDriver] = None
    _ontology_lock = asyncio.Lock()
    _known_relationship_types: Set[str] = set()
    _offline: bool = False

    async def connect(self):
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value())
                )
                await self._initialize_ontology()
                logger.info("Conexão com Neo4j estabelecida.")
                self._offline = False
            except Exception as e:
                logger.warning("Neo4j indisponível; ativando modo offline.", exc_info=e)
                # Mantém driver como None e sinaliza modo offline
                self._driver = None
                self._offline = True

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def _initialize_ontology(self):
        async with self._ontology_lock:
            if not self._known_relationship_types and self._driver is not None:
                # Registra tipos básicos de relacionamento
                async with self._driver.session() as session:
                    await self.register_relationship_type(session, GraphRelationship.CONTAINS.value)
                    await self.register_relationship_type(session, GraphRelationship.CALLS.value)
                    await self.register_relationship_type(session, GraphRelationship.IS_SYNONYM_OF.value)
                    # Tipos adicionais (arestas tipificadas)
                    await self.register_relationship_type(session, GraphRelationship.IMPORTS.value)
                    await self.register_relationship_type(session, GraphRelationship.DEFINES.value)
                    await self.register_relationship_type(session, GraphRelationship.INHERITS_FROM.value)
                    await self.register_relationship_type(session, GraphRelationship.IMPLEMENTS.value)
                    await self.register_relationship_type(session, GraphRelationship.USES.value)
                    await self.register_relationship_type(session, GraphRelationship.IS_A.value)
                    await self.register_relationship_type(session, GraphRelationship.EXAMPLE_OF.value)
                    await self.register_relationship_type(session, GraphRelationship.PART_OF.value)
                    await self.register_relationship_type(session, GraphRelationship.DEPENDS_ON.value)
                    await self.register_relationship_type(session, GraphRelationship.ENABLES.value)
                    await self.register_relationship_type(session, GraphRelationship.PRODUCES.value)
                    await self.register_relationship_type(session, GraphRelationship.RESULTS_IN.value)
                    await self.register_relationship_type(session, GraphRelationship.RELATES_TO.value)
                    logger.info("Ontologia inicial do grafo registrada.")

    async def register_relationship_type(self, tx_or_session, rel_type: str):
        # Usa transação ou sessão para registrar um tipo de relacionamento
        if self._driver is None:
            return
        query = f"MERGE (t:RelationshipType {{name: $rel_type}})"
        await tx_or_session.run(query, rel_type=rel_type)
        self._known_relationship_types.add(rel_type)

    @resilient(operation_name="neo4j_query")
    async def query(self, cypher_query: str, params: dict = None, operation: str | None = None):
        op = operation or "query"
        # Offline: retorna vazio sem lançar exceção
        if self._driver is None or self._offline:
            try:
                _DB_QUERIES.labels(op, "failure").inc()
            except Exception:
                pass
            return []
        start = None
        try:
            start = asyncio.get_event_loop().time()
            async with self._driver.session() as session:
                result = await session.run(cypher_query, params or {})
                rows = [record.data() async for record in result]
                _DB_QUERIES.labels(op, "success").inc()
                if start is not None:
                    _DB_LATENCY.labels(op).observe(asyncio.get_event_loop().time() - start)
                return rows
        except Exception:
            _DB_QUERIES.labels(op, "failure").inc()
            if start is not None:
                _DB_LATENCY.labels(op).observe(asyncio.get_event_loop().time() - start)
            raise

    @resilient(operation_name="neo4j_execute")
    async def execute(self, cypher_query: str, params: dict = None, operation: str | None = None):
        op = operation or "execute"
        # Offline: no-op
        if self._driver is None or self._offline:
            try:
                _DB_QUERIES.labels(op, "failure").inc()
            except Exception:
                pass
            return None
        start = None
        try:
            start = asyncio.get_event_loop().time()
            async with self._driver.session() as session:
                await session.run(cypher_query, params or {})
                _DB_QUERIES.labels(op, "success").inc()
                if start is not None:
                    _DB_LATENCY.labels(op).observe(asyncio.get_event_loop().time() - start)
        except Exception:
            _DB_QUERIES.labels(op, "failure").inc()
            if start is not None:
                _DB_LATENCY.labels(op).observe(asyncio.get_event_loop().time() - start)
            raise

    async def merge_node(self, tx: AsyncTransaction, label: str, name: str) -> int:
        query = f"MERGE (n:{label} {{name: $name}}) RETURN id(n) as node_id"
        result = await tx.run(query, name=name)
        record = await result.single()
        return record["node_id"]

    async def merge_relationship(self, tx: AsyncTransaction, source_id: int, target_id: int, rel_type: str):
        await self.register_relationship_type(tx, rel_type)
        query = f"MATCH (a), (b) WHERE id(a) = $source_id AND id(b) = $target_id MERGE (a)-[:`{rel_type}`]->(b)"
        await tx.run(query, source_id=source_id, target_id=target_id)

    async def get_session(self) -> AsyncSession:
        if self._driver is None or self._offline:
            raise ConnectionError("Graph database em modo offline.")
        return self._driver.session()

    @resilient(operation_name="neo4j_health")
    async def health_check(self) -> bool:
        if self._driver is None or self._offline:
            return False
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as ok")
                record = await result.single()
                return bool(record and record.get("ok") == 1)
        except Exception as e:
            logger.warning(f"Neo4j health check falhou: {e}")
            return False

# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_graph_db_instance: Optional[GraphDatabase] = None

async def initialize_graph_db():
    """Inicializa a instância singleton do GraphDatabase."""
    global _graph_db_instance
    if _graph_db_instance is None:
        _graph_db_instance = GraphDatabase()
        await _graph_db_instance.connect()

async def close_graph_db():
    """Fecha a conexão da instância singleton."""
    if _graph_db_instance:
        await _graph_db_instance.close()

async def get_graph_db() -> GraphDatabase:
    """Função getter para injeção de dependência, retorna a instância singleton."""
    if _graph_db_instance is None:
        await initialize_graph_db()
    return _graph_db_instance


# --- Compatibilidade com código legado ---
# Exportar uma referência para a instância singleton (para imports legados)
# NOTA: Esta é uma referência que será None até initialize_graph_db() ser chamada
graph_db = _graph_db_instance
