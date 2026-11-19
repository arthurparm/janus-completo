from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

from janus.util.codec import MAX_TEXT, JanusError, as_object, as_str, as_string_map, exact_keys, require_token, required
from janus.util.pairs import normalize_pairs, pairs_json


@dataclass(frozen=True)
class DataBlock:
    label: Literal["dado"]
    text: str


@dataclass(frozen=True)
class ModelContext:
    voice_is_model: bool
    instruction: str
    task: str
    step_index: int
    data_blocks: tuple[DataBlock, ...]


@dataclass(frozen=True)
class Proposal:
    kind: Literal["tool_call"]
    tool_name: str
    arguments: tuple[tuple[str, str], ...]
    expected_value: str

    def __post_init__(self) -> None:
        if self.kind != "tool_call":
            raise JanusError("proposta fora do formato neutro")
        require_token(self.tool_name, "tool_name")
        if len(self.expected_value) > MAX_TEXT:
            raise JanusError("expected_value longo")
        object.__setattr__(self, "arguments", normalize_pairs(self.arguments))

    def mapping(self) -> dict[str, str]:
        return dict(self.arguments)

    def to_json(self) -> dict[str, object]:
        return {
            "arguments": pairs_json(self.arguments),
            "expected_value": self.expected_value,
            "kind": self.kind,
            "tool_name": self.tool_name,
        }

    @staticmethod
    def from_mapping(tool_name: str, arguments: Mapping[str, str], expected_value: str) -> Proposal:
        return Proposal("tool_call", tool_name, tuple(arguments.items()), expected_value)

    @staticmethod
    def from_json(value: object) -> Proposal:
        raw = as_object(value, "proposal")
        exact_keys(raw, ("arguments", "expected_value", "kind", "tool_name"), "proposal")
        kind = as_str(required(raw, "kind"), "kind", allow_empty=False)
        if kind != "tool_call":
            raise JanusError("proposta fora do formato neutro")
        return Proposal(
            "tool_call",
            as_str(required(raw, "tool_name"), "tool_name", allow_empty=False),
            as_string_map(required(raw, "arguments"), "arguments"),
            as_str(required(raw, "expected_value"), "expected_value", allow_empty=True),
        )


class ModelAdapter(Protocol):
    model_id: str

    def propose(self, context: ModelContext) -> Proposal: ...


class ScriptedAdapter:
    def __init__(self, model_id: str, proposals: tuple[Proposal, ...]) -> None:
        self.model_id = model_id
        self._proposals = proposals
        self._index = 0
        self.contexts: list[ModelContext] = []

    def propose(self, context: ModelContext) -> Proposal:
        self.contexts.append(context)
        if self._index >= len(self._proposals):
            raise JanusError("adaptador sem proposta")
        proposal = self._proposals[self._index]
        self._index += 1
        return proposal
