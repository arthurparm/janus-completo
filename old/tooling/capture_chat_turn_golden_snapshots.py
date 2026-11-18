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

from qa.chat_turn_baseline.harness import (  # noqa: E402
    ADDITIONAL_SCENARIOS,
    ADR_SCENARIOS,
    capture_all,
    load_snapshots,
    write_snapshots,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture or verify deterministic REST/SSE chat-turn golden snapshots."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write the current captures.")
    mode.add_argument("--check", action="store_true", help="Compare current captures to disk.")
    return parser


async def _run(*, write: bool) -> int:
    captures = await capture_all()
    if write:
        write_snapshots(REPOSITORY_ROOT, captures)
        print(
            json.dumps(
                {
                    "status": "written",
                    "adr_scenarios": len(ADR_SCENARIOS),
                    "additional_scenarios": len(ADDITIONAL_SCENARIOS),
                    "snapshot_files": len(captures),
                },
                sort_keys=True,
            )
        )
        return 0

    expected = load_snapshots(REPOSITORY_ROOT)
    if captures != expected:
        differing = sorted(
            path
            for path in set(captures) | set(expected)
            if captures.get(path) != expected.get(path)
        )
        print(json.dumps({"status": "mismatch", "files": differing}, indent=2))
        return 1
    print(json.dumps({"status": "match", "snapshot_files": len(captures)}, sort_keys=True))
    return 0


def main() -> int:
    args = _build_parser().parse_args()
    return asyncio.run(_run(write=bool(args.write)))


if __name__ == "__main__":
    raise SystemExit(main())
