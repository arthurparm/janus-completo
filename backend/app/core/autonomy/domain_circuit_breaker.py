from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

import structlog

logger = structlog.get_logger(__name__)

DomainName = Literal["code", "knowledge", "tools", "deployment"]


@dataclass
class DomainCircuitState:
    failure_count: int = 0
    last_failure_at: float = 0.0
    open_since: float = 0.0
    is_open: bool = False


class DomainCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 300.0):
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._domains: dict[str, DomainCircuitState] = defaultdict(DomainCircuitState)

    def record_failure(self, domain: DomainName) -> None:
        import time
        state = self._domains[domain]
        state.failure_count += 1
        state.last_failure_at = time.time()
        if state.failure_count >= self._threshold and not state.is_open:
            state.is_open = True
            state.open_since = time.time()
            logger.warning("domain_circuit_breaker_opened", domain=domain, failures=state.failure_count)

    def record_success(self, domain: DomainName) -> None:
        state = self._domains[domain]
        state.failure_count = 0
        if state.is_open:
            state.is_open = False
            state.open_since = 0.0
            logger.info("domain_circuit_breaker_closed", domain=domain)

    def is_open(self, domain: DomainName) -> bool:
        import time
        state = self._domains[domain]
        if not state.is_open:
            return False
        if time.time() - state.open_since >= self._timeout:
            logger.info("domain_circuit_breaker_half_open", domain=domain)
            state.is_open = False
            state.open_since = 0.0
            return False
        return True

    def get_domain_health(self) -> dict[str, dict[str, Any]]:
        return {
            domain: {
                "is_open": state.is_open,
                "failure_count": state.failure_count,
                "last_failure_at": state.last_failure_at,
                "open_since": state.open_since,
            }
            for domain, state in self._domains.items()
        }
