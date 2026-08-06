from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.services.db_migration_service import db_migration_service


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_report_path() -> Path:
    target = REPO_ROOT / "outputs" / "qa" / "backfill-quarantine-gate"
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return target / f"report-{stamp}.json"


def _run_python_script(script: Path, args: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(script), *args]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    payload: dict[str, Any] = {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    if proc.stdout.strip():
        try:
            payload["parsed"] = json.loads(proc.stdout)
        except Exception:
            payload["parsed"] = None
    else:
        payload["parsed"] = None
    return payload


def _run_sql_prepare() -> dict[str, Any]:
    return db_migration_service.prepare_constraint_data()


def _run_sql_validate() -> dict[str, Any]:
    return db_migration_service.validate_constraint_readiness()


def _run_sql_apply() -> dict[str, Any]:
    return db_migration_service.apply_prepared_constraints()


def _run_neo4j_step(command: str, extra_args: list[str]) -> dict[str, Any]:
    script = BACKEND_ROOT / "scripts" / "neo4j_noise_maintenance.py"
    return _run_python_script(script, [command, *extra_args])


def _build_report(args: argparse.Namespace) -> dict[str, Any]:
    report: dict[str, Any] = {
        "generated_at": _utc_now(),
        "mode": args.mode,
        "apply_constraints": bool(args.apply_constraints),
        "steps": [],
    }

    sql_prepare = _run_sql_prepare()
    report["steps"].append({"step": "sql_prepare_constraint_data", "result": sql_prepare})

    sql_validate = _run_sql_validate()
    report["steps"].append({"step": "sql_validate_constraint_readiness", "result": sql_validate})

    if args.mode in {"full", "neo4j-only"}:
        neo4j_audit_args = []
        if args.neo4j_audit_output:
            neo4j_audit_args.extend(["--output", args.neo4j_audit_output])
        neo4j_audit = _run_neo4j_step("audit", neo4j_audit_args)
        report["steps"].append({"step": "neo4j_audit", "result": neo4j_audit})

        neo4j_backfill_args: list[str] = []
        if args.neo4j_backfill_limit is not None:
            neo4j_backfill_args.extend(["--limit", str(args.neo4j_backfill_limit)])
        neo4j_backfill = _run_neo4j_step("backfill-entity-canonical", neo4j_backfill_args)
        report["steps"].append({"step": "neo4j_backfill_entity_canonical", "result": neo4j_backfill})

        if args.apply_constraints:
            neo4j_constraints = _run_neo4j_step("ensure-constraints", [])
            report["steps"].append({"step": "neo4j_apply_constraints", "result": neo4j_constraints})
        else:
            report["steps"].append(
                {
                    "step": "neo4j_apply_constraints",
                    "result": {"status": "skipped", "reason": "apply_constraints=false"},
                }
            )

    if args.mode in {"full", "sql-only"}:
        if args.apply_constraints:
            sql_apply = _run_sql_apply()
            report["steps"].append({"step": "sql_apply_prepared_constraints", "result": sql_apply})
        else:
            report["steps"].append(
                {
                    "step": "sql_apply_prepared_constraints",
                    "result": {"status": "skipped", "reason": "apply_constraints=false"},
                }
            )

    final_validate = _run_sql_validate()
    report["steps"].append({"step": "sql_final_constraint_readiness", "result": final_validate})
    report["status"] = "ok" if final_validate.get("status") == "ready" else "blocked"
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa o gate operacional de backfill/quarentena antes de constraints, "
            "com relatório JSON auditável."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("full", "sql-only", "neo4j-only"),
        default="full",
        help="Escopo do gate operacional.",
    )
    parser.add_argument(
        "--apply-constraints",
        action="store_true",
        help="Aplica constraints apenas após a validação de prontidão.",
    )
    parser.add_argument(
        "--neo4j-backfill-limit",
        type=int,
        default=None,
        help="Limite opcional de entidades no backfill do Neo4j.",
    )
    parser.add_argument(
        "--neo4j-audit-output",
        default="",
        help="Caminho opcional para o relatório de audit do Neo4j.",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Caminho opcional do relatório JSON final.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = _build_report(args)
    output_path = Path(args.report) if args.report else _default_report_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
