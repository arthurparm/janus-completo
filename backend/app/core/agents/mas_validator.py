import re

import structlog

logger = structlog.get_logger(__name__)

SAFETY_CONFIG_PATHS = frozenset({
    ".env", ".env.pc1", ".env.pc2", "config.py", "settings.py",
    "app/config.py", "app/config/", "app/core/config/",
    "docker-compose", "Dockerfile", "requirements.txt",
})

VETOED_TOOL_KEYWORDS = frozenset({
    "rm -rf", "del /f", "format ", "shutdown", "reboot",
    "chmod 777", "chmod -R 777", "dd if=",
    "write_system_file", "execute_system_command", "codex_exec", "codex_login",
    "execute_shell", "run_command",
})

BLOCKED_SHELL_OPERATORS = {"&&", "||", ";", "|", "$(", "`", ">", "<", "\n", "\r"}

SYSTEM_DIRS = re.compile(r"^/(etc|boot|sys|proc|dev|var/log|var/lib|root)(/.*)?$")


class MASValidator:
    def validate_tool_call(self, tool_name: str, args: dict, policy=None) -> tuple[bool, str]:
        if policy is not None:
            try:
                if hasattr(policy, 'is_permanently_vetoed'):
                    if policy.is_permanently_vetoed(tool_name, args):
                        return False, f"Tool '{tool_name}' is permanently vetoed"
            except Exception:
                pass

        violations = self._check_tool_args(args)
        if violations:
            return False, "; ".join(violations)

        return True, ""

    def validate_decomposed_plan(self, tasks: list[dict], policy=None) -> tuple[bool, list[str]]:
        violations: list[str] = []
        for i, task in enumerate(tasks):
            desc = str(task.get("description", "") or "").lower()
            agent = str(task.get("agent", "") or "").lower()

            for keyword in VETOED_TOOL_KEYWORDS:
                if keyword in desc:
                    violations.append(f"Task {i}: description references vetoed operation '{keyword}'")

            if policy is not None:
                try:
                    if hasattr(policy, 'is_permanently_vetoed'):
                        args = {"description": desc, "agent": agent}
                        if policy.is_permanently_vetoed("decomposed_task", args):
                            violations.append(f"Task {i}: permanently vetoed by policy")
                except Exception:
                    pass

        return len(violations) == 0, violations

    def _check_tool_args(self, args: dict) -> list[str]:
        violations: list[str] = []
        for key, val in args.items():
            val_str = str(val)

            if self._affects_security_config(key, val_str):
                violations.append(f"arg '{key}' references security config")

            if self._contains_blocked_shell(val_str):
                violations.append(f"arg '{key}' contains blocked shell operators")

            if self._is_system_path(val_str):
                violations.append(f"arg '{key}' references system path")

            for keyword in VETOED_TOOL_KEYWORDS:
                if keyword in val_str.lower():
                    violations.append(f"arg '{key}' references vetoed operation '{keyword}'")
                    break

        return violations

    def _affects_security_config(self, key: str, val_str: str) -> bool:
        combined = f"{key}={val_str}".lower()
        for p in SAFETY_CONFIG_PATHS:
            if p.lower() in combined:
                return True
        return False

    def _contains_blocked_shell(self, text: str) -> bool:
        for op in BLOCKED_SHELL_OPERATORS:
            if op in text:
                return True
        return False

    def _is_system_path(self, text: str) -> bool:
        if text.startswith("/") and SYSTEM_DIRS.match(text):
            return True
        return False


mas_validator = MASValidator()
