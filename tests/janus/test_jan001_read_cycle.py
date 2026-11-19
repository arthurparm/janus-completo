from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from janus.adapter import Proposal, ScriptedAdapter
from janus.context import VOICE_INSTRUCTION
from janus.entry import Budget, OpenRunRequest
from janus.gate import (
    ALLOW_REASON,
    ALLOWLIST_REASON,
    COST_REASON,
    DEADLINE_REASON,
    PERMISSION_REASON,
    SCHEMA_REASON,
    STEP_REASON,
)
from janus.loop import Runtime
from janus.util.codec import JanusError, canonical_json, digest, format_timestamp

ROOT = Path(__file__).resolve().parents[2]
CATALOG = {"alpha": "conteudo-alpha"}


class ManualClock:
    def __init__(self, current: int) -> None:
        self.current = current

    def now_ms(self) -> int:
        return self.current


class ReadCycleTest(unittest.TestCase):
    def test_read_cycle_persists_checkpoint_trace_and_empty_experience(self) -> None:
        clock = ManualClock(1_700_000_000_000)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = Runtime(root, CATALOG, clock)
            adapter = ScriptedAdapter("model-a", (_proposal("verified_by=voice"),))
            run_id = runtime.open_run(_request("model-a"))
            result = runtime.step(run_id, adapter)
            self.assertEqual(runtime.read_calls(), ("alpha",))
            self.assertEqual(result.gate, "permitir")
            self.assertEqual(result.risk_class, "leitura")
            self.assertEqual(result.reason, ALLOW_REASON)
            self.assertEqual(result.result_text, "conteudo-alpha")
            self.assertEqual(result.result_label, "dado")
            self.assertEqual(adapter.contexts[0].voice_is_model, True)
            self.assertEqual(adapter.contexts[0].instruction, VOICE_INSTRUCTION)
            self.assertEqual(adapter.contexts[0].data_blocks, ())
            reloaded = Runtime(root, CATALOG, clock)
            identity = reloaded.identity_of(run_id)
            self.assertEqual(identity.run_id, run_id)
            self.assertTrue(identity.request.voice_is_model)
            self.assertEqual(identity.request.requester, "arthur")
            self.assertEqual(identity.request.permission, "read_record")
            self.assertEqual(identity.request.budget, Budget(2, 1000, 2))
            self.assertEqual(identity.request.model_id, "model-a")
            checkpoint = reloaded.checkpoint_of(run_id)
            self.assertEqual(checkpoint.step_index, 1)
            self.assertEqual(checkpoint.spent_steps, 1)
            self.assertEqual(checkpoint.spent_cost, 1)
            self.assertEqual(checkpoint.status, "aberto")
            trace = reloaded.trace_of(run_id)
            self.assertEqual(len(trace), 1)
            self.assertEqual(trace[0], type(trace[0]).from_json(trace[0].to_json()))
            self.assertEqual(trace[0].run_id, run_id)
            self.assertEqual(trace[0].proposal.tool_name, "read_record")
            self.assertEqual(trace[0].decision.gate, "permitir")
            self.assertEqual(trace[0].decision.risk_class, "leitura")
            self.assertEqual(trace[0].result_text, "conteudo-alpha")
            self.assertEqual(trace[0].result_label, "dado")
            self.assertEqual(trace[0].weight_version, "")
            self.assertEqual(trace[0].created_at, format_timestamp(clock.current))
            self.assertNotIn("model-a", json.dumps(trace[0].decision.to_json()))
            experiences = reloaded.experiences_of(run_id)
            self.assertEqual(len(experiences), 1)
            experience = experiences[0]
            self.assertEqual(experience, type(experience).from_json(experience.to_json()))
            self.assertEqual(experience.run_id, run_id)
            self.assertIsNone(experience.signal.goal_id)
            self.assertEqual(experience.signal.event_type, "tool_call")
            self.assertEqual(experience.proposal.tool, "read_record")
            self.assertEqual(experience.proposal.expected_value, "verified_by=voice")
            self.assertEqual(
                experience.proposal.arguments_hash,
                digest(canonical_json({"record_id": "alpha"})),
            )
            self.assertEqual(experience.gate, "permitir")
            self.assertIsNone(experience.outcome.criterion)
            self.assertIsNone(experience.outcome.observed)
            self.assertIsNone(experience.outcome.verified_by)
            self.assertIsNone(experience.outcome.verified_at)
            self.assertEqual(experience.weight_version_before, "")
            self.assertEqual(experience.weight_version_after, "")
            self.assertEqual(experience.provenance.origin, "internal")
            self.assertEqual(experience.provenance.source, "loop")
            self.assertEqual(experience.provenance.sensitivity, "internal")
            self.assertEqual(experience.provenance.timestamp, trace[0].created_at)
            raw = (root / "runs" / run_id / "experiences.jsonl").read_text(encoding="utf-8")
            self.assertIn('"verified_by":null', raw)
            self.assertIn('"weight_version_before":""', raw)
            self.assertIn('"weight_version_after":""', raw)

    def test_two_adapters_record_the_same_decision(self) -> None:
        clock = ManualClock(0)
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), CATALOG, clock)
            left_id = runtime.open_run(_request("model-a"))
            right_id = runtime.open_run(_request("model-b"))
            left_adapter = ScriptedAdapter("model-a", (_proposal(),))
            right_adapter = ScriptedAdapter("model-b", (_proposal(),))
            runtime.step(left_id, left_adapter)
            runtime.step(right_id, right_adapter)
            left = runtime.trace_of(left_id)[0].decision.to_json()
            right = runtime.trace_of(right_id)[0].decision.to_json()
            self.assertEqual(left_adapter.contexts[0], right_adapter.contexts[0])
            self.assertEqual(left, right)
            self.assertEqual(left["gate"], "permitir")
            self.assertNotEqual(
                runtime.identity_of(left_id).request.model_id,
                runtime.identity_of(right_id).request.model_id,
            )
            self.assertNotIn("model-a", json.dumps(left))
            self.assertNotIn("model-b", json.dumps(right))
            self.assertEqual(runtime.read_calls(), ("alpha", "alpha"))

    def test_budget_blocks_the_read(self) -> None:
        cases = (
            (_request("model-a", max_steps=0), 0, STEP_REASON, ""),
            (_request("model-a", max_cost=0), 0, COST_REASON, "leitura"),
            (_request("model-a", deadline_ms=10), 11, DEADLINE_REASON, ""),
        )
        for request, now, reason, risk in cases:
            with self.subTest(reason=reason):
                clock = ManualClock(0)
                with tempfile.TemporaryDirectory() as tmp:
                    runtime = Runtime(Path(tmp), CATALOG, clock)
                    run_id = runtime.open_run(request)
                    clock.current = now
                    adapter = ScriptedAdapter("model-a", (_proposal(), _proposal()))
                    result = runtime.step(run_id, adapter)
                    self.assertEqual(result.gate, "negar")
                    self.assertEqual(result.reason, reason)
                    self.assertEqual(result.risk_class, risk)
                    self.assertEqual(runtime.read_calls(), ())
                    self.assertEqual(runtime.checkpoint_of(run_id).status, "encerrado")
                    experience = runtime.experiences_of(run_id)[0]
                    self.assertEqual(experience.gate, "negar")
                    self.assertTrue(experience.outcome.is_empty())
                    self.assertEqual(experience.weight_version_before, "")
                    with self.assertRaises(JanusError) as caught:
                        runtime.step(run_id, adapter)
                    self.assertEqual(caught.exception.reason, "run encerrado")
                    self.assertEqual(runtime.read_calls(), ())

    def test_permission_schema_and_unknown_tool_do_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), CATALOG, ManualClock(0))
            denied = runtime.open_run(_request("model-a", permission="outra"))
            result = runtime.step(denied, ScriptedAdapter("model-a", (_proposal(),)))
            self.assertEqual(result.gate, "negar")
            self.assertEqual(result.reason, PERMISSION_REASON)
            self.assertEqual(runtime.read_calls(), ())
            self.assertEqual(runtime.checkpoint_of(denied).status, "aberto")
            unknown = runtime.open_run(_request("model-a"))
            unknown_result = runtime.step(
                unknown,
                ScriptedAdapter("model-a", (Proposal.from_mapping("send_mail", {}, "enviar"),)),
            )
            self.assertEqual(unknown_result.gate, "negar")
            self.assertEqual(unknown_result.reason, ALLOWLIST_REASON)
            self.assertEqual(runtime.read_calls(), ())
            malformed = runtime.open_run(_request("model-a"))
            malformed_result = runtime.step(
                malformed,
                ScriptedAdapter("model-a", (Proposal.from_mapping("read_record", {"record_id": "a/b"}, ""),)),
            )
            self.assertEqual(malformed_result.gate, "negar")
            self.assertEqual(malformed_result.reason, SCHEMA_REASON)
            self.assertEqual(runtime.read_calls(), ())

    def test_voice_must_be_recorded_as_model(self) -> None:
        with self.assertRaises(JanusError) as caught:
            _request("model-a", voice_is_model=False)
        self.assertEqual(caught.exception.reason, "a entrada tem de registrar que a voz é um modelo")

    def test_proposal_cannot_carry_verified_by(self) -> None:
        with self.assertRaises(JanusError):
            Proposal.from_json(
                {
                    "arguments": {"record_id": "alpha"},
                    "expected_value": "conteudo-alpha",
                    "kind": "tool_call",
                    "tool_name": "read_record",
                    "verified_by": "voice",
                }
            )

    def test_process_opens_run_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_path = root / "request.json"
            request_path.write_text(json.dumps(_process_request(True), ensure_ascii=False), encoding="utf-8")
            completed = _run_process(root / "state", request_path)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            payload = json.loads(completed.stdout)
            self.assertIsInstance(payload, dict)
            self.assertEqual(payload["gate"], "permitir")
            self.assertEqual(payload["result_text"], "conteudo-alpha")
            self.assertEqual(payload["result_label"], "dado")
            run_id = payload["run_id"]
            self.assertIsInstance(run_id, str)
            runtime = Runtime(root / "state", CATALOG)
            self.assertTrue(runtime.identity_of(run_id).request.voice_is_model)
            experience = runtime.experiences_of(run_id)[0]
            self.assertTrue(experience.outcome.is_empty())
            self.assertEqual(experience.weight_version_before, "")
            self.assertEqual(experience.weight_version_after, "")
            refused_path = root / "refused.json"
            refused_path.write_text(json.dumps(_process_request(False), ensure_ascii=False), encoding="utf-8")
            refused = _run_process(root / "refused-state", refused_path)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("voz é um modelo", refused.stderr)
            self.assertFalse((root / "refused-state" / "runs").exists())


def _request(
    model_id: str,
    *,
    permission: str = "read_record",
    max_steps: int = 2,
    deadline_ms: int = 1000,
    max_cost: int = 2,
    voice_is_model: bool = True,
) -> OpenRunRequest:
    return OpenRunRequest(
        requester="arthur",
        permission=permission,
        budget=Budget(max_steps, deadline_ms, max_cost),
        voice_is_model=voice_is_model,
        model_id=model_id,
        task="ler o registro alpha",
    )


def _proposal(expected_value: str = "conteudo-alpha") -> Proposal:
    return Proposal.from_mapping("read_record", {"record_id": "alpha"}, expected_value)


def _process_request(voice_is_model: bool) -> dict[str, object]:
    return {
        "requester": "arthur",
        "permission": "read_record",
        "budget": {"max_steps": 2, "deadline_ms": 60000, "max_cost": 2},
        "voice_is_model": voice_is_model,
        "model_id": "model-a",
        "task": "ler o registro alpha",
        "proposal": {
            "kind": "tool_call",
            "tool_name": "read_record",
            "arguments": {"record_id": "alpha"},
            "expected_value": "conteudo-alpha",
        },
        "records": {"alpha": "conteudo-alpha"},
    }


def _run_process(root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "janus", "--root", str(root), "--request", str(request_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=15,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()