from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from langchain_core.language_models.chat_models import BaseChatModel


class ModelRole(Enum):
    ORCHESTRATOR = "orchestrator"
    CODE_GENERATOR = "code_generator"
    KNOWLEDGE_CURATOR = "knowledge_curator"
    SECURITY_AUDITOR = "security_auditor"


class ModelPriority(Enum):
    LOCAL_ONLY = "local_only"
    FAST_AND_CHEAP = "fast_and_cheap"
    HIGH_QUALITY = "high_quality"


@dataclass
class CachedLLM:
    instance: BaseChatModel
    created_at: datetime
    provider: str
    model: str
    consecutive_failures: int = 0


@dataclass
class ProviderPricing:
    input_per_1k_usd: float
    output_per_1k_usd: float
    cache_read_per_1k_usd: float = 0.0


@dataclass
class ProviderStats:
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.success_count / max(1, self.total_requests)

    @property
    def avg_latency(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.total_latency_seconds / max(1, self.total_requests)


@dataclass
class ModelStats:
    total_requests: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.success_count / max(1, self.total_requests)

    @property
    def avg_latency(self) -> float:
        if self.total_requests <= 0:
            return 0.0
        return self.total_latency_seconds / max(1, self.total_requests)
