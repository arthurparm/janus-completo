import os
import time
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.tools.action_module import PermissionLevel, ToolMetadata, action_registry

logger = structlog.get_logger(__name__)


class RiskProfile(str):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class PolicyConfig:
    risk_profile: str = RiskProfile.BALANCED
    auto_confirm: bool = True
    allowlist: set[str] = field(default_factory=set)
    blocklist: set[str] = field(default_factory=set)
    capability_allowlist: set[str] = field(default_factory=set)
    scope_allowlist: set[str] = field(default_factory=set)
    command_allowlist: set[str] = field(default_factory=set)
    restricted_command_tools: set[str] = field(default_factory=set)
    command_blocklist_tokens: set[str] = field(default_factory=set)
    require_simulation_for_destructive: bool = True
    max_actions_per_cycle: int = 20
    max_seconds_per_cycle: int = 60

    def __post_init__(self):
        def _parse_csv_set(raw: str) -> set[str]:
            return {item.strip().lower() for item in str(raw or "").split(",") if item.strip()}

        if not self.capability_allowlist:
            self.capability_allowlist = _parse_csv_set(
                os.getenv("CHAT_TOOL_CAPABILITY_ALLOWLIST", "")
            )
        if not self.scope_allowlist:
            self.scope_allowlist = _parse_csv_set(os.getenv("CHAT_TOOL_SCOPE_ALLOWLIST", ""))

        if not self.command_allowlist:
            self.command_allowlist = _parse_csv_set(os.getenv("CHAT_TOOL_COMMAND_ALLOWLIST", ""))

        if not self.restricted_command_tools:
            self.restricted_command_tools = _parse_csv_set(
                os.getenv(
                    "CHAT_TOOL_RESTRICTED_COMMAND_TOOLS",
                    "execute_shell,execute_system_command",
                )
            )

        # Enhanced blocklist tokens (space-agnostic checks)
        self.command_blocklist_tokens = _parse_csv_set(
            os.getenv(
                "CHAT_TOOL_COMMAND_BLOCKLIST",
                "rm -rf,del /f,format ,shutdown,reboot,powershell -enc,curl |,wget |,nc ,netcat ,chmod 777,chmod -R 777,dd if=",
            )
        )

        self.allowlist = {str(item).strip().lower() for item in self.allowlist if str(item).strip()}
        self.blocklist = {str(item).strip().lower() for item in self.blocklist if str(item).strip()}
        self.capability_allowlist = {
            str(item).strip().lower() for item in self.capability_allowlist if str(item).strip()
        }
        self.scope_allowlist = {
            str(item).strip().lower() for item in self.scope_allowlist if str(item).strip()
        }
        self.command_allowlist = {
            str(item).strip().lower() for item in self.command_allowlist if str(item).strip()
        }
        self.restricted_command_tools = {
            str(item).strip().lower()
            for item in self.restricted_command_tools
            if str(item).strip()
        }
        self.command_blocklist_tokens = {
            str(item).strip().lower() for item in self.command_blocklist_tokens if str(item).strip()
        }
        self.require_simulation_for_destructive = (
            str(
                os.getenv(
                    "CHAT_TOOL_REQUIRE_SIMULATION_FOR_DESTRUCTIVE",
                    str(self.require_simulation_for_destructive),
                )
            )
            .strip()
            .lower()
            in {"1", "true", "yes", "on"}
        )


@dataclass
class PolicyDecision:
    allowed: bool
    require_confirmation: bool = False
    reason: str | None = None


@dataclass
class SimulationResult:
    is_destructive: bool
    expected_impact: str
    affected_resources: list[str]
    reversible: bool
    final_risk_level: str
    summary: str
    generated_at: str
    simulation_version: str = "v1"


class PolicyEngine:
    """Basic pre-execution validations for tools."""

    def __init__(self, config: PolicyConfig | None = None):
        self.config = config or PolicyConfig()
        self._cycle_started_at: float = time.time()
        self._actions_in_cycle: int = 0

        self._injection_patterns = [
            "ignore previous instructions",
            "ignore all instructions",
            "ignore the above instructions",
            "override system prompt",
            "delete system prompt",
            "reveal system prompt",
            "show system prompt",
            "you are now unsafe",
            "disable safety protocols",
            "ignore your constraints",
            "act as an unrestricted",
            "jailbreak",
            "developer mode",
        ]
        self._destructive_keywords = (
            "delete",
            "drop",
            "truncate",
            "remove",
            "rm ",
            "wipe",
            "format",
            "shutdown",
            "reboot",
            "kill ",
            "destroy",
        )
        self._irreversible_keywords = (
            "delete",
            "drop",
            "truncate",
            "wipe",
            "format",
            "rm -rf",
        )

    def reset_cycle_quota(self):
        # Reset atômico não é garantido sem lock, mas reduz race condition em uso típico
        self._cycle_started_at = time.time()
        self._actions_in_cycle = 0

    def can_continue_cycle(self) -> bool:
        # Check quota first (atomic read)
        if self.config.max_actions_per_cycle and self._actions_in_cycle >= self.config.max_actions_per_cycle:
             return False

        elapsed = time.time() - self._cycle_started_at
        if self.config.max_seconds_per_cycle and elapsed > self.config.max_seconds_per_cycle:
            return False
            
        return True

    def _check_permission_vs_risk(self, meta: ToolMetadata) -> PolicyDecision:
        rp = (self.config.risk_profile or RiskProfile.BALANCED).lower()
        pl = meta.permission_level

        if rp == RiskProfile.CONSERVATIVE:
            if pl in [PermissionLevel.READ_ONLY, PermissionLevel.SAFE]:
                return PolicyDecision(allowed=True)
            if pl == PermissionLevel.WRITE:
                return PolicyDecision(
                    allowed=self.config.auto_confirm,
                    require_confirmation=not self.config.auto_confirm,
                    reason="WRITE requires confirmation in conservative mode",
                )
            return PolicyDecision(allowed=False, reason="Dangerous tool blocked in conservative mode")

        if rp == RiskProfile.BALANCED:
            if pl in [PermissionLevel.READ_ONLY, PermissionLevel.SAFE, PermissionLevel.WRITE]:
                return PolicyDecision(allowed=True)
            return PolicyDecision(
                allowed=str(meta.name).lower() in self.config.allowlist,
                reason="Dangerous tool outside allowlist in balanced mode",
            )

        if rp == RiskProfile.AGGRESSIVE:
            if pl == PermissionLevel.DANGEROUS:
                return PolicyDecision(
                    allowed=str(meta.name).lower() in self.config.allowlist,
                    reason="Dangerous tool outside allowlist in aggressive mode",
                )
            return PolicyDecision(allowed=True)

        return PolicyDecision(allowed=True)

    def _check_capability_allowlist(self, meta: ToolMetadata) -> PolicyDecision:
        if not self.config.capability_allowlist:
            return PolicyDecision(allowed=True)

        category = str(getattr(meta.category, "value", "") or "").strip().lower()
        if category in self.config.capability_allowlist:
            return PolicyDecision(allowed=True)

        return PolicyDecision(
            allowed=False,
            reason=f"Capability '{category or 'unknown'}' outside allowlist",
        )

    def _extract_command_text(self, input_args: dict[str, Any] | None) -> str | None:
        if not isinstance(input_args, dict):
            return None

        for key in ("command", "cmd", "shell_command", "script", "powershell", "bash"):
            value = input_args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list):
                joined = " ".join(str(part) for part in value if str(part).strip()).strip()
                if joined:
                    return joined

        return None

    def _extract_scope_tags(self, meta: ToolMetadata) -> set[str]:
        tags = getattr(meta, "tags", None)
        if not isinstance(tags, list):
            return set()
        scope_tags: set[str] = set()
        for raw_tag in tags:
            tag = str(raw_tag or "").strip().lower()
            if not tag.startswith("scope:"):
                continue
            scope = tag.removeprefix("scope:").strip()
            if scope:
                scope_tags.add(scope)
        return scope_tags

    def _check_scope_allowlist(self, meta: ToolMetadata) -> PolicyDecision:
        if not self.config.scope_allowlist:
            return PolicyDecision(allowed=True)

        tool_scopes = self._extract_scope_tags(meta)
        if tool_scopes.intersection(self.config.scope_allowlist):
            return PolicyDecision(allowed=True)

        if not tool_scopes:
            return PolicyDecision(allowed=False, reason="Tool has no declared scope tags")

        return PolicyDecision(
            allowed=False,
            reason=f"Tool scopes {sorted(tool_scopes)} outside allowlist",
        )

    def _check_command_allowlist(
        self, *, meta: ToolMetadata, input_args: dict[str, Any] | None
    ) -> PolicyDecision:
        tool_name = str(meta.name or "").strip().lower()
        is_restricted_tool = (
            tool_name in self.config.restricted_command_tools
            or meta.permission_level == PermissionLevel.DANGEROUS
        )
        if not is_restricted_tool:
            return PolicyDecision(allowed=True)

        command_text = self._extract_command_text(input_args)
        if not command_text:
            return PolicyDecision(allowed=True)

        normalized = command_text.lower().strip()
        # Remove multiple spaces to avoid bypass like "rm   -rf"
        normalized_tight = " ".join(normalized.split())

        for token in self.config.command_blocklist_tokens:
            if token and (token in normalized or token in normalized_tight):
                logger.warning("policy_blocked_command_token", tool=meta.name, token=token)
                return PolicyDecision(
                    allowed=False,
                    reason=f"Command blocked by token: {token}",
                )

        if self.config.command_allowlist:
            if any(normalized.startswith(prefix) for prefix in self.config.command_allowlist):
                return PolicyDecision(allowed=True)
            return PolicyDecision(allowed=False, reason="Command outside allowlist")

        if not self.config.auto_confirm:
            return PolicyDecision(
                allowed=False,
                require_confirmation=True,
                reason="Sensitive command requires manual approval",
            )

        return PolicyDecision(
            allowed=False,
            reason="Sensitive command blocked because command allowlist is not configured",
        )

    def validate_content_safety(self, content: str) -> PolicyDecision:
        if not content or not isinstance(content, str):
            return PolicyDecision(allowed=True)

        content_lower = content.lower()
        normalized = (
            content_lower.replace("@", "a")
            .replace("$", "s")
            .replace("0", "o")
            .replace("1", "i")
            .replace("!", "i")
        )

        for pattern in self._injection_patterns:
            if pattern in content_lower or pattern in normalized:
                logger.warning("potential_prompt_injection_detected", pattern=pattern)
                return PolicyDecision(
                    allowed=False,
                    reason=f"Blocked by suspicious content pattern: {pattern}",
                )

        return PolicyDecision(allowed=True)

    def validate_tool_call(
        self,
        tool_name: str,
        input_args: dict | None = None,
        user_id: str | None = None,
    ) -> PolicyDecision:
        if str(tool_name).lower() in self.config.blocklist:
            return PolicyDecision(allowed=False, reason="Tool in blocklist")

        tool = action_registry.get_tool(tool_name)
        meta = action_registry.get_metadata(tool_name) if tool else None
        if not tool or not meta:
            return PolicyDecision(allowed=False, reason="Tool not registered")

        if not action_registry.check_rate_limit(tool_name, user_id=user_id):
            return PolicyDecision(allowed=False, reason="Rate limit reached")

        decision = self._check_permission_vs_risk(meta)
        if not decision.allowed:
            return decision

        capability_decision = self._check_capability_allowlist(meta)
        if not capability_decision.allowed:
            return capability_decision

        scope_decision = self._check_scope_allowlist(meta)
        if not scope_decision.allowed:
            return scope_decision

        command_decision = self._check_command_allowlist(meta=meta, input_args=input_args)
        if not command_decision.allowed:
            return command_decision

        if meta.requires_confirmation and not self.config.auto_confirm:
            return PolicyDecision(
                allowed=False,
                require_confirmation=True,
                reason="Requires manual confirmation",
            )

        self._actions_in_cycle += 1
        return PolicyDecision(allowed=True)

    def simulate_tool_call(
        self,
        tool_name: str,
        input_args: dict[str, Any] | None = None,
    ) -> SimulationResult:
        tool_name_norm = str(tool_name or "").strip().lower()
        args_json = json.dumps(input_args or {}, ensure_ascii=False, default=str).lower()
        combined = f"{tool_name_norm} {args_json}"
        is_destructive = any(keyword in combined for keyword in self._destructive_keywords)
        affected_resources = self._infer_affected_resources(input_args)
        reversible = not any(keyword in combined for keyword in self._irreversible_keywords)
        risk_level = "high" if is_destructive else "low"
        expected_impact = (
            "May alter or remove system/application state."
            if is_destructive
            else "Read-only or low-impact operation."
        )
        summary = (
            "Simulation indicates destructive behavior; manual confirmation required."
            if is_destructive
            else "Simulation indicates non-destructive behavior."
        )
        return SimulationResult(
            is_destructive=is_destructive,
            expected_impact=expected_impact,
            affected_resources=affected_resources,
            reversible=reversible,
            final_risk_level=risk_level,
            summary=summary,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def _infer_affected_resources(self, input_args: dict[str, Any] | None) -> list[str]:
        if not isinstance(input_args, dict):
            return []
        resources: list[str] = []
        for key in ("path", "file_path", "target", "resource", "collection", "table", "queue_name"):
            value = input_args.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text and text not in resources:
                resources.append(text)
        return resources
