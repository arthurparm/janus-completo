import structlog
from typing import List, Dict, Any, Optional
from fastapi import Request

from app.repositories.tool_repository import ToolRepository
from app.core.tools import (
    DynamicToolGenerator,
    ToolCategory,
    PermissionLevel,
    ToolMetadata
)

logger = structlog.get_logger(__name__)

class ToolServiceError(Exception):
    """Base exception for tool service errors."""
    pass


class ToolNotFoundError(ToolServiceError):
    """Raised when a tool is not found."""
    pass


class ToolCreationError(ToolServiceError):
    """Raised on failure to create a dynamic tool."""
    pass


class ProtectedToolError(ToolServiceError):
    """Raised when attempting to modify a protected built-in tool."""
    pass


class ToolService:
    """
    Service layer for managing tools.
    Orchestrate business logic, receiving its dependencies via DI.
    """

    PROTECTED_TOOLS = {
        "write_file", "read_file", "list_directory",
        "recall_experiences", "analyze_memory_for_failures",
        "get_current_datetime", "get_system_info",
        "search_web", "get_enriched_context",
        "execute_python_code", "execute_python_expression"
    }

    def __init__(self, repo: ToolRepository):
        self._repo = repo

    def list_tools(self, category: Optional[ToolCategory], permission_level: Optional[PermissionLevel],
                   tags: Optional[List[str]]) -> List[ToolMetadata]:
        logger.info("Listing tools via service.")
        return self._repo.find_all(category, permission_level, tags)

    def get_tool_details(self, tool_name: str) -> ToolMetadata:
        logger.info("Fetching tool details via service", tool_name=tool_name)
        metadata = self._repo.find_by_name(tool_name)
        if not metadata:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found.")
        return metadata

    def get_statistics(self) -> Dict[str, Any]:
        logger.info("Fetching tools statistics via service.")
        return self._repo.get_all_statistics()

    def generate_documentation(self, include_stats: bool = True, format: str = "markdown") -> str:
        """
        Generates descriptive documentation of the registered local tools.

        - Uses metadata from registry (name, category, description, permission level, rate limit, tags)
        - Optionally includes recent statistics per tool (total, success, average duration)

        Args:
            include_stats: If True, includes call registration statistics
            format: Only "markdown" supported for formatted output

        Returns:
            Formatted text with the documentation of tools
        """
        try:
            metas = self.list_tools(category=None, permission_level=None, tags=None)
        except Exception as e:
            logger.error("Failed to list tools for documentation", exc_info=e)
            metas = []

        stats: Dict[str, Any] = {}
        if include_stats:
            try:
                stats = self.get_statistics()
            except Exception as e:
                logger.warning("Failed to get statistics for documentation", exc_info=e)
                stats = {}

        total_tools = len(metas)
        if format.lower() != "markdown":
            format = "markdown"

        # Group by category
        grouped: Dict[str, List[ToolMetadata]] = {}
        for m in metas:
            cat = getattr(m.category, "value", str(m.category))
            grouped.setdefault(cat, []).append(m)

        lines: List[str] = []
        lines.append("# Local Tools Documentation")
        lines.append("")
        lines.append(f"Summary: {total_tools} tool(s) registered")
        if include_stats and stats:
            lines.append(
                f"General statistics: {stats.get('total_calls', 0)} recent calls, "
                f"success rate {stats.get('success_rate', 0.0)}"
            )
        lines.append("")

        tool_usage = stats.get("tool_usage", {}) if stats else {}

        for cat, items in sorted(grouped.items(), key=lambda x: x[0]):
            lines.append(f"## Category: {cat}")
            lines.append("")
            for m in sorted(items, key=lambda x: x.name):
                perm = getattr(m.permission_level, "value", str(m.permission_level))
                rl = m.rate_limit_per_minute
                req_conf = getattr(m, "requires_confirmation", False)
                tags = ", ".join(m.tags) if m.tags else "(no tags)"

                lines.append(f"### {m.name}")
                if m.description:
                    lines.append(m.description.strip())
                lines.append("")
                lines.append(f"- Permission: `{perm}`")
                lines.append(f"- Rate limit/min: `{rl if rl is not None else 'no limit'}`")
                lines.append(f"- Requires confirmation: `{bool(req_conf)}`")
                lines.append(f"- Tags: {tags}")

                usage = tool_usage.get(m.name)
                if include_stats and usage:
                    total = usage.get("total", 0)
                    success = usage.get("success", 0)
                    avg = usage.get("avg_duration", 0.0)
                    rate = round(success / total, 3) if total else 0.0
                    lines.append(
                        f"- Recent usage: `{total}` calls, success `{success}`, rate `{rate}`, average duration `{avg}s`"
                    )
                lines.append("")

        return "\n".join(lines)

    def create_tool_from_function(self, request_data: Dict[str, Any]) -> ToolMetadata:
        logger.info("Orchestrating creation of tool from Python code", tool_name=request_data['name'])
        try:
            tool = DynamicToolGenerator.from_python_code(
                name=request_data['name'],
                description=request_data['description'],
                code=request_data['code'],
                function_name=request_data['function_name']
            )
            # Normalize enum values (accepts uppercase from client, e.g., "COMPUTATION")
            raw_category = str(request_data.get('category', 'custom')).lower()
            raw_permission = str(request_data.get('permission_level', 'safe')).lower()

            metadata_to_save = {
                "category": ToolCategory(raw_category),
                "permission_level": PermissionLevel(raw_permission),
                "rate_limit_per_minute": request_data.get('rate_limit_per_minute'),
                "tags": request_data.get('tags', [])
            }
            self._repo.save(tool, metadata_to_save)
            return self.get_tool_details(request_data['name'])
        except Exception as e:
            logger.error("Error in service while creating tool from function", exc_info=e)
            raise ToolCreationError(f"Failed to create tool: {e}") from e

    def create_tool_from_api(self, request_data: Dict[str, Any]) -> ToolMetadata:
        logger.info("Orchestrating creation of tool from API HTTP", tool_name=request_data['name'])
        try:
            tool = DynamicToolGenerator.from_api_endpoint(
                name=request_data['name'],
                description=request_data['description'],
                endpoint_url=request_data['endpoint_url'],
                method=request_data.get('method', 'GET'),
                headers=request_data.get('headers')
            )

            raw_category = str(request_data.get('category', 'api')).lower()
            raw_permission = str(request_data.get('permission_level', 'safe')).lower()

            metadata_to_save = {
                "category": ToolCategory(raw_category),
                "permission_level": PermissionLevel(raw_permission),
                "rate_limit_per_minute": request_data.get('rate_limit_per_minute'),
                "tags": request_data.get('tags', [])
            }
            self._repo.save(tool, metadata_to_save)
            return self.get_tool_details(request_data['name'])
        except Exception as e:
            logger.error("Error in service while creating tool from API", exc_info=e)
            raise ToolCreationError(f"Failed to create API tool: {e}") from e

    def delete_tool(self, tool_name: str):
        logger.info("Orchestrating removal of tool", tool_name=tool_name)
        if tool_name in self.PROTECTED_TOOLS:
            raise ProtectedToolError(f"The tool '{tool_name}' is protected and cannot be removed.")
        self.get_tool_details(tool_name)  # Check if the tool exists
        self._repo.delete(tool_name)
        logger.info("Tool successfully removed via service", tool_name=tool_name)

    def list_categories(self) -> List[str]:
        return self._repo.get_all_categories()

    def list_permissions(self) -> List[str]:
        return self._repo.get_all_permissions()


def get_tool_service(request: Request) -> ToolService:
    return request.app.state.tool_service