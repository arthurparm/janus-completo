"""Deterministic test-only doubles for failure and retry scenarios."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DeterministicToolDouble:
    name: str
    response: Any = None
    error: Exception | None = None

    def invoke(self, _: Any = None) -> Any:
        if self.error is not None:
            raise self.error
        return self.response


def deterministic_failure(name: str = "deterministic_failure") -> DeterministicToolDouble:
    return DeterministicToolDouble(name=name, error=RuntimeError("deterministic test failure"))
