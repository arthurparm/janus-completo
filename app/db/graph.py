import asyncio
import logging
from typing import Set, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.async_unit_of_work import AsyncTransaction
from prometheus_client import Counter, Histogram
from fastapi import Depends

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker
from app.models.schemas import GraphRelationship  # Importa o Enum

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

    async def connect(self):
        """Estabelece a conexão com o banco de dados."""
        if self._driver:
            return
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

    async def close(self):
        """Fecha a conexão com o banco de dados."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Driver Neo4j fechado.")

    async def _initialize_ontology(self):
        async with self._driver.session() as session:
            result = await session.run("MATCH (rt:RelationshipType) RETURN rt.name AS name")
            existing_types = {record["name"] async for record in result}
            self._known_relationship_types.update(existing_types)
            logger.info(
                f"Ontologia carregada. {len(self._known_relationship_types)} tipos de relacionamento conhecidos.")

    async def register_relationship_type(self, tx: AsyncTransaction, type_name: str):
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

    @resilient(operation_name="neo4j_query")
    async def query(self, cypher_query: str, params: dict = None):
        async with self._driver.session() as session:
            result = await session.run(cypher_query, params or {})
            return [record.data() async for record in result]

    @resilient(operation_name="neo4j_execute")
    async def execute(self, cypher_query: str, params: dict = None):
        async with self._driver.session() as session:
            await session.run(cypher_query, params or {})

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
        return self._driver.session()


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
