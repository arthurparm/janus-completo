# JAN-033
from __future__ import annotations

import os
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from janus.adapter import ModelContext, Proposal
from janus.api import approve_pending, interrupt_run
from janus.gate import STEP_REASON
from janus.loop import Runtime
from janus.util.codec import JanusError
from tests.janus.support import alpha_request, delete_proposal, read_proposal, read_runtime

BUSY = "arquivo do run em uso"
# O Windows devolve PermissionError quando leitura e substituição colidem. A falha é plantada
# para a prova valer em qualquer sistema.
_ORIGINAL_READ = Path.read_text
_ORIGINAL_REPLACE = os.replace


class FileCollisionTest(unittest.TestCase):
    def test_interrupt_with_busy_checkpoint_read_writes_the_mark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request())
            with _busy_read("checkpoint.json"):
                with self.assertRaises(JanusError) as caught:
                    interrupt_run(runtime, run_id)
            self.assertEqual(caught.exception.reason, BUSY)
            self.assertEqual(runtime.checkpoint_of(run_id).stop_reason, "interrompido")
            with self.assertRaises(JanusError) as refused:
                runtime.step(run_id, _Adapter())
            self.assertEqual(refused.exception.reason, "run encerrado")
            self.assertEqual(runtime.read_calls(), ())

    def test_interrupt_with_one_busy_read_returns_closed_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request())
            with _busy_read("checkpoint.json", times=1):
                returned = interrupt_run(runtime, run_id)
            self.assertEqual(returned["status"], "encerrado")
            self.assertEqual(returned["stop_reason"], "interrompido")

    def test_interrupt_of_absent_run_with_busy_read_leaves_no_mark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            with self.assertRaises(JanusError) as caught:
                interrupt_run(runtime, "0" * 32)
            self.assertEqual(caught.exception.reason, "run ausente")
            self.assertEqual(tuple(Path(tmp).iterdir()), ())

    def test_reader_open_during_step_keeps_budget_and_step_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request(max_steps=1))
            checkpoint_path = Path(tmp) / "runs" / run_id / "checkpoint.json"
            for _ in range(3):
                _step_with_open_reader(runtime, run_id, checkpoint_path)
            indices = [entry.step_index for entry in runtime.trace_of(run_id)]
            self.assertLessEqual(len(runtime.read_calls()), 1)
            self.assertEqual(len(indices), len(set(indices)))
            self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, len(runtime.read_calls()))

    def test_busy_replace_before_the_tool_refuses_without_effect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request())
            before = runtime.checkpoint_of(run_id)
            with _busy_replace("checkpoint.json"):
                with self.assertRaises(JanusError) as caught:
                    runtime.step(run_id, _Adapter())
            self.assertEqual(caught.exception.reason, BUSY)
            self.assertEqual(runtime.read_calls(), ())
            self.assertEqual(runtime.trace_of(run_id), ())
            self.assertEqual(runtime.experiences_of(run_id), ())
            self.assertEqual(runtime.checkpoint_of(run_id), before)
            self.assertEqual(tuple(Path(tmp).rglob("*.tmp")), ())

    def test_busy_replace_after_the_tool_keeps_spend_and_step_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request(max_steps=1))
            with _busy_replace("checkpoint.json", after=1):
                with self.assertRaises(JanusError) as caught:
                    runtime.step(run_id, _Adapter())
            self.assertEqual(caught.exception.reason, BUSY)
            self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)
            self.assertEqual(len(runtime.experiences_of(run_id)), 1)
            second = runtime.step(run_id, _Adapter())
            self.assertEqual(second.reason, STEP_REASON)
            self.assertEqual(runtime.read_calls(), ("alpha",))
            self.assertEqual([entry.step_index for entry in runtime.trace_of(run_id)], [1, 2])

    def test_one_busy_replace_lets_the_step_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request())
            with _busy_replace("checkpoint.json", times=1):
                result = runtime.step(run_id, _Adapter())
            self.assertEqual(result.gate, "permitir")
            self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)
            self.assertEqual(runtime.checkpoint_of(run_id).last_result_text, "conteudo-alpha")

    def test_busy_pending_after_the_decision_keeps_trace_and_experience(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request(permission="delete_record"))
            adapter = _Adapter(delete_proposal("chave-1"))
            # A primeira leitura é a da decisão. A seguinte é a que grava a pendência.
            with _busy_read("pending.jsonl", after=1):
                with self.assertRaises(JanusError) as caught:
                    runtime.step(run_id, adapter)
            self.assertEqual(caught.exception.reason, BUSY)
            self.assertEqual(runtime.trace_of(run_id)[0].decision.gate, "pedir")
            self.assertEqual(len(runtime.experiences_of(run_id)), 1)
            self.assertEqual(runtime.checkpoint_of(run_id).spent_steps, 1)
            self.assertEqual(runtime.irreversible_calls(), ())

    def test_busy_pending_replace_keeps_pending_written_meanwhile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = read_runtime(Path(tmp))
            run_id = runtime.open_run(alpha_request(permission="delete_record"))
            runtime.step(run_id, _Adapter(delete_proposal("chave-1")))
            first = runtime.pending_of(run_id)[0]
            armed: list[None] = [None]

            def replace(source: Path, target: Path) -> None:
                if target.name == "pending.jsonl" and armed:
                    armed.clear()
                    runtime.step(run_id, _Adapter(delete_proposal("chave-2")))
                    raise PermissionError(13, "arquivo em uso")
                _ORIGINAL_REPLACE(source, target)

            with mock.patch("janus.state.os.replace", side_effect=replace):
                approve_pending(runtime, first.to_json())
            statuses = [(item.idempotency_key, item.status) for item in runtime.pending_of(run_id)]
            self.assertEqual(statuses, [("chave-1", "aprovada"), ("chave-2", "aberta")])


class _Adapter:
    model_id = "model-a"

    def __init__(self, proposal: Proposal | None = None) -> None:
        self._proposal = read_proposal() if proposal is None else proposal

    def propose(self, context: ModelContext) -> Proposal:
        return self._proposal


class _ReaderAdapter(_Adapter):
    """Abre o checkpoint durante o propose. Quem chama o passo fecha depois."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        self.close: Callable[[], None] | None = None

    def propose(self, context: ModelContext) -> Proposal:
        self.close = self._path.open("r", encoding="utf-8").close
        return super().propose(context)


def _step_with_open_reader(runtime: Runtime, run_id: str, path: Path) -> None:
    adapter = _ReaderAdapter(path)
    try:
        runtime.step(run_id, adapter)
    except (JanusError, PermissionError):
        # A recusa é aceita. O que a prova olha é o orçamento e o traço.
        pass
    finally:
        if adapter.close is not None:
            adapter.close()


def _busy_read(name: str, *, after: int = 0, times: int | None = None) -> mock._patch[mock.MagicMock]:
    seen: list[None] = []

    def read(path: Path, encoding: str = "utf-8") -> str:
        if path.name == name:
            seen.append(None)
            if len(seen) > after and (times is None or len(seen) <= after + times):
                raise PermissionError(13, "arquivo em uso")
        return _ORIGINAL_READ(path, encoding=encoding)

    return mock.patch.object(Path, "read_text", autospec=True, side_effect=read)


def _busy_replace(name: str, *, after: int = 0, times: int | None = None) -> mock._patch[mock.MagicMock]:
    seen: list[None] = []

    def replace(source: Path, target: Path) -> None:
        if target.name == name:
            seen.append(None)
            if len(seen) > after and (times is None or len(seen) <= after + times):
                raise PermissionError(13, "arquivo em uso")
        _ORIGINAL_REPLACE(source, target)

    return mock.patch("janus.state.os.replace", side_effect=replace)


if __name__ == "__main__":
    unittest.main()
