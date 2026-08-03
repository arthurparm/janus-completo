from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.tools import PermissionLevel, ToolCategory
from app.services.tool_service import ToolService, get_tool_service

router = APIRouter(tags=["Tools"])


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    permission_level: str
    rate_limit_per_minute: int | None
    requires_confirmation: bool
    tags: list[str]


class ToolListResponse(BaseModel):
    total: int
    tools: list[ToolInfo]


class ToolStatsResponse(BaseModel):
    total_tools_registered: int
    total_calls: int
    successful_calls: int
    success_rate: float
    tool_usage: dict[str, dict[str, Any]]


def _tool_info(meta: Any) -> ToolInfo:
    return ToolInfo(
        name=meta.name,
        description=meta.description,
        category=meta.category.value,
        permission_level=meta.permission_level.value,
        rate_limit_per_minute=meta.rate_limit_per_minute,
        requires_confirmation=meta.requires_confirmation,
        tags=meta.tags,
    )


@router.get("/", response_model=ToolListResponse)
async def list_tools(
    service: ToolService = Depends(get_tool_service),
    category: str | None = None,
    permission_level: str | None = None,
    tags: str | None = None,
):
    try:
        category_filter = ToolCategory(category.lower()) if category else None
        permission_filter = PermissionLevel(permission_level.lower()) if permission_level else None
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
        values = service.list_tools(category_filter, permission_filter, tag_list)
        tools = [_tool_info(meta) for meta in values]
        return ToolListResponse(total=len(tools), tools=tools)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filter") from exc


@router.get("/stats/usage", response_model=ToolStatsResponse)
async def get_tool_statistics(service: ToolService = Depends(get_tool_service)):
    return service.get_statistics()


@router.get("/categories/list")
async def list_categories(service: ToolService = Depends(get_tool_service)):
    return {"categories": service.list_categories()}


@router.get("/permissions/list")
async def list_permissions(service: ToolService = Depends(get_tool_service)):
    return {"permission_levels": service.list_permissions()}


@router.get("/{tool_name}", response_model=ToolInfo)
async def get_tool_details(tool_name: str, service: ToolService = Depends(get_tool_service)):
    return _tool_info(service.get_tool_details(tool_name))
