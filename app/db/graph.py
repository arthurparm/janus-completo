
import logging
import time

from neo4j import GraphDatabase as Neo4jGraphDatabase, Neo4jDriver
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

# Metrics
_DB_QUERIES = Counter("neo4j_queries_total", "Total de queries ao Neo4j", ["operation", "outcome", "exception_type"])  # type: ignore
_DB_LATENCY = Histogram("neo4j_query_latency_seconds", "Latência por query ao Neo4j", ["operation", "outcome"])  # type: ignore

# Circuit Breaker for DB operations
_DB_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=20)


class GraphDatabase:
    _driver: Neo4jDriver = None

    def get_driver(self) -> Neo4jDriver:
        """Returns the existing driver or creates a new one."""
        if self._driver is None:
            logger.info("Driver not initialized. Creating new Neo4j driver...")
            try:
                password = settings.NEO4J_PASSWORD.get_secret_value()
                self._driver = Neo4jGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, password),
                    connection_timeout=15.0,  # seconds
                )
                logger.info("New Neo4j driver created successfully.")
            except Exception as e:
                logger.critical(f"FATAL: Could not create Neo4j driver: {e}", exc_info=True)
                raise
        return self._driver

    def close(self):
        """Closes the driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed.")

    def _do_query(self, cypher_query: str, params: dict | None = None):
        driver = self.get_driver()
        with driver.session() as session:
            result = session.run(cypher_query, params or {})
            return [record.data() for record in result]

    def query(self, cypher_query: str, params: dict = None, *, operation: str | None = None):
        """Executes a query using a session from the driver with retries/CB/metrics."""
        op = operation or "generic"
        wrapped = resilient(
            max_attempts=3,
            initial_backoff=0.2,
            max_backoff=2.0,
            circuit_breaker=_DB_CB,
            retry_on=(Exception,),
            operation_name=f"neo4j_{op}",
        )(self._do_query)
        start = time.perf_counter()
        try:
            rows = wrapped(cypher_query, params)
            _DB_QUERIES.labels(op, "success", "").inc()
            _DB_LATENCY.labels(op, "success").observe(time.perf_counter() - start)
            return rows
        except Exception as e:
            _DB_QUERIES.labels(op, "failure", type(e).__name__).inc()
            _DB_LATENCY.labels(op, "failure").observe(time.perf_counter() - start)
            logger.error(f"Error executing Cypher query: {cypher_query}", exc_info=True)
            raise

    def health_check(self) -> bool:
        try:
            res = self.query("RETURN 1 as one", {}, operation="health")
            return bool(res and res[0].get("one") == 1)
        except Exception:
            return False


graph_db = GraphDatabase()
