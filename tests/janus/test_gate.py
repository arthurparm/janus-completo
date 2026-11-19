import unittest

from janus.entry import Budget
from janus.gate import ALLOW_REASON, STEP_REASON, decide_read


class GateTest(unittest.TestCase):
    def test_read_is_allowed_inside_budget(self) -> None:
        decision = decide_read(
            "read_record",
            (("record_id", "alpha"),),
            "read_record",
            Budget(2, 1000, 2),
            0,
            0,
            0,
            0,
        )
        self.assertEqual(decision.gate, "permitir")
        self.assertEqual(decision.reason, ALLOW_REASON)
        self.assertEqual(decision.risk_class, "leitura")

    def test_exhausted_budget_denies(self) -> None:
        decision = decide_read(
            "read_record",
            (("record_id", "alpha"),),
            "read_record",
            Budget(2, 1000, 2),
            2,
            0,
            0,
            0,
        )
        self.assertEqual(decision.gate, "negar")
        self.assertEqual(decision.reason, STEP_REASON)
        self.assertEqual(decision.risk_class, "")


if __name__ == "__main__":
    unittest.main()
