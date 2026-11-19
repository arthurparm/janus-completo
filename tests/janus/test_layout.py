import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = (
    "src/janus/__init__.py",
    "src/janus/entry.py",
    "src/janus/loop.py",
    "src/janus/context.py",
    "src/janus/adapter.py",
    "src/janus/gate.py",
    "src/janus/state.py",
    "src/janus/trace.py",
    "src/janus/experience.py",
    "src/janus/goals.py",
    "src/janus/learner.py",
    "src/janus/evolution.py",
    "src/janus/api.py",
    "src/janus/__main__.py",
    "src/janus/tools/__init__.py",
    "src/janus/tools/read_record.py",
    "src/janus/util/__init__.py",
    "src/janus/util/codec.py",
    "src/janus/util/pairs.py",
    "tests/janus/test_gate.py",
    "tests/janus/test_jan001_read_cycle.py",
    "client/conversa/model.ts",
    "client/supervisao/model.ts",
)


class LayoutTest(unittest.TestCase):
    def test_required_paths_exist(self) -> None:
        missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_repository_root_has_no_loose_package(self) -> None:
        self.assertFalse((ROOT / "janus" / "__init__.py").is_file())


if __name__ == "__main__":
    unittest.main()
