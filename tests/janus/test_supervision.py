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
