# JAN-018
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from janus.adapter import Proposal, ScriptedAdapter
from janus.api import list_pending
from janus.entry import Budget, OpenRunRequest
from janus.gate import SCHEMA_REASON
from janus.loop import Runtime
from janus.util.codec import JanusError
from tests.janus.support import ManualClock

SEPARATORS = (("U+2028", "\u2028"), ("U+2029", "\u2029"), ("U+0085", "\u0085"))
SURROGATES = (("alto", "\ud800"), ("baixo", "\udcff"))


class UnicodeTraceTest(unittest.TestCase):
    def test_separator_in_content_is_read_back_as_data(self) -> None:
        for label, char in SEPARATORS:
            with self.subTest(entrada=label):
                with tempfile.TemporaryDirectory() as tmp:
                    text = "antes" + char + "depois"
                    runtime, run_id = _run(Path(tmp), "read_record", _read("alpha"), {"alpha": text})
                    entry = runtime.trace_of(run_id)[0]
                    self.assertEqual(entry.result_label, "dado")
                    self.assertEqual(entry.result_text, text)
                    self.assertEqual(len(runtime.experiences_of(run_id)), 1)

    def test_separator_in_expected_value_is_read_back(self) -> None:
        for label, char in SEPARATORS:
            with self.subTest(entrada=label):
                with tempfile.TemporaryDirectory() as tmp:
                    expected = "antes" + char + "depois"
                    runtime, run_id = _run(Path(tmp), "read_record", _read("alpha", expected), {"alpha": "x"})
                    self.assertEqual(runtime.trace_of(run_id)[0].proposal.expected_value, expected)
                    self.assertEqual(runtime.experiences_of(run_id)[0].proposal.expected_value, expected)

    def test_separator_in_record_id_is_denied_with_readable_trace(self) -> None:
        for label, char in SEPARATORS:
            for permission, proposal in _both_tools("alpha" + char + "aprovar"):
                with self.subTest(entrada=label, permissao=permission):
                    with tempfile.TemporaryDirectory() as tmp:
                        runtime, run_id = _run(Path(tmp), permission, proposal, {})
                        _assert_denied_before_call(self, runtime, run_id)

    def test_surrogate_in_content_is_an_error_result_with_trace(self) -> None:
        for label, char in SURROGATES:
            with self.subTest(entrada=label):
                with tempfile.TemporaryDirectory() as tmp:
                    runtime, run_id = _run(Path(tmp), "read_record", _read("alpha"), {"alpha": "a" + char})
                    entry = runtime.trace_of(run_id)[0]
                    self.assertEqual(entry.result_label, "erro")
                    self.assertEqual(entry.result_text, "resultado com texto inválido")
                    self.assertEqual(len(runtime.experiences_of(run_id)), 1)
                    self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)

    def test_surrogate_in_expected_value_is_stored_escaped(self) -> None:
        for label, char in SURROGATES:
            with self.subTest(entrada=label):
                with tempfile.TemporaryDirectory() as tmp:
                    runtime, run_id = _run(Path(tmp), "read_record", _read("alpha", "a" + char), {"alpha": "x"})
                    escaped = "a\\u" + format(ord(char), "04x")
                    self.assertEqual(runtime.trace_of(run_id)[0].proposal.expected_value, escaped)
                    self.assertEqual(runtime.experiences_of(run_id)[0].proposal.expected_value, escaped)
                    self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)

    def test_surrogate_in_record_id_is_denied_with_readable_trace(self) -> None:
        for label, char in SURROGATES:
            for permission, proposal in _both_tools("alpha" + char):
                with self.subTest(entrada=label, permissao=permission):
                    with tempfile.TemporaryDirectory() as tmp:
                        runtime, run_id = _run(Path(tmp), permission, proposal, {})
                        _assert_denied_before_call(self, runtime, run_id)

    def test_surrogate_in_task_is_refused_without_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(JanusError):
                _request("read_record", "ler \udcff")
            self.assertFalse((Path(tmp) / "runs").exists())


def _request(permission: str, task: str = "ler o registro alpha") -> OpenRunRequest:
    return OpenRunRequest("arthur", permission, Budget(2, 1000, 2), True, "model-a", task)


def _run(root: Path, permission: str, proposal: Proposal, records: dict[str, str]) -> tuple[Runtime, str]:
    runtime = Runtime(root, records, ManualClock())
    run_id = runtime.open_run(_request(permission))
    runtime.step(run_id, ScriptedAdapter("model-a", (proposal,)))
    return runtime, run_id


def _read(record_id: str, expected_value: str = "") -> Proposal:
    return Proposal.from_mapping("read_record", {"record_id": record_id}, expected_value)


def _both_tools(record_id: str) -> tuple[tuple[str, Proposal], ...]:
    delete = Proposal.from_mapping(
        "delete_record", {"record_id": record_id, "idempotency_key": "chave-1"}, ""
    )
    return (("read_record", _read(record_id)), ("delete_record", delete))


def _assert_denied_before_call(test: unittest.TestCase, runtime: Runtime, run_id: str) -> None:
    entry = runtime.trace_of(run_id)[0]
    test.assertEqual(entry.decision.gate, "negar")
    test.assertEqual(entry.decision.reason, SCHEMA_REASON)
    test.assertEqual(runtime.read_calls(), ())
    test.assertEqual(runtime.irreversible_calls(), ())
    test.assertEqual(list_pending(runtime, run_id), ())
    test.assertEqual(len(runtime.experiences_of(run_id)), 1)
    test.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)


if __name__ == "__main__":
    unittest.main()
