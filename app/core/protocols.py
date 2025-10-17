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


class MemoryDBProtocol(Protocol):
    """
    Interface para operações do banco de memória vetorial (episódica).
    """

    async def amemorize(self, experience: Any) -> None: ...

    async def arecall(self, query: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]: ...

    async def arecall_filtered(self, query: Optional[str], filters: Dict[str, Any], limit: Optional[int] = 10) -> List[Dict[str, Any]]: ...

    async def arecall_by_timeframe(self, query: Optional[str], start_ts_ms: Optional[int], end_ts_ms: Optional[int], limit: Optional[int] = 10) -> List[Dict[str, Any]]: ...

    async def arecall_recent_failures(self, limit: Optional[int] = 10, timeframe_seconds: Optional[int] = None) -> List[Dict[str, Any]]: ...
