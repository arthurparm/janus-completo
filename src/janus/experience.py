from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from janus.util.codec import (
    GateName,
    JanusError,
    as_gate,
    as_id,
    as_object,
    as_optional_str,
    as_str,
    as_timestamp,
    exact_keys,
    require_token,
    required,
)


def as_hash(value: object, label: str) -> str:
    text = as_str(value, label, allow_empty=False)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise JanusError(f"{label} inválido")
    return text


@dataclass(frozen=True)
class Outcome:
    criterion: str | None
    observed: str | None
    verified_by: str | None
    verified_at: str | None

    def is_empty(self) -> bool:
        return (
            self.criterion is None
            and self.observed is None
            and self.verified_by is None
            and self.verified_at is None
        )

    def to_json(self) -> dict[str, object]:
        return {
            "criterion": self.criterion,
            "observed": self.observed,
            "verified_at": self.verified_at,
            "verified_by": self.verified_by,
        }

    @staticmethod
    def from_json(value: object) -> Outcome:
        raw = as_object(value, "outcome")
        exact_keys(raw, ("criterion", "observed", "verified_at", "verified_by"), "outcome")
        return Outcome(
            as_optional_str(required(raw, "criterion"), "criterion"),
            as_optional_str(required(raw, "observed"), "observed"),
            as_optional_str(required(raw, "verified_by"), "verified_by"),
            as_optional_str(required(raw, "verified_at"), "verified_at"),
        )


EMPTY_OUTCOME = Outcome(None, None, None, None)


@dataclass(frozen=True)
class Signal:
    goal_id: str | None
    event_type: Literal["tool_call"]
    summary_hash: str

    def to_json(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "goal_id": self.goal_id,
            "summary_hash": self.summary_hash,
        }

    @staticmethod
    def from_json(value: object) -> Signal:
        raw = as_object(value, "signal")
        exact_keys(raw, ("event_type", "goal_id", "summary_hash"), "signal")
        event_type = as_str(required(raw, "event_type"), "event_type", allow_empty=False)
        if event_type != "tool_call":
            raise JanusError("event_type inválido")
        goal_id = as_optional_str(required(raw, "goal_id"), "goal_id")
        if goal_id is not None:
            require_token(goal_id, "goal_id")
        return Signal(goal_id, "tool_call", as_hash(required(raw, "summary_hash"), "summary_hash"))


@dataclass(frozen=True)
class ProposalRef:
    tool: str
    arguments_hash: str
    expected_value: str

    def to_json(self) -> dict[str, object]:
        return {
            "arguments_hash": self.arguments_hash,
            "expected_value": self.expected_value,
            "tool": self.tool,
        }

    @staticmethod
    def from_json(value: object) -> ProposalRef:
        raw = as_object(value, "proposal")
        exact_keys(raw, ("arguments_hash", "expected_value", "tool"), "proposal")
        return ProposalRef(
            as_str(required(raw, "tool"), "tool", allow_empty=False),
            as_hash(required(raw, "arguments_hash"), "arguments_hash"),
            as_str(required(raw, "expected_value"), "expected_value", allow_empty=True),
        )


@dataclass(frozen=True)
class Provenance:
    origin: Literal["internal"]
    source: str
    timestamp: str
    sensitivity: Literal["internal"]

    def to_json(self) -> dict[str, object]:
        return {
            "origin": self.origin,
            "sensitivity": self.sensitivity,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_json(value: object) -> Provenance:
        raw = as_object(value, "provenance")
        exact_keys(raw, ("origin", "sensitivity", "source", "timestamp"), "provenance")
        origin = as_str(required(raw, "origin"), "origin", allow_empty=False)
        sensitivity = as_str(required(raw, "sensitivity"), "sensitivity", allow_empty=False)
        if origin != "internal" or sensitivity != "internal":
            raise JanusError("proveniência inválida")
        return Provenance(
            "internal",
            as_str(required(raw, "source"), "source", allow_empty=False),
            as_timestamp(required(raw, "timestamp"), "timestamp"),
            "internal",
        )


@dataclass(frozen=True)
class Experience:
    experience_id: str
    run_id: str
    signal: Signal
    proposal: ProposalRef
    gate: GateName
    outcome: Outcome
    provenance: Provenance
    weight_version_before: str
    weight_version_after: str

    def to_json(self) -> dict[str, object]:
        return {
            "experience_id": self.experience_id,
            "gate": self.gate,
            "outcome": self.outcome.to_json(),
            "proposal": self.proposal.to_json(),
            "provenance": self.provenance.to_json(),
            "run_id": self.run_id,
            "signal": self.signal.to_json(),
            "weight_version_after": self.weight_version_after,
            "weight_version_before": self.weight_version_before,
        }

    @staticmethod
    def from_json(value: object) -> Experience:
        raw = as_object(value, "experience")
        exact_keys(
            raw,
            (
                "experience_id",
                "gate",
                "outcome",
                "proposal",
                "provenance",
                "run_id",
                "signal",
                "weight_version_after",
                "weight_version_before",
            ),
            "experience",
        )
        return Experience(
            experience_id=as_id(required(raw, "experience_id"), "experience_id"),
            run_id=as_id(required(raw, "run_id"), "run_id"),
            signal=Signal.from_json(required(raw, "signal")),
            proposal=ProposalRef.from_json(required(raw, "proposal")),
            gate=as_gate(required(raw, "gate"), "gate"),
            outcome=Outcome.from_json(required(raw, "outcome")),
            provenance=Provenance.from_json(required(raw, "provenance")),
            weight_version_before=as_str(
                required(raw, "weight_version_before"),
                "weight_version_before",
                allow_empty=True,
            ),
            weight_version_after=as_str(
                required(raw, "weight_version_after"),
                "weight_version_after",
                allow_empty=True,
            ),
        )
