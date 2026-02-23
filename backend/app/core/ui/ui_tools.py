from typing import Any, Literal

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.core.tools.action_module import PermissionLevel, ToolCategory, register_tool

# --- Pydantic Models ---

class UiComponentRequest(BaseModel):
    """
    Request to render a Generative UI component on the frontend.
    Canonical mechanism for structured UI rendering in chat.
    """
    type: Literal["table", "chart", "list", "card", "code_block"] = Field(
        ..., 
        description="The type of UI component to render."
    )
    title: str = Field(..., description="A title for the component.")
    data: dict[str, Any] | list[Any] = Field(
        ..., 
        description="The structured data to populate the component."
    )
    description: str | None = Field(None, description="Optional description or caption.")


# --- Tool Implementation ---

@tool(args_schema=UiComponentRequest)
def render_ui_component(
    type: str,
    title: str,
    data: dict[str, Any] | list[Any],
    description: str = None
) -> str:
    """
    Renders a specialized UI component in the chat interface.
    
    Use this tool whenever you need to present structured data (tables, charts, lists) 
    in a visually rich format, instead of outputting raw Markdown tables or text.
    
    Returns:
        A confirmation string. The actual UI event is handled by the system 
        and emitted to the frontend via the 'ui_render_request' event.
    """
    # In a real tool execution flow, the return value is observed by the LLM.
    # The side effect (emitting the UI event) happens in the tool executor or 
    # is inferred from the tool call itself by the frontend if we stream tool calls.
    
    # The frontend listens for this tool call and renders the component directly.

    return f"UI Component '{title}' ({type}) generated successfully."


def register_ui_tools():
    """Registers the UI tools with the global tool registry."""
    register_tool(
        render_ui_component,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.SAFE,
        tags=["ui", "frontend", "component"]
    )
