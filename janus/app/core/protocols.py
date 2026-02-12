from typing import Any, Protocol

from neo4j import AsyncTransaction


class MessageBrokerProtocol(Protocol):
    """
    Define a interface para um sistema de Message Broker.
    """

    async def publish(self, queue_name: str, message: str) -> None: ...

    async def get_queue_info(self, queue_name: str) -> dict[str, Any] | None: ...

    async def health_check(self) -> bool: ...


class GraphDBProtocol(Protocol):
    """
    Define a interface para um banco de dados de grafo.
    """

    async def query(
        self, cypher_query: str, params: dict[str, Any] | None = None, operation: str | None = None
    ) -> list[dict[str, Any]]: ...

    async def execute(
        self, cypher_query: str, params: dict[str, Any] | None = None, operation: str | None = None
    ) -> None: ...

    async def merge_node(
        self,
        tx: AsyncTransaction,
        label: str,
        name: str,
        properties: dict[str, Any] | None = None,
        merge_keys: list[str] | None = None,
    ) -> str: ...

    async def merge_relationship(
        self, tx: AsyncTransaction, source_id: str, target_id: str, rel_type: str
    ) -> None: ...

    async def get_driver(self) -> Any: ...  # Retorno genérico para uso em transações


class MemoryDBProtocol(Protocol):
    """
    Interface para operações do banco de memória vetorial (episódica).
    """

    async def amemorize(self, experience: Any) -> None: ...

    async def arecall(
        self, query: str, limit: int | None = 10, min_score: float | None = None
    ) -> list[dict[str, Any]]: ...

    async def arecall_filtered(
        self,
        query: str | None,
        filters: dict[str, Any],
        limit: int | None = 10,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...

    async def arecall_by_timeframe(
        self,
        query: str | None,
        start_ts_ms: int | None,
        end_ts_ms: int | None,
        limit: int | None = 10,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...

    async def arecall_recent_failures(
        self,
        limit: int | None = 10,
        timeframe_seconds: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...


class MemoryRepositoryProtocol(Protocol):
    """
    Contrato do Repositório de Memória consumido pela camada de Serviço.
    """

    async def save_experience(self, experience: Any) -> None: ...

    async def search_experiences(
        self, query: str, limit: int | None = 10, min_score: float | None = None
    ) -> list[dict[str, Any]]: ...

    async def search_filtered(
        self,
        query: str | None,
        filters: dict[str, Any],
        limit: int | None = 10,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...

    async def search_by_timeframe(
        self,
        query: str | None,
        start_ts_ms: int | None,
        end_ts_ms: int | None,
        limit: int | None = 10,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...

    async def search_recent_failures(
        self,
        limit: int | None = 10,
        timeframe_seconds: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...

    async def search_recent_lessons(
        self,
        limit: int | None = 10,
        timeframe_seconds: int | None = None,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]: ...
