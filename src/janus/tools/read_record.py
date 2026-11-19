from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from janus.util.codec import MAX_TEXT, JanusError, require_token

ResultLabel = Literal["dado", "erro"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    risk_class: str
    permission: str
    cost: int
    argument_names: tuple[str, ...]


@dataclass(frozen=True)
class ToolOutput:
    text: str
    label: ResultLabel


READ_RECORD = ToolSpec(
    name="read_record",
    risk_class="leitura",
    permission="read_record",
    cost=1,
    argument_names=("record_id",),
)


class ReadRecordTool:
    def __init__(self, records: Mapping[str, str]) -> None:
        stored: dict[str, str] = {}
        for key, value in records.items():
            require_token(key, "record_id")
            if not isinstance(value, str):
                raise JanusError("registro inválido")
            stored[key] = value
        self._records = stored
        self._calls: list[str] = []

    def calls(self) -> tuple[str, ...]:
        return tuple(self._calls)

    def execute(self, arguments: Mapping[str, str]) -> ToolOutput:
        record_id = arguments["record_id"]
        self._calls.append(record_id)
        found = self._records.get(record_id)
        if found is None:
            return ToolOutput("registro ausente", "erro")
        if len(found) > MAX_TEXT:
            return ToolOutput("resultado acima do limite", "erro")
        return ToolOutput(found, "dado")
