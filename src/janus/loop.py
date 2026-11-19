from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

from janus.adapter import ModelAdapter, Proposal
from janus.context import build_context
from janus.entry import Identity, OpenRunRequest
from janus.experience import EMPTY_OUTCOME, Experience, ProposalRef, Provenance, Signal
from janus.gate import STEP_REASON, TERMINAL_REASONS, Decision, decide_read
from janus.state import Checkpoint, Pending, RunStore
from janus.tools import tool_cost
from janus.tools.delete_record import DeleteRecordTool, plain_language
from janus.tools.read_record import ReadRecordTool, ResultLabel
from janus.trace import TraceEntry
from janus.util.codec import GateName, JanusError, canonical_json, digest, format_timestamp


class Clock(Protocol):
    def now_ms(self) -> int: ...


class SystemClock:
    def now_ms(self) -> int:
        return time.time_ns() // 1_000_000


@dataclass(frozen=True)
class StepResult:
    run_id: str
    step_index: int
    gate: GateName
    tool_name: str
    risk_class: str
    reason: str
    result_text: str
    result_label: ResultLabel

    def to_json(self) -> dict[str, object]:
        return {
            "gate": self.gate,
            "reason": self.reason,
            "result_label": self.result_label,
            "result_text": self.result_text,
            "risk_class": self.risk_class,
            "run_id": self.run_id,
            "step_index": self.step_index,
            "tool_name": self.tool_name,
        }


class Runtime:
    def __init__(self, root: Path, records: Mapping[str, str], clock: Clock | None = None) -> None:
        self._store = RunStore(root)
        self._tool = ReadRecordTool(records)
        self._irreversible = DeleteRecordTool()
        self._clock = SystemClock() if clock is None else clock

    def open_run(self, request: OpenRunRequest) -> str:
        run_id = uuid.uuid4().hex
        identity = Identity(run_id, request)
        self._store.create(identity, Checkpoint.initial(run_id, self._clock.now_ms()))
        return run_id

    def step(self, run_id: str, adapter: ModelAdapter) -> StepResult:
        identity = self._store.load_identity(run_id)
        checkpoint = self._store.load_checkpoint(run_id)
        if checkpoint.status != "aberto":
            raise JanusError("run encerrado")
        now_ms = self._clock.now_ms()
        proposal = adapter.propose(build_context(identity, checkpoint))
        seen_keys = tuple(
            (item.idempotency_key, item.arguments_hash) for item in self._store.read_pending(run_id)
        )
        decision = decide_read(
            proposal.tool_name,
            proposal.arguments,
            identity.request.permission,
            identity.request.budget,
            checkpoint.spent_steps,
            checkpoint.spent_cost,
            checkpoint.started_at_ms,
            now_ms,
            seen_keys,
        )
        executed = False
        result_label: ResultLabel = "erro"
        if (
            decision.gate == "permitir"
            and decision.tool_name == "read_record"
            and decision.risk_class == "leitura"
        ):
            output = self._tool.execute(dict(decision.arguments))
            result_text = output.text
            result_label = output.label
            executed = True
        elif decision.gate == "permitir":
            result_text = "somente leitura executa"
            result_label = "erro"
        else:
            result_text = decision.reason
        if decision.gate == "pedir":
            self._remember_pending(identity, decision, now_ms)
        if decision.reason == STEP_REASON:
            spent_steps = checkpoint.spent_steps
            spent_cost = checkpoint.spent_cost
        else:
            spent_steps = checkpoint.spent_steps + 1
            spent_cost = checkpoint.spent_cost + (tool_cost(decision.tool_name) if executed else 0)
        status = "encerrado" if decision.reason in TERMINAL_REASONS else "aberto"
        stop_reason = decision.reason if status == "encerrado" else ""
        created_at = format_timestamp(now_ms)
        step_index = checkpoint.step_index + 1
        self._store.append_trace(
            TraceEntry(
                run_id,
                step_index,
                proposal,
                decision,
                result_text,
                result_label,
                "",
                created_at,
            )
        )
        self._store.append_experience(_experience(run_id, proposal, decision.gate, created_at))
        self._store.save_checkpoint(
            Checkpoint(
                run_id,
                step_index,
                spent_steps,
                spent_cost,
                checkpoint.started_at_ms,
                status,
                stop_reason,
                decision.gate,
                result_label,
                result_text,
            )
        )
        return StepResult(
            run_id,
            step_index,
            decision.gate,
            decision.tool_name,
            decision.risk_class,
            decision.reason,
            result_text,
            result_label,
        )

    def interrupt(self, run_id: str) -> Checkpoint:
        checkpoint = self._store.load_checkpoint(run_id)
        if checkpoint.status == "encerrado":
            return checkpoint
        closed = replace(checkpoint, status="encerrado", stop_reason="interrompido")
        self._store.save_checkpoint(closed)
        return closed

    def identity_of(self, run_id: str) -> Identity:
        return self._store.load_identity(run_id)

    def checkpoint_of(self, run_id: str) -> Checkpoint:
        return self._store.load_checkpoint(run_id)

    def trace_of(self, run_id: str) -> tuple[TraceEntry, ...]:
        return self._store.read_trace(run_id)

    def experiences_of(self, run_id: str) -> tuple[Experience, ...]:
        return self._store.read_experiences(run_id)

    def pending_of(self, run_id: str) -> tuple[Pending, ...]:
        return self._store.read_pending(run_id)

    def read_calls(self) -> tuple[str, ...]:
        return self._tool.calls()

    def irreversible_calls(self) -> tuple[str, ...]:
        return self._irreversible.calls()

    def _remember_pending(self, identity: Identity, decision: Decision, now_ms: int) -> None:
        arguments = dict(decision.arguments)
        action, effect = plain_language(arguments["record_id"])
        self._store.append_pending(
            Pending(
                run_id=identity.run_id,
                action=action,
                effect=effect,
                risk_class=decision.risk_class,
                deadline_ms=identity.request.budget.deadline_ms,
                status="aberta",
                idempotency_key=arguments["idempotency_key"],
                arguments_hash=digest(canonical_json(arguments)),
                opened_at=format_timestamp(now_ms),
                tool_name=decision.tool_name,
            )
        )


def _experience(run_id: str, proposal: Proposal, gate: GateName, created_at: str) -> Experience:
    arguments_hash = digest(canonical_json(proposal.mapping()))
    summary_hash = digest(f"tool_call|{proposal.tool_name}|{arguments_hash}|{proposal.expected_value}")
    return Experience(
        uuid.uuid4().hex,
        run_id,
        Signal(None, "tool_call", summary_hash),
        ProposalRef(proposal.tool_name, arguments_hash, proposal.expected_value),
        gate,
        EMPTY_OUTCOME,
        Provenance("internal", "loop", created_at, "internal"),
        "",
        "",
    )
