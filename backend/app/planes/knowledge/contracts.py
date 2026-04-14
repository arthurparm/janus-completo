from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class RetrievalBackendName(StrEnum):
    BASELINE_QDRANT = "baseline_qdrant"
    EXPERIMENTAL_QUANTIZED_RETRIEVAL = "experimental_quantized_retrieval"


@dataclass(frozen=True)
class RetrievalBackendDecision:
    active_backend: RetrievalBackendName
    shadow_backend: RetrievalBackendName | None = None


class RetrievalBackendProtocol(Protocol):
    name: RetrievalBackendName

    async def search_documents(
        self,
        *,
        query: str,
        user_id: str,
        doc_id: str | None,
        knowledge_space_id: str | None,
        limit: int,
        min_score: float | None,
    ) -> list[dict[str, Any]]: ...

