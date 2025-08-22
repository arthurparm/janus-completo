from neo4j import GraphDatabase as Neo4jGraphDatabase, Neo4jDriver
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class GraphDatabase:
    _driver: Neo4jDriver = None

    def get_driver(self) -> Neo4jDriver:
        """Returns the existing driver or creates a new one."""
        if self._driver is None:
            logger.info("Driver not initialized. Creating new Neo4j driver...")
            try:
                self._driver = Neo4jGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
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

    def query(self, cypher_query: str, params: dict = None):
        """Executes a query using a session from the driver."""
        driver = self.get_driver()
        try:
            with driver.session() as session:
                result = session.run(cypher_query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing Cypher query: {cypher_query}", exc_info=True)
            raise

# A single instance to be used throughout the app
graph_db = GraphDatabase()