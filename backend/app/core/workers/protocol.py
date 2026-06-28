from typing import Protocol


class WorkerProtocol(Protocol):

    name: str

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    def is_healthy(self) -> bool:
        ...

    def get_status(self) -> dict:
        ...
