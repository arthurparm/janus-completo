from __future__ import annotations

from dataclasses import dataclass

from janus.adapter import Proposal
from janus.gate import Decision
from janus.util.codec import (
    ResultLabel,
    as_count,
    as_id,
    as_object,
    as_result_label,
    as_str,
    as_timestamp,
    exact_keys,
    required,
)


@dataclass(frozen=True)
class TraceEntry:
    run_id: str
    step_index: int
    proposal: Proposal
    decision: Decision
    result_text: str
    result_label: ResultLabel
    weight_version: str
    created_at: str

    def to_json(self) -> dict[str, object]:
        return {
            "created_at": self.created_at,
            "decision": self.decision.to_json(),
            "proposal": self.proposal.to_json(),
            "result": {"label": self.result_label, "text": self.result_text},
            "run_id": self.run_id,
            "step_index": self.step_index,
            "weight_version": self.weight_version,
        }

    @staticmethod
    def from_json(value: object) -> TraceEntry:
        raw = as_object(value, "trace")
        exact_keys(
            raw,
            ("created_at", "decision", "proposal", "result", "run_id", "step_index", "weight_version"),
            "trace",
        )
        result = as_object(required(raw, "result"), "result")
        exact_keys(result, ("label", "text"), "result")
        return TraceEntry(
            run_id=as_id(required(raw, "run_id"), "run_id"),
            step_index=as_count(required(raw, "step_index"), "step_index"),
            proposal=Proposal.from_json(required(raw, "proposal")),
            decision=Decision.from_json(required(raw, "decision")),
            result_text=as_str(required(result, "text"), "text", allow_empty=True),
            result_label=as_result_label(required(result, "label"), "label"),
            weight_version=as_str(required(raw, "weight_version"), "weight_version", allow_empty=True),
            created_at=as_timestamp(required(raw, "created_at"), "created_at"),
        )
