from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar, Protocol, runtime_checkable

import structlog
from app.core.security.security_alerts import emit_security_alert
from app.core.tools import PermissionLevel, ToolCategory, ToolMetadata
from fastapi import Request

logger = structlog.get_logger(__name__)


@runtime_checkable
class ToolRepositoryPort(Protocol):
    """Typed boundary required by the read-only tool catalog service."""

    def find_all(
        self,
        category: ToolCategory | None,
        permission_level: PermissionLevel | None,
        tags: list[str] | None,
    ) -> list[ToolMetadata]: ...

    def find_by_name(self, tool_name: str) -> ToolMetadata | None: ...

    def get_all_statistics(self) -> Mapping[str, object]: ...

    def get_all_categories(self) -> list[str]: ...

    def get_all_permissions(self) -> list[str]: ...


class ToolServiceError(Exception):
    pass


class ToolNotFoundError(ToolServiceError):
    pass


class ToolCreationError(ToolServiceError):
    pass


class ProtectedToolError(ToolServiceError):
    pass


class ToolService:
    """Read-only view of the immutable, homologated production registry."""

    PROTECTED_TOOLS: ClassVar[set[str]] = {
        "recall_experiences",
        "recall_working_memory",
        "query_knowledge_graph",
        "find_related_concepts",
        "get_entity_details",
        "get_current_datetime",
        "render_ui_component",
    }

    def __init__(self, repo: ToolRepositoryPort):
        if not isinstance(repo, ToolRepositoryPort):
            raise TypeError("Tool repository does not satisfy the catalog contract")
        self._repo = repo

    def list_tools(
        self,
        category: ToolCategory | None,
        permission_level: PermissionLevel | None,
        tags: list[str] | None,
    ) -> list[ToolMetadata]:
        return self._repo.find_all(category, permission_level, tags)

    def get_tool_details(self, tool_name: str) -> ToolMetadata:
        metadata = self._repo.find_by_name(tool_name)
        if metadata is None:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")
        return metadata

    def get_statistics(self) -> dict[str, object]:
        statistics = self._repo.get_all_statistics()
        normalized: dict[str, object] = {}
        for key, value in statistics.items():
            if not isinstance(key, str):
                raise TypeError("Tool statistics require string keys")
            normalized[key] = value
        return normalized

    def generate_documentation(self, include_stats: bool = True, format: str = "markdown") -> str:
        del format
        tools = self.list_tools(None, None, None)
        statistics = self.get_statistics() if include_stats else {}
        lines = ["# Homologated production tools", ""]
        if not tools:
            lines.extend(["No homologated tools are currently registered.", ""])
        for metadata in sorted(tools, key=lambda item: item.name):
            lines.extend(
                [
                    f"## {metadata.name}",
                    metadata.description,
                    f"- Permission: `{metadata.permission_level.value}`",
                    f"- Namespace: `{metadata.namespace}`",
                    "",
                ]
            )
        if statistics:
            registered = statistics.get("total_tools_registered", 0)
            if isinstance(registered, bool) or not isinstance(registered, int):
                raise TypeError("Tool statistics contain an invalid registered-tools count")
            lines.append(f"Registered tools: {registered}")
        return "\n".join(lines)

    def create_tool_from_function(self, request_data: Mapping[str, object]) -> ToolMetadata:
        emit_security_alert(
            "dynamic_tool_creation_blocked",
            {"capability": "function", "requested_name": request_data.get("name")},
        )
        raise ToolCreationError("Dynamic tool creation is permanently disabled")

    def create_tool_from_api(self, request_data: Mapping[str, object]) -> ToolMetadata:
        emit_security_alert(
            "dynamic_tool_creation_blocked",
            {"capability": "api", "requested_name": request_data.get("name")},
        )
        raise ToolCreationError("Dynamic tool creation is permanently disabled")

    def delete_tool(self, tool_name: str) -> None:
        emit_security_alert("production_registry_mutation_blocked", {"tool_name": tool_name})
        raise ProtectedToolError("Production registry is immutable")

    def list_categories(self) -> list[str]:
        return self._repo.get_all_categories()

    def list_permissions(self) -> list[str]:
        return self._repo.get_all_permissions()


def get_tool_service(request: Request) -> ToolService:
    service = getattr(request.app.state, "tool_service", None)
    if not isinstance(service, ToolService):
        raise RuntimeError("ToolService is not initialized")
    return service
