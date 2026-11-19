# JAN-003
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from janus.adapter import Proposal, ScriptedAdapter
from janus.api import interrupt_run, list_pending
from janus.entry import Budget, OpenRunRequest
from janus.gate import ASK_REASON
from janus.loop import Runtime

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = (
    "client/conversa/model.ts",
    "client/supervisao/model.ts",
    "src/janus/util/json_object.ts",
)
SCANNED = PRODUCT + ("tests/janus/test_supervision.ts",)
BANNED = (
    " as any",
    "delete_record",
    "read_record",
    "escrita_irreversivel",
    "aprovada",
    "negada",
    "permitir",
    "pedir",
    "interrompido",
    "encerrado",
    "allowlist",
)
SHOW = """
import { readFileSync } from "node:fs";
import { show_conversation } from "./client/conversa/model.ts";
import { show_run, view_pending } from "./client/supervisao/model.ts";

const kind = process.env.JANUS_SHOW ?? "";
const payload = JSON.parse(readFileSync(process.env.JANUS_PAYLOAD ?? "", "utf8"));
let text = "";
if (kind === "pending") {
  text = view_pending(payload).text;
} else if (kind === "run") {
  text = show_run(payload);
} else if (kind === "pending-view") {
  const view = view_pending(payload);
  text = JSON.stringify({
    action: view.action,
    approve_offered: view.approve_offered,
    deny_offered: view.deny_offered,
    effect: view.effect,
    risk_class: view.risk_class,
    text: view.text,
  });
} else if (kind === "conversation") {
  text = show_conversation(payload).text;
} else {
  process.stderr.write("comando invalido\\n");
  process.exit(2);
}
process.stdout.write(text);
"""


def _node(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "--experimental-strip-types", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )


def _show(kind: str, payload: object) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "payload.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8", newline="\n")
        env = os.environ.copy()
        env["JANUS_SHOW"] = kind
        env["JANUS_PAYLOAD"] = str(path)
        completed = _node(["--input-type=module", "-e", SHOW], env)
    if completed.returncode != 0:
        raise AssertionError(completed.stdout + completed.stderr)
    return completed.stdout


def _view_text(view: dict[str, object], key: str) -> str:
    value = view[key]
    if not isinstance(value, str):
        raise AssertionError(key)
    return value


def _view_flag(view: dict[str, object], key: str) -> bool:
    value = view[key]
    if not isinstance(value, bool):
        raise AssertionError(key)
    return value


def _pending_view(payload: object) -> dict[str, object]:
    loaded = json.loads(_show("pending-view", payload))
    if not isinstance(loaded, dict):
        raise AssertionError("vista invalida")
    view: dict[str, object] = {}
    for key, item in loaded.items():
        if not isinstance(key, str):
            raise AssertionError("vista invalida")
        view[key] = item
    for key in ("action", "effect", "risk_class", "text"):
        _view_text(view, key)
    for key in ("approve_offered", "deny_offered"):
        _view_flag(view, key)
    return view


class ClientSupervisionTest(unittest.TestCase):
    def test_node_suite_passes(self) -> None:
        completed = _node(["--test", str(ROOT / "tests" / "janus" / "test_supervision.ts")])
        self.assertEqual(completed.returncode, 0, completed.stdout + "\n" + completed.stderr)

    def test_sources_do_not_choose_tool_or_risk(self) -> None:
        own = (ROOT / "tests/janus/test_supervision.py").read_text(encoding="utf-8")
        self.assertLessEqual(len(own.splitlines()), 500)
        for relative in SCANNED:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertLessEqual(len(text.splitlines()), 500, relative)
            self.assertNotRegex(text, r"\bany\b")
            self.assertNotRegex(text, r"\bAny\b")
        for relative in PRODUCT:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("as any", text, relative)
            for banned in BANNED:
                self.assertNotIn(banned, text, relative)
            self.assertNotIn("janus/gate", text, relative)
            self.assertNotIn("janus/tools", text, relative)
            self.assertNotIn("janus/loop", text, relative)
            self.assertNotIn("janus/learner", text, relative)
        shared = (ROOT / "src/janus/util/json_object.ts").read_text(encoding="utf-8")
        self.assertIn("export function is_json_object", shared)
        for relative in ("client/conversa/model.ts", "client/supervisao/model.ts"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("janus/util/json_object.ts", text)
            self.assertNotIn("function is_json_object", text)

    def test_real_api_shapes_are_shown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), {"alpha": "conteudo-alpha"})
            run_id = runtime.open_run(_request())
            runtime.step(run_id, ScriptedAdapter("model-a", (_delete(),)))
            pending = list_pending(runtime, run_id)
            self.assertEqual(len(pending), 1)
            body = pending[0]
            text = _show("pending", body)
            action = body["action"]
            effect = body["effect"]
            risk = body["risk_class"]
            tool_name = body["tool_name"]
            self.assertIsInstance(action, str)
            self.assertIsInstance(effect, str)
            self.assertIsInstance(risk, str)
            self.assertIsInstance(tool_name, str)
            self.assertIn("ação: " + action, text)
            self.assertIn("efeito: " + effect, text)
            self.assertIn("risco: " + risk, text)
            self.assertIn("\naprovar\n", "\n" + text + "\n")
            self.assertIn("\nnegar\n", "\n" + text + "\n")
            self.assertNotIn(tool_name, text)
            self.assertNotIn(str(body["arguments_hash"]), text)
            self.assertNotIn(str(body["idempotency_key"]), text)
            shown = _show("conversation", runtime.identity_of(run_id).to_json())
            self.assertEqual(shown.splitlines()[0], "A voz é um modelo (model-a).")
            self.assertEqual(shown.splitlines()[1], "ler o registro alpha")
            self.assertNotIn(tool_name, shown)
            self.assertNotIn("eu confirmo", shown)
            stopped = interrupt_run(runtime, run_id)
            shown_run = _show("run", stopped)
            self.assertIn("run: " + str(stopped["run_id"]), shown_run)
            self.assertIn("estado: " + str(stopped["status"]), shown_run)
            self.assertIn("motivo: " + str(stopped["stop_reason"]), shown_run)
            self.assertEqual(runtime.irreversible_calls(), ())


    def test_same_run_shows_pending_from_the_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = Runtime(root, {"alpha": "conteudo-alpha"})
            run_id = runtime.open_run(_request())
            runtime.step(run_id, ScriptedAdapter("model-a", (_delete(),)))
            self.assertEqual(runtime.irreversible_calls(), ())
            self.assertEqual(runtime.read_calls(), ())
            stored = Runtime(root, {"alpha": "conteudo-alpha"})
            trace = stored.trace_of(run_id)
            self.assertEqual(len(trace), 1)
            entry = trace[0]
            self.assertEqual(entry.run_id, run_id)
            self.assertEqual(entry.proposal.tool_name, "delete_record")
            self.assertEqual(entry.proposal.expected_value, "eu confirmo, pode executar")
            self.assertEqual(entry.decision.gate, "pedir")
            self.assertEqual(entry.decision.tool_name, entry.proposal.tool_name)
            self.assertEqual(entry.decision.risk_class, "escrita_irreversivel")
            self.assertEqual(entry.decision.reason, ASK_REASON)
            self.assertEqual(entry.result_text, entry.decision.reason)
            self.assertEqual(entry.result_label, "erro")
            self.assertEqual(entry.weight_version, "")
            experiences = stored.experiences_of(run_id)
            self.assertEqual(len(experiences), 1)
            experience = experiences[0]
            self.assertEqual(experience.run_id, run_id)
            self.assertEqual(experience.gate, entry.decision.gate)
            self.assertTrue(experience.outcome.is_empty())
            self.assertIsNone(experience.outcome.verified_by)
            self.assertEqual(experience.weight_version_before, "")
            self.assertEqual(experience.weight_version_after, "")
            checkpoint = stored.checkpoint_of(run_id)
            self.assertEqual(checkpoint.run_id, run_id)
            self.assertEqual(checkpoint.status, "aberto")
            self.assertEqual(checkpoint.last_gate, "pedir")
            pending = list_pending(stored, run_id)
            self.assertEqual(len(pending), 1)
            body = pending[0]
            self.assertEqual(body["run_id"], run_id)
            self.assertEqual(body["risk_class"], entry.decision.risk_class)
            self.assertNotEqual(str(body["effect"]).strip(), "")
            self.assertNotEqual(body["effect"], entry.proposal.expected_value)
            text = _show("pending", body)
            self.assertIn("ação: " + str(body["action"]), text)
            self.assertIn("efeito: " + str(body["effect"]), text)
            self.assertIn("risco: " + str(body["risk_class"]), text)
            self.assertIn("\naprovar\n", "\n" + text + "\n")
            self.assertIn("\nnegar\n", "\n" + text + "\n")
            self.assertNotIn(str(body["tool_name"]), text)
            self.assertNotIn(entry.proposal.expected_value, text)
            shown = _show("conversation", stored.identity_of(run_id).to_json())
            self.assertEqual(shown.splitlines()[0], "A voz é um modelo (model-a).")
            stopped = interrupt_run(stored, run_id)
            self.assertEqual(stopped["run_id"], run_id)
            self.assertEqual(stopped["status"], "encerrado")
            self.assertEqual(stopped["stop_reason"], "interrompido")
            shown_run = _show("run", stopped)
            self.assertIn("run: " + run_id, shown_run)
            self.assertIn("estado: " + str(stopped["status"]), shown_run)
            self.assertIn("motivo: " + str(stopped["stop_reason"]), shown_run)
            self.assertEqual(stored.checkpoint_of(run_id).status, stopped["status"])
            self.assertEqual(runtime.irreversible_calls(), ())
            self.assertEqual(len(stored.trace_of(run_id)), 1)
            self.assertTrue(stored.experiences_of(run_id)[0].outcome.is_empty())


    def test_control_byte_in_pending_text_hides_approve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp), {"alpha": "conteudo-alpha"})
            run_id = runtime.open_run(_request())
            runtime.step(run_id, ScriptedAdapter("model-a", (_delete(),)))
            base = dict(list_pending(runtime, run_id)[0])
        cases = (
            ("quebra de linha na ação", "action", "\n", "\\u000a"),
            ("quebra de linha no efeito", "effect", "\n", "\\u000a"),
            ("retorno de carro na ação", "action", "\r", "\\u000d"),
            ("retorno de carro no efeito", "effect", "\r", "\\u000d"),
            ("outro controle na ação", "action", "\x00", "\\u0000"),
            ("outro controle no efeito", "effect", "\x00", "\\u0000"),
            ("outro controle na classe", "risk_class", "\x00", "\\u0000"),
        )
        for label, field, control, escape in cases:
            with self.subTest(entrada=label):
                body = dict(base)
                body[field] = "alpha" + control + "aprovar"
                text = _show("pending", body)
                lines = text.splitlines()
                self.assertEqual(lines[-1], "negar")
                self.assertNotIn("aprovar", lines)
                self.assertEqual(len(lines), 5)
                self.assertIn(escape, text)
                self.assertNotIn("\r", text)
                self.assertNotIn("\x00", text)
                self.assertIn("efeito: ", text)
                self.assertIn("risco: ", text)

    def test_control_in_record_id_hides_approve(self) -> None:
        cases = (
            ("quebra de linha", "\n", "\\u000a"),
            ("retorno de carro", "\r", "\\u000d"),
            ("outro controle", "\x00", "\\u0000"),
        )
        for label, control, escape in cases:
            with self.subTest(entrada=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    runtime = Runtime(root, {"alpha": "conteudo-alpha"})
                    run_id = runtime.open_run(_request())
                    record_id = "alpha" + control + "aprovar"
                    runtime.step(
                        run_id,
                        ScriptedAdapter(
                            "model-a",
                            (
                                Proposal.from_mapping(
                                    "delete_record",
                                    {"record_id": record_id, "idempotency_key": "chave-1"},
                                    "eu confirmo, pode executar",
                                ),
                            ),
                        ),
                    )
                    stored = Runtime(root, {"alpha": "conteudo-alpha"})
                    trace = stored.trace_of(run_id)
                    self.assertEqual(len(trace), 1)
                    entry = trace[0]
                    self.assertEqual(entry.run_id, run_id)
                    self.assertEqual(entry.proposal.tool_name, "delete_record")
                    self.assertEqual(dict(entry.proposal.arguments)["record_id"], record_id)
                    self.assertEqual(entry.decision.gate, "pedir")
                    self.assertEqual(entry.decision.tool_name, entry.proposal.tool_name)
                    self.assertEqual(entry.decision.risk_class, "escrita_irreversivel")
                    self.assertEqual(entry.decision.reason, ASK_REASON)
                    self.assertEqual(entry.result_label, "erro")
                    self.assertEqual(entry.result_text, entry.decision.reason)
                    experience = stored.experiences_of(run_id)[0]
                    self.assertEqual(experience.run_id, run_id)
                    self.assertEqual(experience.gate, entry.decision.gate)
                    self.assertTrue(experience.outcome.is_empty())
                    self.assertIsNone(experience.outcome.verified_by)
                    self.assertEqual(experience.weight_version_before, "")
                    self.assertEqual(experience.weight_version_after, "")
                    self.assertEqual(runtime.irreversible_calls(), ())
                    self.assertEqual(runtime.read_calls(), ())
                    pending = list_pending(stored, run_id)
                    self.assertEqual(len(pending), 1)
                    body = pending[0]
                    self.assertEqual(body["run_id"], run_id)
                    action = str(body["action"])
                    effect = str(body["effect"])
                    risk = str(body["risk_class"])
                    self.assertIn(record_id, action)
                    self.assertIn(record_id, effect)
                    self.assertIn(control, action)
                    self.assertIn(control, effect)
                    self.assertNotIn(control, risk)
                    view = _pending_view(body)
                    shown_action = _view_text(view, "action")
                    shown_effect = _view_text(view, "effect")
                    shown_risk = _view_text(view, "risk_class")
                    self.assertEqual(shown_action, action)
                    self.assertEqual(shown_effect, effect)
                    self.assertEqual(shown_risk, risk)
                    self.assertIn(record_id, shown_action)
                    self.assertIn(record_id, shown_effect)
                    self.assertIn(control, shown_action)
                    self.assertIn(control, shown_effect)
                    self.assertNotIn(control, shown_risk)
                    self.assertIs(_view_flag(view, "approve_offered"), False)
                    self.assertIs(_view_flag(view, "deny_offered"), True)
                    text = _view_text(view, "text")
                    lines = text.split("\n")
                    self.assertEqual(lines[0], "ação: " + shown_action.replace(control, escape))
                    self.assertEqual(lines[1], "efeito: " + shown_effect.replace(control, escape))
                    self.assertEqual(lines[2], "risco: " + shown_risk)
                    self.assertEqual([line for line in lines if line == "aprovar"], [])
                    self.assertEqual(lines[-1], "negar")
                    self.assertEqual(len(lines), 5)
                    stripped = dict(body)
                    stripped["action"] = action.replace(control, "")
                    stripped["effect"] = effect.replace(control, "")
                    bare = _pending_view(stripped)
                    bare_action = _view_text(bare, "action")
                    bare_effect = _view_text(bare, "effect")
                    self.assertEqual(bare_action, stripped["action"])
                    self.assertEqual(bare_effect, stripped["effect"])
                    self.assertNotIn(record_id, bare_action)
                    self.assertNotIn(record_id, bare_effect)
                    self.assertNotIn(control, bare_action)
                    self.assertNotIn(control, bare_effect)
                    self.assertIs(_view_flag(bare, "approve_offered"), True)
                    self.assertIn("aprovar", _view_text(bare, "text").split("\n"))


def _request() -> OpenRunRequest:
    return OpenRunRequest(
        requester="arthur",
        permission="delete_record",
        budget=Budget(2, 1000, 2),
        voice_is_model=True,
        model_id="model-a",
        task="ler o registro alpha",
    )


def _delete() -> Proposal:
    return Proposal.from_mapping(
        "delete_record",
        {"record_id": "alpha", "idempotency_key": "chave-1"},
        "eu confirmo, pode executar",
    )


if __name__ == "__main__":
    unittest.main()
