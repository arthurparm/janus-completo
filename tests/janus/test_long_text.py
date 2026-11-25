# JAN-024
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from janus.adapter import ModelContext, Proposal, ScriptedAdapter
from janus.entry import Budget, OpenRunRequest
from janus.loop import Runtime
from janus.util.codec import JanusError
from tests.janus.support import ManualClock

# O efeito da pendência acrescenta 52 caracteres ao record_id, e a ação, 18.
LONGEST_RECORD_ID = 3948
LIMIT = 4000
FIELDS = ("requester", "permission", "model_id")


class LongTextTest(unittest.TestCase):
    def test_longest_record_id_that_fits_creates_readable_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(Path(tmp))
            run_id = runtime.open_run(_request(permission="delete_record"))
            result = runtime.step(run_id, _adapter(_delete("a" * LONGEST_RECORD_ID)))
            self.assertEqual(result.gate, "pedir")
            pending = runtime.pending_of(run_id)
            self.assertEqual(len(pending), 1)
            self.assertEqual(len(pending[0].effect), LIMIT)
            self.assertEqual(len(runtime.trace_of(run_id)), 1)
            self.assertEqual(len(runtime.experiences_of(run_id)), 1)

    def test_record_id_over_the_pending_limit_is_denied_and_recorded(self) -> None:
        for length in (LONGEST_RECORD_ID + 1, 3982, 3983, LIMIT):
            with self.subTest(record_id=length):
                with tempfile.TemporaryDirectory() as tmp:
                    runtime = _runtime(Path(tmp))
                    run_id = runtime.open_run(_request(permission="delete_record"))
                    result = runtime.step(run_id, _adapter(_delete("a" * length)))
                    self.assertEqual(result.gate, "negar")
                    self.assertEqual(result.reason, "texto da pendência acima do limite")
                    self.assertEqual(result.risk_class, "escrita_irreversivel")
                    self.assertEqual(runtime.irreversible_calls(), ())
                    self.assertEqual(runtime.pending_of(run_id), ())
                    self.assertEqual(runtime.trace_of(run_id)[0].decision.gate, "negar")
                    self.assertEqual(runtime.experiences_of(run_id)[0].gate, "negar")
                    self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)

    def test_tool_name_at_the_limit_keeps_every_step_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(Path(tmp))
            run_id = runtime.open_run(_request())
            runtime.step(run_id, _adapter(_read()))
            result = runtime.step(run_id, _adapter(Proposal.from_mapping("t" * LIMIT, {}, "")))
            self.assertEqual(result.gate, "negar")
            self.assertEqual(len(runtime.trace_of(run_id)), 2)
            self.assertEqual(len(runtime.experiences_of(run_id)), 2)

    def test_tool_name_over_the_limit_is_refused_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = _runtime(Path(tmp))
            run_id = runtime.open_run(_request())
            runtime.step(run_id, _adapter(_read()))
            before = runtime.checkpoint_of(run_id)
            with self.assertRaises(JanusError) as caught:
                runtime.step(run_id, _LongToolName())
            self.assertEqual(caught.exception.reason, "tool_name inválido")
            self.assertEqual(len(runtime.trace_of(run_id)), 1)
            self.assertEqual(len(runtime.experiences_of(run_id)), 1)
            self.assertEqual(runtime.checkpoint_of(run_id), before)
            self.assertEqual(runtime.read_calls(), ("alpha",))

    def test_request_field_over_the_limit_is_refused_before_the_run_exists(self) -> None:
        for field in FIELDS:
            with self.subTest(campo=field):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    runtime = _runtime(root)
                    with self.assertRaises(JanusError) as caught:
                        runtime.open_run(_request(**{field: "x" * (LIMIT + 1)}))
                    self.assertEqual(caught.exception.reason, f"{field} inválido")
                    self.assertEqual(tuple(root.iterdir()), ())

    def test_request_field_at_the_limit_opens_a_readable_run(self) -> None:
        for field in FIELDS:
            with self.subTest(campo=field):
                with tempfile.TemporaryDirectory() as tmp:
                    runtime = _runtime(Path(tmp))
                    run_id = runtime.open_run(_request(**{field: "x" * LIMIT}))
                    runtime.step(run_id, _adapter(_read()))
                    self.assertEqual(runtime.identity_of(run_id).run_id, run_id)
                    self.assertEqual(len(runtime.trace_of(run_id)), 1)
                    self.assertEqual(len(runtime.experiences_of(run_id)), 1)


class _LongToolName:
    model_id = "model-a"

    def propose(self, context: ModelContext) -> Proposal:
        return Proposal.from_mapping("t" * (LIMIT + 1), {}, "")


def _runtime(root: Path) -> Runtime:
    return Runtime(root, {"alpha": "conteudo-alpha"}, ManualClock())


def _request(
    *,
    requester: str = "arthur",
    permission: str = "read_record",
    model_id: str = "model-a",
) -> OpenRunRequest:
    return OpenRunRequest(requester, permission, Budget(3, 1000, 3), True, model_id, "ler o registro alpha")


def _adapter(proposal: Proposal) -> ScriptedAdapter:
    return ScriptedAdapter("model-a", (proposal,))


def _read() -> Proposal:
    return Proposal.from_mapping("read_record", {"record_id": "alpha"}, "ler")


def _delete(record_id: str) -> Proposal:
    return Proposal.from_mapping(
        "delete_record", {"record_id": record_id, "idempotency_key": "chave-1"}, ""
    )


if __name__ == "__main__":
    unittest.main()
