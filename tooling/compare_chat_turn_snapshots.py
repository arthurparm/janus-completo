from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
for candidate in (str(BACKEND_ROOT), str(REPOSITORY_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from qa.chat_turn_baseline.comparator import compare_current_to_golden  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare current deterministic chat behavior with classified golden snapshots."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the full JSON report; stdout always receives the summary.",
    )
    return parser


async def _run(output: Path | None) -> int:
    report = await compare_current_to_golden(REPOSITORY_ROOT)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 1 if int(report["summary"]["regressions"]) else 0


def main() -> int:
    args = _build_parser().parse_args()
    return asyncio.run(_run(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
