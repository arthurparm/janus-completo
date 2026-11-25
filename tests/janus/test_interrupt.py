# JAN-023
from __future__ import annotations

import tempfile
import threading
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from janus.adapter import ModelContext, Proposal
from janus.api import interrupt_run
from janus.gate import STEP_REASON
from janus.loop import Runtime, StepResult
from janus.trace import TraceEntry
from janus.util.codec import JanusError
from tests.janus.support import alpha_request, delete_proposal, read_proposal, read_runtime

REASON = "run interrompido"
JOIN_LIMIT_SECONDS = 10.0


class InterruptDuringStepTest(unittest.TestCase):
    def test_interrupt_during_propose_keeps_run_closed(self) -> None:
        for label, permission, other_runtime in _cases():
            with self.subTest(caso=label):
                with tempfile.TemporaryDirectory() as tmp:
                    step = _interrupted_step(Path(tmp), permission, other_runtime)
                    self.assertEqual(step.returned["status"], "encerrado")
                    checkpoint = step.runtime.checkpoint_of(step.run_id)
                    self.assertEqual(checkpoint.status, "encerrado")
                    self.assertEqual(checkpoint.stop_reason, "interrompido")

    def test_interrupted_step_denies_the_proposal_without_effect(self) -> None:
        for label, permission, other_runtime in _cases():
            with self.subTest(caso=label):
                with tempfile.TemporaryDirectory() as tmp:
                    step = _interrupted_step(Path(tmp), permission, other_runtime)
                    self.assertEqual(step.result.gate, "negar")
                    self.assertEqual(step.result.reason, REASON)
                    self.assertEqual(step.runtime.read_calls(), ())
                    self.assertEqual(step.runtime.irreversible_calls(), ())
                    self.assertEqual(step.runtime.pending_of(step.run_id), ())

    def test_interrupted_step_records_trace_with_empty_experience(self) -> None:
        for label, permission, other_runtime in _cases():
            with self.subTest(caso=label):
                with tempfile.TemporaryDirectory() as tmp:
                    step = _interrupted_step(Path(tmp), permission, other_runtime)
                    trace = step.runtime.trace_of(step.run_id)
                    experiences = step.runtime.experiences_of(step.run_id)
                    checkpoint = step.runtime.checkpoint_of(step.run_id)
                    self.assertEqual(len(trace), 1)
                    self.assertEqual(trace[0].decision.gate, "negar")
                    self.assertEqual(trace[0].decision.reason, REASON)
                    self.assertEqual(len(experiences), 1)
                    self.assertEqual(experiences[0].gate, "negar")
                    self.assertTrue(experiences[0].outcome.is_empty())
                    self.assertEqual(checkpoint.step_index, 1)
                    self.assertEqual(checkpoint.spent_steps, 1)
                    self.assertEqual(checkpoint.spent_cost, 0)

    def test_step_after_interrupted_step_does_not_call_a_tool(self) -> None:
        for label, permission, other_runtime in _cases():
            with self.subTest(caso=label):
                with tempfile.TemporaryDirectory() as tmp:
                    step = _interrupted_step(Path(tmp), permission, other_runtime)
                    calls = step.runtime.read_calls()
                    adapter = _Adapter(_proposal(permission))
                    with self.assertRaises(JanusError) as caught:
                        step.runtime.step(step.run_id, adapter)
                    self.assertEqual(caught.exception.reason, "run encerrado")
                    self.assertEqual(adapter.calls, 0)
                    self.assertEqual(step.runtime.read_calls(), calls)
                    self.assertEqual(step.runtime.irreversible_calls(), ())

    def test_interrupt_after_the_decision_keeps_run_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request("read_record"))
            store = runtime._store
            append = store.append_trace

            def append_after_interrupt(entry: TraceEntry) -> None:
                interrupt_run(read_runtime(Path(tmp)), run_id)
                append(entry)

            store.append_trace = append_after_interrupt
            result = runtime.step(run_id, _Adapter(_proposal("read_record")))
            self.assertEqual(result.gate, "permitir")
            self.assertEqual(runtime.read_calls(), ("alpha",))
            checkpoint = runtime.checkpoint_of(run_id)
            self.assertEqual(checkpoint.status, "encerrado")
            self.assertEqual(checkpoint.stop_reason, "interrompido")
            self.assertEqual(checkpoint.spent_steps, 1)

    def test_mark_after_consultation_keeps_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            step = _late_interrupted_step(Path(tmp), "delete_record")
            self.assertEqual(step.returned["status"], "encerrado")
            self.assertEqual(step.result.gate, "pedir")
            pending = step.runtime.pending_of(step.run_id)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].status, "aberta")
            self.assertEqual(step.runtime.irreversible_calls(), ())
            self.assertEqual(step.runtime.checkpoint_of(step.run_id).status, "encerrado")

    def test_mark_after_consultation_records_trace_with_empty_experience(self) -> None:
        for permission, gate in (("read_record", "permitir"), ("delete_record", "pedir")):
            with self.subTest(permissao=permission):
                with tempfile.TemporaryDirectory() as tmp:
                    step = _late_interrupted_step(Path(tmp), permission)
                    trace = step.runtime.trace_of(step.run_id)
                    experiences = step.runtime.experiences_of(step.run_id)
                    checkpoint = step.runtime.checkpoint_of(step.run_id)
                    self.assertEqual(step.returned["status"], "encerrado")
                    self.assertEqual(len(trace), 1)
                    self.assertEqual(trace[0].decision.gate, gate)
                    self.assertEqual(len(experiences), 1)
                    self.assertEqual(experiences[0].gate, gate)
                    self.assertTrue(experiences[0].outcome.is_empty())
                    self.assertEqual(checkpoint.stop_reason, "interrompido")
                    self.assertEqual(checkpoint.spent_steps, 1)

    def test_interrupt_on_exhausted_step_keeps_budget_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request("read_record", max_steps=0))
            adapter = _Adapter(_proposal("read_record"), lambda: interrupt_run(read_runtime(Path(tmp)), run_id))
            result = runtime.step(run_id, adapter)
            self.assertEqual(result.reason, STEP_REASON)
            self.assertEqual(runtime.trace_of(run_id)[0].decision.reason, STEP_REASON)
            self.assertEqual(len(runtime.experiences_of(run_id)), 1)
            self.assertEqual(runtime.read_calls(), ())
            checkpoint = runtime.checkpoint_of(run_id)
            self.assertEqual(checkpoint.status, "encerrado")
            self.assertEqual(checkpoint.spent_steps, 0)


class _Adapter:
    model_id = "model-a"

    def __init__(self, proposal: Proposal, during: Callable[[], object] | None = None) -> None:
        self._proposal = proposal
        self._during = during
        self.calls = 0

    def propose(self, context: ModelContext) -> Proposal:
        self.calls += 1
        if self._during is not None:
            self._during()
        return self._proposal


@dataclass(frozen=True)
class _Step:
    runtime: Runtime
    run_id: str
    returned: dict[str, object]
    result: StepResult


def _cases() -> tuple[tuple[str, str, bool], ...]:
    return (
        ("leitura, mesmo runtime", "read_record", False),
        ("leitura, segundo runtime", "read_record", True),
        ("escrita, mesmo runtime", "delete_record", False),
        ("escrita, segundo runtime", "delete_record", True),
    )


def _interrupted_step(root: Path, permission: str, other_runtime: bool) -> _Step:
    runtime = read_runtime(root)
    run_id = runtime.open_run(alpha_request(permission))
    interrupter = read_runtime(root) if other_runtime else runtime
    returned: list[dict[str, object]] = []

    def during() -> None:
        thread = threading.Thread(target=lambda: returned.append(interrupt_run(interrupter, run_id)))
        thread.start()
        thread.join(JOIN_LIMIT_SECONDS)

    result = runtime.step(run_id, _Adapter(_proposal(permission), during))
    if len(returned) != 1:
        raise AssertionError("interrupt_run não terminou durante o propose")
    return _Step(runtime, run_id, returned[0], result)


def _late_interrupted_step(root: Path, permission: str) -> _Step:
    """A marca chega logo depois da consulta que o passo faz após o propose."""
    runtime = read_runtime(root)
    run_id = runtime.open_run(alpha_request(permission))
    interrupter = read_runtime(root)
    store = runtime._store
    consult = store.is_interrupted
    armed: list[None] = []
    returned: list[dict[str, object]] = []

    def consult_then_interrupt(target: str) -> bool:
        seen = consult(target)
        if armed:
            armed.clear()
            returned.append(interrupt_run(interrupter, target))
        return seen

    store.is_interrupted = consult_then_interrupt
    result = runtime.step(run_id, _Adapter(_proposal(permission), lambda: armed.append(None)))
    if len(returned) != 1:
        raise AssertionError("a marca não chegou depois da consulta")
    return _Step(runtime, run_id, returned[0], result)


def _proposal(permission: str) -> Proposal:
    if permission == "read_record":
        return read_proposal()
    return delete_proposal("chave-1")


if __name__ == "__main__":
    unittest.main()
