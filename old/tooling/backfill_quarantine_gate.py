#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = REPO_ROOT / "backend" / "scripts" / "run_backfill_quarantine_gate.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Wrapper operacional do gate de backfill/quarentena antes de constraints. "
            "Encaminha para backend/scripts/run_backfill_quarantine_gate.py."
        )
    )
    parser.add_argument("--mode", choices=("full", "sql-only", "neo4j-only"), default="full")
    parser.add_argument("--apply-constraints", action="store_true")
    parser.add_argument("--neo4j-backfill-limit", type=int, default=None)
    parser.add_argument("--neo4j-audit-output", default="")
    parser.add_argument("--report", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cmd = [sys.executable, str(GATE_SCRIPT), "--mode", str(args.mode)]
    if args.apply_constraints:
        cmd.append("--apply-constraints")
    if args.neo4j_backfill_limit is not None:
        cmd.extend(["--neo4j-backfill-limit", str(args.neo4j_backfill_limit)])
    if args.neo4j_audit_output:
        cmd.extend(["--neo4j-audit-output", str(args.neo4j_audit_output)])
    if args.report:
        cmd.extend(["--report", str(args.report)])
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
