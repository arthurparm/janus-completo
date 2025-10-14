from typing import Protocol, Any, Dict, Optional, List
from neo4j import AsyncTransaction


class MessageBrokerProtocol(Protocol):
    """
    Define a interface para um sistema de Message Broker.
    """

    async def publish(self, queue_name: str, message: str) -> None: ...

    async def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]: ...

    async def health_check(self) -> bool: ...


class GraphDBProtocol(Protocol):
    """
    Define a interface para um banco de dados de grafo.
    """

    async def query(self, cypher_query: str, params: Optional[Dict[str, Any]] = None,
                    operation: Optional[str] = None) -> List[Dict[str, Any]]: ...

    async def execute(self, cypher_query: str, params: Optional[Dict[str, Any]] = None,
                      operation: Optional[str] = None) -> None: ...

    async def merge_node(self, tx: AsyncTransaction, label: str, name: str) -> int: ...

    async def merge_relationship(self, tx: AsyncTransaction, source_id: int, target_id: int, rel_type: str) -> None: ...

    async def get_driver(self) -> Any: ...  # Retorno genérico para uso em transações
