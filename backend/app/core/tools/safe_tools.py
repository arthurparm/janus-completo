from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

import structlog
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


@tool  # type: ignore[untyped-decorator]
async def recall_experiences(query: str) -> str:
    """Read matching episodic memories."""
    from app.core.memory.memory_core import get_memory_db

    memory_db = await get_memory_db()
    return json.dumps(await memory_db.arecall(query=query, limit=3), ensure_ascii=False)


@tool  # type: ignore[untyped-decorator]
def recall_working_memory(query: str, limit: int = 5) -> str:
    """Read matching short-term memories."""
    from app.core.memory.working_memory import get_working_memory

    return json.dumps(get_working_memory().recall(query=query, limit=limit), ensure_ascii=False)


@tool  # type: ignore[untyped-decorator]
async def query_knowledge_graph(query: str) -> str:
    """Read semantically relevant entries from the knowledge graph."""
    from app.core.memory.knowledge_graph_manager import knowledge_graph_manager

    return json.dumps(await knowledge_graph_manager.semantic_search(query, limit=10), ensure_ascii=False)


@tool  # type: ignore[untyped-decorator]
async def find_related_concepts(concept: str, max_depth: int = 2) -> str:
    """Read concepts connected to a named concept."""
    from app.db.graph import get_graph_db

    depth = max(1, min(int(max_depth), 3))
    graph = await get_graph_db()
    query = (
        "MATCH path=(c:Concept {name: $concept})-[*1..%d]-(related) "
        "RETURN related.name AS concept, type(last(relationships(path))) AS relationship, "
        "length(path) AS distance ORDER BY distance LIMIT 10" % depth
    )
    return json.dumps(await graph.query(query, {"concept": concept}), ensure_ascii=False)


@tool  # type: ignore[untyped-decorator]
async def get_entity_details(entity_name: str) -> str:
    """Read a knowledge-graph entity and its outgoing relationships."""
    from app.db.graph import get_graph_db

    graph = await get_graph_db()
    query = (
        "MATCH (e) WHERE e.name = $entity_name OR e.id = $entity_name "
        "OPTIONAL MATCH (e)-[r]->(related) "
        "RETURN e AS entity, collect({type: type(r), target: related.name}) AS relationships LIMIT 1"
    )
    return json.dumps(await graph.query(query, {"entity_name": entity_name}), ensure_ascii=False, default=str)


@tool  # type: ignore[untyped-decorator]
def get_current_datetime() -> str:
    """Return the current UTC date and time without exposing host information."""
    now = datetime.now(timezone.utc)
    return json.dumps({"iso8601": now.isoformat(), "timezone": "UTC", "weekday": now.strftime("%A")})


class UiComponentRequest(BaseModel):  # type: ignore[misc]
    type: Literal["table", "chart", "list", "card", "code_block"]
    title: str
    data: dict[str, Any] | list[Any]
    description: str | None = None


@tool(args_schema=UiComponentRequest)  # type: ignore[untyped-decorator]
def render_ui_component(
    type: str,
    title: str,
    data: dict[str, Any] | list[Any],
    description: str | None = None,
) -> str:
    """Return a deterministic UI render acknowledgement."""
    _ = (data, description)
    return json.dumps({"status": "accepted", "component_type": type, "title": title})


APPROVED_TOOLS: tuple[BaseTool, ...] = (
    recall_experiences,
    recall_working_memory,
    query_knowledge_graph,
    find_related_concepts,
    get_entity_details,
    get_current_datetime,
    render_ui_component,
)

unified_tools: list[BaseTool] = list(APPROVED_TOOLS)
meta_agent_tools: list[BaseTool] = list(APPROVED_TOOLS)


def get_tools_for_agent(agent_type: Any) -> list[BaseTool]:
    _ = agent_type
    return list(APPROVED_TOOLS)
