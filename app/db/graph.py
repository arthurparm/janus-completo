import logging
import threading
import time

from neo4j import GraphDatabase as Neo4jGraphDatabase, Neo4jDriver
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

# Metrics
_DB_QUERIES = Counter("neo4j_queries_total", "Total de queries ao Neo4j",
                      ["operation", "outcome", "exception_type"])  # type: ignore
_DB_LATENCY = Histogram("neo4j_query_latency_seconds", "Latência por query ao Neo4j",
                        ["operation", "outcome"])  # type: ignore

# Circuit Breaker for DB operations
_DB_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=20)


class GraphDatabase:
    _driver: Neo4jDriver | None = None
    _driver_lock = threading.Lock()

    def get_driver(self) -> Neo4jDriver:
        """
        Retorna o driver Neo4j, inicializando-o de forma thread-safe se necessário.
        Garante que o driver seja criado apenas uma vez.
        """
        # Double-checked locking para performance
        if self._driver is not None:
            return self._driver

        with self._driver_lock:
            if self._driver is None:
                logger.info("Driver not initialized. Creating new Neo4j driver...")
                try:
                    password = settings.NEO4J_PASSWORD.get_secret_value()
                    driver = Neo4jGraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USER, password),
                        connection_timeout=15.0,
                        max_connection_lifetime=3600,  # 1 hour
                    )
                    # Verifica a conectividade antes de atribuir
                    driver.verify_connectivity()
                    self._driver = driver
                    logger.info("New Neo4j driver created and verified successfully.")
                except Exception as e:
                    logger.critical(f"FATAL: Could not create or verify Neo4j driver: {e}", exc_info=True)
                    raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e

        return self._driver

    def close(self):
        """Closes the driver connection."""
        with self._driver_lock:
            if self._driver is not None:
                try:
                    self._driver.close()
                    logger.info("Neo4j driver closed.")
                except Exception as e:
                    logger.error(f"Error while closing Neo4j driver: {e}", exc_info=True)
                finally:
                    self._driver = None

    def reset(self):
        """Força o fechamento e a recriação do driver na próxima chamada."""
        logger.warning("Resetting Neo4j driver connection.")
        self.close()

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
            driver = self.get_driver()
            driver.verify_connectivity()
            logger.debug("Neo4j health check passed via verify_connectivity.")
            return True
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return False


graph_db = GraphDatabase()
