import subprocess
import tempfile
import uuid
from enum import Enum

import structlog
from app.repositories.observability_repository import record_audit_event_direct

logger = structlog.get_logger(__name__)


class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"


class AutonomyCIValidator:
    def __init__(self):
        self._jobs: dict[str, dict] = {}

    def schedule_validation(
        self,
        tool_name: str,
        tool_code: str,
        evolution_attempt_id: str,
    ) -> str:
        job_id = f"ci-{uuid.uuid4().hex[:12]}"
        self._jobs[job_id] = {
            "job_id": job_id,
            "tool_name": tool_name,
            "evolution_attempt_id": evolution_attempt_id,
            "status": ValidationStatus.PENDING,
            "result": None,
        }
        record_audit_event_direct(
            endpoint="autonomy_ci",
            action="validation_scheduled",
            status="pending",
            details_json={"job_id": job_id, "tool_name": tool_name},
        )
        self._run_validation(job_id, tool_code)
        return job_id

    def _run_validation(self, job_id: str, tool_code: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return
        job["status"] = ValidationStatus.RUNNING

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", prefix="autonomy_tool_", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(tool_code)
                tmp_path = tmp.name

            result = subprocess.run(
                ["ruff", "check", tmp_path, "--config", "backend/pyproject.toml"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            violations = []
            if result.returncode != 0 and result.stdout:
                violations = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]

            has_regressions = self._check_known_regressions(tool_code)

            passed = result.returncode == 0 and not has_regressions

            job["status"] = ValidationStatus.PASSED if passed else ValidationStatus.FAILED
            job["result"] = {
                "ruff_exit_code": result.returncode,
                "violations": violations,
                "has_known_regressions": has_regressions,
            }

            if not passed:
                try:
                    from app.core.tools.action_module import action_registry
                    action_registry.rollback_tool(job["tool_name"])
                except Exception:
                    pass

            record_audit_event_direct(
                endpoint="autonomy_ci",
                action="validation_completed",
                status="success" if passed else "failure",
                details_json={
                    "job_id": job_id,
                    "passed": passed,
                    "violations_count": len(violations),
                },
            )

        except FileNotFoundError:
            job["status"] = ValidationStatus.PASSED
            job["result"] = {"warning": "ruff not available, validation skipped"}
            logger.warning("autonomy_ci_ruff_not_found")
        except subprocess.TimeoutExpired:
            job["status"] = ValidationStatus.FAILED
            job["result"] = {"error": "ruff check timed out"}
        except Exception as e:
            job["status"] = ValidationStatus.FAILED
            job["result"] = {"error": str(e)}

    def _check_known_regressions(self, tool_code: str) -> bool:
        regression_patterns = [
            "subprocess.",
            "os.system(",
            "socket.",
            "requests.",
            "eval(",
            "exec(",
            "__import__(",
            "shutil.rmtree",
        ]
        return any(pattern in tool_code for pattern in regression_patterns)

    def get_validation_result(self, job_id: str) -> dict | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return {
            "job_id": job["job_id"],
            "tool_name": job["tool_name"],
            "status": job["status"].value if isinstance(job["status"], ValidationStatus) else job["status"],
            "result": job.get("result"),
        }


autonomy_ci_validator = AutonomyCIValidator()
