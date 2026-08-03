"""Fail-closed registry for the homologated Janus production tools."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from langchain_core.tools import BaseTool

from app.core.security.redaction import redact_sensitive_payload
from app.core.security.security_alerts import emit_security_alert


class ToolCategory(Enum):
    FILESYSTEM = "filesystem"
    API = "api"
    DATABASE = "database"
    COMPUTATION = "computation"
    WEB = "web"
    SYSTEM = "system"
    CUSTOM = "custom"
    DYNAMIC = "dynamic"


class PermissionLevel(Enum):
    READ_ONLY = "read_only"
    SAFE = "safe"
    WRITE = "write"
    DANGEROUS = "dangerous"


@dataclass
class ToolMetadata:
    name: str
    category: ToolCategory
    description: str
    permission_level: PermissionLevel
    rate_limit_per_minute: int | None = None
    requires_confirmation: bool = False
    tags: list[str] = field(default_factory=list)
    namespace: str | None = None
    code_signature: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    llm_model: str | None = None
    evolution_attempt_id: str | None = None


@dataclass
class ToolCall:
    tool_name: str
    timestamp: float
    duration_seconds: float
    success: bool
    error: str | None = None
    input_args: dict[str, Any] = field(default_factory=dict)


class ActionRegistry:
    """Registry that becomes immutable when the production manifest is loaded."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._metadata: dict[str, ToolMetadata] = {}
        self._namespaces: dict[str, str] = {}
        self._previous_versions: dict[str, BaseTool] = {}
        self._call_history: list[ToolCall] = []
        self._rate_limits: dict[tuple[str, str], list[float]] = {}
        self._manifest_allowlist: frozenset[str] | None = None

    def clear_and_lock_manifest(self, allowed_names: frozenset[str]) -> None:
        self._tools.clear()
        self._metadata.clear()
        self._namespaces.clear()
        self._previous_versions.clear()
        self._manifest_allowlist = frozenset(allowed_names)

    def register(
        self,
        tool: BaseTool,
        category: ToolCategory = ToolCategory.CUSTOM,
        permission_level: PermissionLevel = PermissionLevel.SAFE,
        namespace: str = "core",
        code_signature: str | None = None,
        rate_limit_per_minute: int | None = None,
        requires_confirmation: bool = False,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        name = str(tool.name)
        if namespace == "evolution":
            emit_security_alert("autonomous_tool_registration_blocked", {"tool_name": name})
            raise PermissionError("Evolution tool registration is permanently disabled")
        if self._manifest_allowlist is not None:
            valid = (
                name in self._manifest_allowlist
                and namespace == "production"
                and permission_level is PermissionLevel.READ_ONLY
            )
            if not valid:
                emit_security_alert("production_registry_mutation_blocked", {"tool_name": name})
                raise PermissionError("Tool is not homologated for the production registry")
        if name in self._tools:
            if self._manifest_allowlist is not None:
                raise PermissionError("Production registry is immutable")
            self._previous_versions[name] = self._tools[name]
        self._tools[name] = tool
        self._namespaces[name] = namespace
        self._metadata[name] = ToolMetadata(
            name=name,
            category=category,
            description=str(getattr(tool, "description", "") or ""),
            permission_level=permission_level,
            rate_limit_per_minute=rate_limit_per_minute,
            requires_confirmation=requires_confirmation,
            tags=list(tags or []),
            namespace=namespace,
            code_signature=code_signature,
            created_by=kwargs.get("created_by"),
            created_at=kwargs.get("created_at"),
            llm_model=kwargs.get("llm_model"),
            evolution_attempt_id=kwargs.get("evolution_attempt_id"),
        )

    def register_tool(self, tool: BaseTool, **kwargs: Any) -> None:
        self.register(tool, **kwargs)

    def unregister(self, name: str) -> bool:
        if self._manifest_allowlist is not None:
            emit_security_alert("production_registry_mutation_blocked", {"tool_name": name})
            raise PermissionError("Production registry is immutable")
        existed = name in self._tools
        self._tools.pop(name, None)
        self._metadata.pop(name, None)
        self._namespaces.pop(name, None)
        self._previous_versions.pop(name, None)
        return existed

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def resolve_tool(self, name: str) -> BaseTool | None:
        return self.get_tool(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        return self._metadata.get(name)

    def get_namespace(self, name: str) -> str | None:
        return self._namespaces.get(name)

    def get_tool_provenance(self, name: str) -> dict[str, Any] | None:
        metadata = self.get_metadata(name)
        if metadata is None:
            return None
        return {
            "name": metadata.name,
            "namespace": metadata.namespace,
            "code_signature": metadata.code_signature,
            "created_by": metadata.created_by,
            "created_at": metadata.created_at,
            "llm_model": metadata.llm_model,
            "evolution_attempt_id": metadata.evolution_attempt_id,
        }

    def list_tools(
        self,
        category: ToolCategory | None = None,
        permission_level: PermissionLevel | None = None,
        tags: list[str] | None = None,
    ) -> list[BaseTool]:
        required_tags = set(tags or [])
        values: list[BaseTool] = []
        for name, tool in self._tools.items():
            metadata = self._metadata[name]
            if category is not None and metadata.category is not category:
                continue
            if permission_level is not None and metadata.permission_level is not permission_level:
                continue
            if required_tags and not required_tags.issubset(metadata.tags):
                continue
            values.append(tool)
        return values

    def list_by_namespace(self, namespace: str) -> list[BaseTool]:
        return [tool for name, tool in self._tools.items() if self._namespaces.get(name) == namespace]

    def check_rate_limit(self, tool_name: str, user_id: str | None = None) -> bool:
        metadata = self.get_metadata(tool_name)
        if metadata is None or metadata.rate_limit_per_minute is None:
            return True
        now = time.time()
        key = (str(user_id or "anonymous"), tool_name)
        recent = [stamp for stamp in self._rate_limits.get(key, []) if now - stamp < 60]
        self._rate_limits[key] = recent
        return len(recent) < metadata.rate_limit_per_minute

    def record_call(
        self,
        tool_name: str,
        duration: float,
        success: bool,
        error: str | None = None,
        input_args: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> None:
        now = time.time()
        self._rate_limits.setdefault((str(user_id or "anonymous"), tool_name), []).append(now)
        safe_args = redact_sensitive_payload(input_args or {})
        self._call_history.append(
            ToolCall(
                tool_name=tool_name,
                timestamp=now,
                duration_seconds=float(duration),
                success=bool(success),
                error=str(redact_sensitive_payload(error)) if error else None,
                input_args=safe_args if isinstance(safe_args, dict) else {},
            )
        )
        self._call_history = self._call_history[-1000:]

    def get_statistics(self) -> dict[str, Any]:
        total = len(self._call_history)
        successful = sum(1 for call in self._call_history if call.success)
        usage: dict[str, dict[str, Any]] = {}
        for name in self._tools:
            calls = [call for call in self._call_history if call.tool_name == name]
            usage[name] = {
                "total": len(calls),
                "success": sum(1 for call in calls if call.success),
                "avg_duration": (
                    sum(call.duration_seconds for call in calls) / len(calls) if calls else 0.0
                ),
            }
        return {
            "total_tools_registered": len(self._tools),
            "total_calls": total,
            "successful_calls": successful,
            "success_rate": successful / total if total else 0.0,
            "tool_usage": usage,
        }

    def verify_tool_signature(self, name: str) -> bool:
        metadata = self.get_metadata(name)
        return bool(metadata and metadata.code_signature)

    def rollback_tool(self, name: str) -> bool:
        if self._manifest_allowlist is not None:
            emit_security_alert("production_registry_mutation_blocked", {"tool_name": name})
            return False
        previous = self._previous_versions.pop(name, None)
        if previous is None:
            return False
        self._tools[name] = previous
        return True


action_registry = ActionRegistry()


def register_tool(
    tool: BaseTool,
    category: ToolCategory = ToolCategory.CUSTOM,
    namespace: str = "core",
    **kwargs: Any,
) -> None:
    action_registry.register(tool, category=category, namespace=namespace, **kwargs)


def create_tool_from_function(*args: Any, **kwargs: Any) -> BaseTool:
    emit_security_alert("dynamic_tool_creation_blocked", {"capability": "function"})
    raise PermissionError("Dynamic tool creation is permanently disabled")


def get_all_tools() -> list[BaseTool]:
    return action_registry.list_tools()


def get_tools_by_category(category: ToolCategory) -> list[BaseTool]:
    return action_registry.list_tools(category=category)
