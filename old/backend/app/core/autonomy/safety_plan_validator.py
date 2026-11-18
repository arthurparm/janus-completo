import re

import structlog

logger = structlog.get_logger(__name__)

SAFETY_CONFIG_PATHS = frozenset({
    ".env", ".env.pc1", ".env.pc2", "config.py", "settings.py",
    "app/config.py", "app/config/", "app/core/config/",
    "docker-compose", "Dockerfile", "requirements.txt",
})

class SafetyPlanValidator:
    SYSTEM_DIRS = re.compile(r"^/(etc|boot|sys|proc|dev|var/log|var/lib|root)(/.*)?$")

    def validate_plan(self, plan: list[dict], policy=None) -> tuple[bool, list[str]]:
        violations: list[str] = []
        for step in plan:
            step_id = step.get("step_id", "?")
            tool = str(step.get("tool", "") or "").strip()
            params = step.get("tool_params") or {}

            if policy is not None:
                try:
                    if policy.is_permanently_vetoed(tool, params):
                        violations.append(f"Step {step_id}: tool '{tool}' is permanently vetoed")
                except Exception:
                    pass

            if self._affects_security_config(params):
                violations.append(f"Step {step_id}: modifies security configuration files")

            for key, val in params.items():
                val_str = str(val)
                if self._contains_blocked_shell(val_str):
                    violations.append(f"Step {step_id}: param '{key}' contains blocked shell operators")
                if self._is_system_path(val_str):
                    violations.append(f"Step {step_id}: param '{key}' references system path '{val_str}'")

        return len(violations) == 0, violations

    def _affects_security_config(self, params: dict) -> bool:
        for val in params.values():
            val_str = str(val).lower()
            for p in SAFETY_CONFIG_PATHS:
                if p.lower() in val_str:
                    return True
        return False

    def _contains_blocked_shell(self, text: str) -> bool:
        blocked = {"&&", "||", ";", "|", "$(", "`", ">", "<", "\n", "\r"}
        for op in blocked:
            if op in text:
                return True
        return False

    def _is_system_path(self, text: str) -> bool:
        if text.startswith("/") and self.SYSTEM_DIRS.match(text):
            return True
        return False


safety_plan_validator = SafetyPlanValidator()
