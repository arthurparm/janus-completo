import asyncio
import structlog
import re
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession, AsyncTransaction
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.infrastructure.resilience import CircuitBreaker, resilient
from app.models.schemas import GraphRelationship

logger = structlog.get_logger(__name__)

# --- Métricas e Circuit Breaker ---
_DB_QUERIES = Counter("neo4j_queries_total", "Total de queries ao Neo4j", ["operation", "outcome"])
_DB_LATENCY = Histogram("neo4j_query_latency_seconds", "Latência por query ao Neo4j", ["operation"])
_DB_CB = CircuitBreaker(failure_threshold=5, recovery_timeout=30)


class GraphDatabase:
    """
    Gerencia a conexão e as operações com o banco de dados Neo4j.
    Instanciada como um singleton gerenciado pelo ciclo de vida da aplicação.
    """

    _driver: AsyncDriver | None = None
    _ontology_lock = asyncio.Lock()
    _known_relationship_types: set[str] = set()
    _offline: bool = False

    async def connect(self):
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
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

    async def _get_existing_schema(self, session) -> set[str]:
        """Retorna conjunto de nomes de índices e constraints existentes."""
        names = set()
        try:
            # Tenta listar índices (Neo4j 4.3+)
            result = await session.run("SHOW INDEXES YIELD name RETURN name")
            async for record in result:
                if record["name"]:
                    names.add(record["name"])
            
            # Tenta listar constraints
            result = await session.run("SHOW CONSTRAINTS YIELD name RETURN name")
            async for record in result:
                if record["name"]:
                    names.add(record["name"])
        except Exception:
            # Ignora erros (versões antigas ou falta de permissão)
            pass
        return names

    async def _initialize_ontology(self):
        async with self._ontology_lock:
            if not self._known_relationship_types and self._driver is not None:
                # Registra tipos básicos de relacionamento
                async with self._driver.session() as session:
                    # Carrega esquema existente para evitar notificações desnecessárias
                    existing_schema = await self._get_existing_schema(session)

                    await self.register_relationship_type(session, GraphRelationship.CONTAINS.value)
                    await self.register_relationship_type(session, GraphRelationship.CALLS.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.IS_SYNONYM_OF.value
                    )
                    # Tipos adicionais (arestas tipificadas)
                    await self.register_relationship_type(session, GraphRelationship.IMPORTS.value)
                    await self.register_relationship_type(session, GraphRelationship.DEFINES.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.INHERITS_FROM.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.IMPLEMENTS.value
                    )
                    await self.register_relationship_type(session, GraphRelationship.USES.value)
                    await self.register_relationship_type(session, GraphRelationship.IS_A.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.EXAMPLE_OF.value
                    )
                    await self.register_relationship_type(session, GraphRelationship.PART_OF.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.DEPENDS_ON.value
                    )
                    await self.register_relationship_type(session, GraphRelationship.ENABLES.value)
                    await self.register_relationship_type(session, GraphRelationship.PRODUCES.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.RESULTS_IN.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.RELATES_TO.value
                    )
                    await self.register_relationship_type(session, GraphRelationship.MENTIONS.value)
                    await self.register_relationship_type(session, GraphRelationship.CAUSES.value)
                    await self.register_relationship_type(session, GraphRelationship.SOLVES.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.CAUSED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.SOLVED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.HAS_PROPERTY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.SIMILAR_TO.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.FOLLOWED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.EXTRACTED_FROM.value
                    )

                    # JARVIS / Agentic Relationships
                    await self.register_relationship_type(session, GraphRelationship.HAS_GOAL.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.HAS_PREFERENCE.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.IMPLEMENTED_BY.value
                    )
                    await self.register_relationship_type(session, GraphRelationship.EXECUTES.value)
                    await self.register_relationship_type(session, GraphRelationship.NEXT.value)
                    await self.register_relationship_type(session, GraphRelationship.TRUSTS.value)
                    await self.register_relationship_type(
                        session, GraphRelationship.BLOCKED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.COMPLETED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.CREATED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.MODIFIED_BY.value
                    )
                    await self.register_relationship_type(
                        session, GraphRelationship.RESULTS_IN.value
                    )

                    try:
                        # Vector Index for Hybrid Search
                        # Neo4j 5.11+ required
                        try:
                            # 1. Vector Indexes (One per key label)
                            # Concept
                            if "concept_embeddings" not in existing_schema:
                                await session.run(
                                    """
                                    CREATE VECTOR INDEX concept_embeddings IF NOT EXISTS
                                    FOR (n:Concept) ON (n.embedding)
                                    OPTIONS {indexConfig: {
                                        `vector.dimensions`: 1536,
                                        `vector.similarity_function`: 'cosine'
                                    }}
                                    """
                                )
                            # Technology
                            if "technology_embeddings" not in existing_schema:
                                await session.run(
                                    """
                                    CREATE VECTOR INDEX technology_embeddings IF NOT EXISTS
                                    FOR (n:Technology) ON (n.embedding)
                                    OPTIONS {indexConfig: {
                                        `vector.dimensions`: 1536,
                                        `vector.similarity_function`: 'cosine'
                                    }}
                                    """
                                )
                            # Tool
                            if "tool_embeddings" not in existing_schema:
                                await session.run(
                                    """
                                    CREATE VECTOR INDEX tool_embeddings IF NOT EXISTS
                                    FOR (n:Tool) ON (n.embedding)
                                    OPTIONS {indexConfig: {
                                        `vector.dimensions`: 1536,
                                        `vector.similarity_function`: 'cosine'
                                    }}
                                    """
                                )
                            # Pattern
                            if "pattern_embeddings" not in existing_schema:
                                await session.run(
                                    """
                                    CREATE VECTOR INDEX pattern_embeddings IF NOT EXISTS
                                    FOR (n:Pattern) ON (n.embedding)
                                    OPTIONS {indexConfig: {
                                        `vector.dimensions`: 1536,
                                        `vector.similarity_function`: 'cosine'
                                    }}
                                    """
                                )

                            # 2. Universal Full-Text Index (Lexical Search)
                            if "keyword_search" not in existing_schema:
                                await session.run(
                                    """
                                    CREATE FULLTEXT INDEX keyword_search IF NOT EXISTS
                                    FOR (n:Concept|Technology|Tool|Pattern|Solution|Error|Person)
                                    ON EACH [n.name, n.description, n.summary]
                                    """
                                )

                            logger.info(
                                "Índices Vetoriais e Full-Text (Universal) verificados."
                            )
                        except Exception as e:
                            logger.warning("log_warning", message=f"Falha ao criar índices avançados (Vector/FullText): {e}"
                            )

                        # Core Constraints
                        if "experience_id_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT experience_id_unique IF NOT EXISTS FOR (e:Experience) REQUIRE e.id IS UNIQUE"
                            )
                        if "reltype_name_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT reltype_name_unique IF NOT EXISTS FOR (t:RelationshipType) REQUIRE t.name IS UNIQUE"
                            )
                        if "concept_name_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE"
                            )

                        # JARVIS Constraints & Indexes
                        if "user_name_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT user_name_unique IF NOT EXISTS FOR (u:User) REQUIRE u.name IS UNIQUE"
                            )
                        if "goal_id_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT goal_id_unique IF NOT EXISTS FOR (g:Goal) REQUIRE g.id IS UNIQUE"
                            )
                        if "episode_id_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT episode_id_unique IF NOT EXISTS FOR (e:Episode) REQUIRE e.id IS UNIQUE"
                            )
                        if "action_id_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT action_id_unique IF NOT EXISTS FOR (a:Action) REQUIRE a.id IS UNIQUE"
                            )
                        if "plan_id_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT plan_id_unique IF NOT EXISTS FOR (p:Plan) REQUIRE p.id IS UNIQUE"
                            )
                        if "episode_timestamp_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX episode_timestamp_idx IF NOT EXISTS FOR (e:Episode) ON (e.timestamp)"
                            )

                        if "file_path_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE"
                            )
                        if "codefile_path_unique" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT codefile_path_unique IF NOT EXISTS FOR (f:CodeFile) REQUIRE f.path IS UNIQUE"
                            )
                        if "function_node_key" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT function_node_key IF NOT EXISTS FOR (f:Function) REQUIRE (f.name, f.file_path) IS UNIQUE"
                            )
                        if "class_node_key" not in existing_schema:
                            await session.run(
                                "CREATE CONSTRAINT class_node_key IF NOT EXISTS FOR (c:Class) REQUIRE (c.name, c.file_path) IS UNIQUE"
                            )
                        
                        # Indexes
                        if "concept_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.name)"
                            )
                        if "technology_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX technology_name_idx IF NOT EXISTS FOR (t:Technology) ON (t.name)"
                            )
                        if "tool_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX tool_name_idx IF NOT EXISTS FOR (t:Tool) ON (t.name)"
                            )
                        if "person_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name)"
                            )
                        if "error_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX error_name_idx IF NOT EXISTS FOR (e:Error) ON (e.name)"
                            )
                        if "solution_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX solution_name_idx IF NOT EXISTS FOR (s:Solution) ON (s.name)"
                            )
                        if "pattern_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX pattern_name_idx IF NOT EXISTS FOR (p:Pattern) ON (p.name)"
                            )
                        if "function_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX function_name_idx IF NOT EXISTS FOR (f:Function) ON (f.name)"
                            )
                        if "class_name_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name)"
                            )
                        if "function_name_file_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX function_name_file_idx IF NOT EXISTS FOR (f:Function) ON (f.name, f.file_path)"
                            )
                        if "class_name_file_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX class_name_file_idx IF NOT EXISTS FOR (c:Class) ON (c.name, c.file_path)"
                            )
                        if "file_path_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX file_path_idx IF NOT EXISTS FOR (f:File) ON (f.path)"
                            )
                        if "codefile_path_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX codefile_path_idx IF NOT EXISTS FOR (f:CodeFile) ON (f.path)"
                            )
                        if "experience_consolidated_at_idx" not in existing_schema:
                            await session.run(
                                "CREATE INDEX experience_consolidated_at_idx IF NOT EXISTS FOR (e:Experience) ON (e.consolidated_at)"
                            )
                    except Exception:
                        try:
                            await session.run(
                                "CREATE CONSTRAINT ON (e:Experience) ASSERT e.id IS UNIQUE"
                            )
                        except Exception:
                            pass
                        try:
                            await session.run(
                                "CREATE CONSTRAINT ON (t:RelationshipType) ASSERT t.name IS UNIQUE"
                            )
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
        query = "MERGE (t:RelationshipType {name: $rel_type})"
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
            from app.core.monitoring.health_monitor import (
                get_timeout_recommendation,
                record_latency,
            )

            start = asyncio.get_event_loop().time()
            async with self._driver.session() as session:
                _timeout = get_timeout_recommendation(
                    "neo4j_query",
                    float(getattr(settings, "NEO4J_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
                )
                result = await asyncio.wait_for(
                    session.run(cypher_query, params or {}), timeout=float(_timeout)
                )
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
        max_attempts=int(getattr(settings, "NEO4J_EXECUTE_MAX_ATTEMPTS", 1) or 1),
        initial_backoff=float(
            getattr(
                settings,
                "NEO4J_EXECUTE_INITIAL_BACKOFF_SECONDS",
                getattr(settings, "LLM_RETRY_INITIAL_BACKOFF_SECONDS", 0.5),
            )
            or 0.5
        ),
        max_backoff=float(
            getattr(
                settings,
                "NEO4J_EXECUTE_MAX_BACKOFF_SECONDS",
                getattr(settings, "LLM_RETRY_MAX_BACKOFF_SECONDS", 5.0),
            )
            or 5.0
        ),
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
            from app.core.monitoring.health_monitor import (
                get_timeout_recommendation,
                record_latency,
            )

            start = asyncio.get_event_loop().time()
            async with self._driver.session() as session:
                _timeout = get_timeout_recommendation(
                    "neo4j_query",
                    float(getattr(settings, "NEO4J_DEFAULT_TIMEOUT_SECONDS", 30) or 30),
                )
                await asyncio.wait_for(
                    session.run(cypher_query, params or {}), timeout=float(_timeout)
                )
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

    async def cleanup_synonym_properties(
        self, label: str, canonical_mappings: dict[str, list[str]]
    ) -> int:
        if self._driver is None or self._offline:
            return 0
        total_updated = 0
        async with self._driver.session() as session:
            tx = await session.begin_transaction()
            try:
                for canonical, synonyms in canonical_mappings.items():
                    if not synonyms:
                        continue
                    where_clauses = [f"n.{syn} IS NOT NULL" for syn in synonyms]
                    set_clauses = [
                        f"n.{canonical} = coalesce(n.{canonical}, n.{syn})" for syn in synonyms
                    ]
                    remove_clauses = [f"n.{syn}" for syn in synonyms]
                    query = (
                        f"MATCH (n:{label}) "
                        f"WHERE {' OR '.join(where_clauses)} "
                        f"SET {', '.join(set_clauses)} "
                        f"REMOVE {', '.join(remove_clauses)} "
                        f"RETURN count(n) AS count"
                    )
                    result = await tx.run(query)
                    record = await result.single()
                    if record and "count" in record:
                        try:
                            total_updated += int(record["count"])
                        except Exception:
                            pass
                await tx.commit()
            finally:
                await tx.close()
        return total_updated

    async def merge_node(
        self,
        tx: AsyncTransaction,
        label: str,
        name: str,
        properties: dict[str, Any] | None = None,
        merge_keys: list[str] | None = None,
    ) -> str:
        props = dict(properties or {})
        props.setdefault("name", name)
        keys = merge_keys or ["name"]

        merge_parts: list[str] = []
        merge_params: dict[str, Any] = {}

        for key in keys:
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                raise ValueError(f"Invalid merge key for graph node: {key}")

            key_value = props.get(key)
            if key_value is None:
                raise ValueError(f"Missing required merge key '{key}' for graph node merge")

            param_name = f"merge_{key}"
            merge_parts.append(f"{key}: ${param_name}")
            merge_params[param_name] = key_value

        merge_clause = ", ".join(merge_parts)
        query = f"MERGE (n:{label} {{{merge_clause}}}) SET n += $props RETURN elementId(n) as node_id"
        start = asyncio.get_event_loop().time()
        result = await tx.run(query, **merge_params, props=props)
        record = await result.single()
        try:
            _DB_QUERIES.labels("merge_node", "success").inc()
            _DB_LATENCY.labels("merge_node").observe(asyncio.get_event_loop().time() - start)
        except Exception:
            pass
        return record["node_id"]

    async def merge_relationship(
        self, tx: AsyncTransaction, source_id: str, target_id: str, rel_type: str
    ):
        await self.register_relationship_type(tx, rel_type)
        query = f"MATCH (a) WHERE elementId(a) = $source_id MATCH (b) WHERE elementId(b) = $target_id MERGE (a)-[:`{rel_type}`]->(b)"
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
            logger.warning("log_warning", message=f"Neo4j health check falhou: {e}")
            return False


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_graph_db_instance: GraphDatabase | None = None


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
