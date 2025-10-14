import asyncio
import logging
from typing import Set

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.async_unit_of_work import AsyncTransaction
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

# --- Métricas e Circuit Breaker ---
_DB_QUERIES = Counter("neo4j_queries_total", "Total de queries ao Neo4j", ["operation", "outcome"])
_DB_LATENCY = Histogram("neo4j_query_latency_seconds", "Latência por query ao Neo4j", ["operation"])
_DB_CB = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

class GraphDatabase:
    _driver: AsyncDriver | None = None
    _driver_lock = asyncio.Lock()
    _ontology_lock = asyncio.Lock()
    _known_relationship_types: Set[str] = set()

    async def get_driver(self) -> AsyncDriver:
        if self._driver is not None:
            return self._driver

        async with self._driver_lock:
            if self._driver is None:
                logger.info("Criando novo driver Neo4j...")
                try:
                    password = settings.NEO4J_PASSWORD.get_secret_value()
                    self._driver = AsyncGraphDatabase.driver(
                        settings.NEO4J_URI, auth=(settings.NEO4J_USER, password)
                    )
                    await self._driver.verify_connectivity()
                    await self._initialize_ontology()
                    logger.info("Driver Neo4j criado e ontologia inicializada.")
                except Exception as e:
                    logger.critical(f"FATAL: Não foi possível criar o driver Neo4j: {e}", exc_info=True)
                    raise ConnectionError(f"Falha ao conectar ao Neo4j: {e}") from e
        return self._driver

    async def _initialize_ontology(self):
        driver = await self.get_driver()
        async with driver.session() as session:
            result = await session.run("MATCH (rt:RelationshipType) RETURN rt.name AS name")
            existing_types = {record["name"] async for record in result}
            self._known_relationship_types.update(existing_types)
            logger.info(
                f"Ontologia carregada. {len(self._known_relationship_types)} tipos de relacionamento conhecidos.")

    async def register_relationship_type(self, type_name: str, tx: AsyncTransaction):
        if type_name in self._known_relationship_types:
            return
        async with self._ontology_lock:
            if type_name in self._known_relationship_types:
                return
            logger.warning(f"Tipo de relacionamento desconhecido: '{type_name}'. Registrando dinamicamente...")
            await tx.run(
                "MERGE (rt:RelationshipType {name: $name}) SET rt.dynamically_added = true, rt.createdAt = timestamp()",
                name=type_name
            )
            self._known_relationship_types.add(type_name)
            logger.info(f"Novo tipo de relacionamento '{type_name}' registrado com sucesso.")

    async def merge_node(self, tx: AsyncTransaction, label: str, name: str) -> int:
        query = f"MERGE (n:{label} {{name: $name}}) RETURN id(n) as node_id"
        result = await tx.run(query, name=name)
        record = await result.single()
        return record["node_id"]

    async def merge_relationship(self, tx: AsyncTransaction, source_id: int, target_id: int, rel_type: str):
        await self.register_relationship_type(rel_type, tx)
        query = f"MATCH (a), (b) WHERE id(a) = $source_id AND id(b) = $target_id MERGE (a)-[:`{rel_type}`]->(b)"
        await tx.run(query, source_id=source_id, target_id=target_id)

    async def close(self):
        async with self._driver_lock:
            if self._driver:
                await self._driver.close()
                self._driver = None
                logger.info("Driver Neo4j fechado.")

    @resilient(operation_name="neo4j_query")
    async def query(self, cypher_query: str, params: dict = None):
        driver = await self.get_driver()
        async with driver.session() as session:
            result = await session.run(cypher_query, params or {})
            return [record.data() async for record in result]

    @resilient(operation_name="neo4j_execute")
    async def execute(self, cypher_query: str, params: dict = None):
        driver = await self.get_driver()
        async with driver.session() as session:
            await session.run(cypher_query, params or {})

    async def ahealth_check(self) -> bool:
        try:
            driver = await self.get_driver()
            await driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning(f"Health check do Neo4j falhou: {e}")
            return False

graph_db = GraphDatabase()
