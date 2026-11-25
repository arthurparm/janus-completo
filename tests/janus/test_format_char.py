# JAN-020
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from janus.adapter import Proposal, ScriptedAdapter
from janus.api import list_pending
from janus.entry import Budget, OpenRunRequest
from janus.gate import SCHEMA_REASON
from janus.loop import Runtime
from tests.janus.support import ManualClock


class FormatCharTest(unittest.TestCase):
    def test_format_char_in_record_id_is_denied_before_pending(self) -> None:
        cases = (
            ("inversão de direção", "\u202e"),
            ("isolamento de direção", "\u2067"),
            ("largura zero", "\u200b"),
            ("fora do plano básico", "\U000e0001"),
        )
        for label, char in cases:
            with self.subTest(entrada=label):
                with tempfile.TemporaryDirectory() as tmp:
                    runtime = Runtime(Path(tmp), {}, ManualClock())
                    request = OpenRunRequest(
                        "arthur", "delete_record", Budget(2, 1000, 2), True, "model-a", "apagar"
                    )
                    run_id = runtime.open_run(request)
                    proposal = Proposal.from_mapping(
                        "delete_record",
                        {"record_id": "alpha" + char + "ahpla", "idempotency_key": "chave-1"},
                        "",
                    )
                    result = runtime.step(run_id, ScriptedAdapter("model-a", (proposal,)))
                    self.assertEqual(result.gate, "negar")
                    self.assertEqual(result.reason, SCHEMA_REASON)
                    self.assertEqual(list_pending(runtime, run_id), ())
                    self.assertEqual(runtime.irreversible_calls(), ())


if __name__ == "__main__":
    unittest.main()
