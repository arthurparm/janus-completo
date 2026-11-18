from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LocalInferenceRuntime(Protocol):
    name: str

    async def generate(self, *, prompt: str, config: dict[str, Any] | None = None) -> dict[str, Any]: ...


@dataclass
class OllamaRuntime:
    name: str = "ollama"

    async def generate(self, *, prompt: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"status": "delegated", "runtime": self.name, "prompt_chars": len(prompt)}


@dataclass
class ExperimentalTurboQuantRuntime:
    name: str = "experimental_turboquant"

    async def generate(self, *, prompt: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError("TurboQuant runtime is not implemented yet")

