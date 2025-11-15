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
                    await self.register_relationship_type(session, GraphRelationship.MENTIONS.value)
                    await self.register_relationship_type(session, GraphRelationship.CAUSES.value)
                    await self.register_relationship_type(session, GraphRelationship.SOLVES.value)
                    await self.register_relationship_type(session, GraphRelationship.CAUSED_BY.value)
                    await self.register_relationship_type(session, GraphRelationship.SOLVED_BY.value)
                    await self.register_relationship_type(session, GraphRelationship.HAS_PROPERTY.value)
                    await self.register_relationship_type(session, GraphRelationship.SIMILAR_TO.value)
                    await self.register_relationship_type(session, GraphRelationship.FOLLOWED_BY.value)
                    await self.register_relationship_type(session, GraphRelationship.EXTRACTED_FROM.value)
                    try:
                        await session.run("CREATE CONSTRAINT experience_id_unique IF NOT EXISTS FOR (e:Experience) REQUIRE e.id IS UNIQUE")
                        await session.run("CREATE CONSTRAINT reltype_name_unique IF NOT EXISTS FOR (t:RelationshipType) REQUIRE t.name IS UNIQUE")
                        await session.run("CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.name)")
                        await session.run("CREATE INDEX technology_name_idx IF NOT EXISTS FOR (t:Technology) ON (t.name)")
                        await session.run("CREATE INDEX tool_name_idx IF NOT EXISTS FOR (t:Tool) ON (t.name)")
                        await session.run("CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name)")
                        await session.run("CREATE INDEX error_name_idx IF NOT EXISTS FOR (e:Error) ON (e.name)")
                        await session.run("CREATE INDEX solution_name_idx IF NOT EXISTS FOR (s:Solution) ON (s.name)")
                        await session.run("CREATE INDEX pattern_name_idx IF NOT EXISTS FOR (p:Pattern) ON (p.name)")
                        await session.run("CREATE INDEX function_name_idx IF NOT EXISTS FOR (f:Function) ON (f.name)")
                        await session.run("CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name)")
                        await session.run("CREATE INDEX function_name_file_idx IF NOT EXISTS FOR (f:Function) ON (f.name, f.file_path)")
                        await session.run("CREATE INDEX class_name_file_idx IF NOT EXISTS FOR (c:Class) ON (c.name, c.file_path)")
                        await session.run("CREATE INDEX file_path_idx IF NOT EXISTS FOR (f:File) ON (f.path)")
                        await session.run("CREATE INDEX codefile_path_idx IF NOT EXISTS FOR (f:CodeFile) ON (f.path)")
                        await session.run("CREATE INDEX experience_consolidated_at_idx IF NOT EXISTS FOR (e:Experience) ON (e.consolidated_at)")
                    except Exception:
                        try:
                            await session.run("CREATE CONSTRAINT ON (e:Experience) ASSERT e.id IS UNIQUE")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE CONSTRAINT ON (t:RelationshipType) ASSERT t.name IS UNIQUE")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Concept(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Technology(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Tool(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Person(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Error(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Solution(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Pattern(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Function(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Class(name)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Function(name, file_path)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Class(name, file_path)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :File(path)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :CodeFile(path)")
                        except Exception:
                            pass
                        try:
                            await session.run("CREATE INDEX ON :Experience(consolidated_at)")
                        except Exception:
                            pass
                    logger.info("Ontologia inicial do grafo registrada.")

    async def register_relationship_type(self, tx_or_session, rel_type: str):
        # Usa transação ou sessão para registrar um tipo de relacionamento
        if self._driver is None:
            return
        query = f"MERGE (t:RelationshipType {{name: $rel_type}})"
        await tx_or_session.run(query, rel_type=rel_type)
        self._known_relationship_types.add(rel_type)

    @resilient(
        operation_name="neo4j_query",
        circuit_breaker=_DB_CB,
        max_attempts=int(getattr(settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
        initial_backoff=float(getattr(settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
        max_backoff=float(getattr(settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
    )
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
            from app.core.monitoring.health_monitor import get_timeout_recommendation, record_latency
            start = asyncio.get_event_loop().time()
            async with self._driver.session() as session:
                _timeout = get_timeout_recommendation("neo4j_query", float(getattr(settings, "NEO4J_DEFAULT_TIMEOUT_SECONDS", 30) or 30))
                result = await asyncio.wait_for(session.run(cypher_query, params or {}), timeout=float(_timeout))
                rows = [record.data() async for record in result]
                _DB_QUERIES.labels(op, "success").inc()
                if start is not None:
                    _elapsed = asyncio.get_event_loop().time() - start
                    _DB_LATENCY.labels(op).observe(_elapsed)
                    try:
                        record_latency("neo4j_query", _elapsed)
                    except Exception:
                        pass
                return rows
        except Exception:
            _DB_QUERIES.labels(op, "failure").inc()
            if start is not None:
                _elapsed = asyncio.get_event_loop().time() - start
                _DB_LATENCY.labels(op).observe(_elapsed)
                try:
                    from app.core.monitoring.health_monitor import record_latency
                    record_latency("neo4j_query", _elapsed)
                except Exception:
                    pass
            raise

    @resilient(
        operation_name="neo4j_execute",
        circuit_breaker=_DB_CB,
        max_attempts=int(getattr(settings, "LLM_RETRY_MAX_ATTEMPTS", 3) or 3),
        initial_backoff=float(getattr(settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5) or 0.5),
        max_backoff=float(getattr(settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0) or 5.0),
    )
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
            from app.core.monitoring.health_monitor import get_timeout_recommendation, record_latency
            start = asyncio.get_event_loop().time()
            async with self._driver.session() as session:
                _timeout = get_timeout_recommendation("neo4j_query", float(getattr(settings, "NEO4J_DEFAULT_TIMEOUT_SECONDS", 30) or 30))
                await asyncio.wait_for(session.run(cypher_query, params or {}), timeout=float(_timeout))
                _DB_QUERIES.labels(op, "success").inc()
                if start is not None:
                    _elapsed = asyncio.get_event_loop().time() - start
                    _DB_LATENCY.labels(op).observe(_elapsed)
                    try:
                        record_latency("neo4j_query", _elapsed)
                    except Exception:
                        pass
        except Exception:
            _DB_QUERIES.labels(op, "failure").inc()
            if start is not None:
                _elapsed = asyncio.get_event_loop().time() - start
                _DB_LATENCY.labels(op).observe(_elapsed)
                try:
                    from app.core.monitoring.health_monitor import record_latency
                    record_latency("neo4j_query", _elapsed)
                except Exception:
                    pass
            raise

    async def merge_node(self, tx: AsyncTransaction, label: str, name: str) -> int:
        query = f"MERGE (n:{label} {{name: $name}}) RETURN id(n) as node_id"
        start = asyncio.get_event_loop().time()
        result = await tx.run(query, name=name)
        record = await result.single()
        try:
            _DB_QUERIES.labels("merge_node", "success").inc()
            _DB_LATENCY.labels("merge_node").observe(asyncio.get_event_loop().time() - start)
        except Exception:
            pass
        return record["node_id"]

    async def merge_relationship(self, tx: AsyncTransaction, source_id: int, target_id: int, rel_type: str):
        await self.register_relationship_type(tx, rel_type)
        query = f"MATCH (a), (b) WHERE id(a) = $source_id AND id(b) = $target_id MERGE (a)-[:`{rel_type}`]->(b)"
        start = asyncio.get_event_loop().time()
        await tx.run(query, source_id=source_id, target_id=target_id)
        try:
            _DB_QUERIES.labels("merge_rel", "success").inc()
            _DB_LATENCY.labels("merge_rel").observe(asyncio.get_event_loop().time() - start)
        except Exception:
            pass

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
