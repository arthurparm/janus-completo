from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text

REPO_APP_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_APP_ROOT) not in sys.path:
    sys.path.append(str(REPO_APP_ROOT))

from app.core.security.redaction import redact_sensitive_payload
from app.db import db


@dataclass(frozen=True)
class Scenario:
    key: str
    tool_name: str
    args: dict[str, Any]


def _default_scenarios() -> list[Scenario]:
    return [
        Scenario(
            key="low_readonly",
            tool_name="list_directory",
            args={"path": "/app/workspace"},
        ),
        Scenario(
            key="medium_write",
            tool_name="write_file",
            args={
                "file_path": "workspace/demo-approval-checklist.md",
                "content": "Checklist PX-004\n- Revisar risco\n- Confirmar contexto\n",
                "requester_email": "ops@example.com",
            },
        ),
        Scenario(
            key="high_command",
            tool_name="execute_shell",
            args={
                "command": "rm -rf /tmp/janus-demo",
                "justification": "cleanup temp workspace",
                "api_token": "sk-demo-secret-token-1234567890",
            },
        ),
    ]


def seed_pending_actions(*, user_id: str, reset: bool = True) -> dict[str, Any]:
    session = db.get_session_direct()
    scenarios = _default_scenarios()

    try:
        deleted = 0
        if reset:
            deleted_result = session.execute(
                text(
                    """
                    DELETE FROM pending_actions
                    WHERE user_id = :user_id
                      AND run_id IS NULL
                      AND cycle IS NULL
                    """
                ),
                {"user_id": user_id},
            )
            deleted = int(getattr(deleted_result, "rowcount", 0) or 0)

        created: list[dict[str, Any]] = []
        for scenario in scenarios:
            safe_args = redact_sensitive_payload(scenario.args)
            insert_result = session.execute(
                text(
                    """
                    INSERT INTO pending_actions (user_id, tool_name, args_json, run_id, cycle, status)
                    VALUES (:user_id, :tool_name, :args_json, NULL, NULL, 'pending')
                    RETURNING id
                    """
                ),
                {
                    "user_id": user_id,
                    "tool_name": scenario.tool_name,
                    "args_json": json.dumps(safe_args, ensure_ascii=False),
                },
            )
            inserted_id = int(insert_result.scalar())
            created.append(
                {
                    "id": inserted_id,
                    "scenario": scenario.key,
                    "tool_name": scenario.tool_name,
                    "status": "pending",
                }
            )

        session.commit()
        return {"user_id": user_id, "reset": reset, "deleted": deleted, "created": created}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Seed deterministic pending-approval scenarios for reproducible UX/Admin testing."
    )
    parser.add_argument("--user-id", default="seed-admin")
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args()

    result = seed_pending_actions(user_id=str(args.user_id), reset=not bool(args.no_reset))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
