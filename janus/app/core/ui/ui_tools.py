from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.tools.agent_tools import register_tool

# --- Pydantic Models ---

class UiComponentRequest(BaseModel):
    """
    Request to render a Generative UI component on the frontend.
    This replaces the old <janus-ui> XML tag approach.
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
    
    # For Janus architecture:
    # We return a structured string that the AgentEventPublisher can pick up,
    # OR we rely on the fact that the 'tool_use' block is already sent to the frontend
    # and the frontend can intercept 'render_ui_component' calls and render them directly.
    
    # Strategy: The frontend (Angular) listens for tool calls. 
    # If the tool name is 'render_ui_component', it suppresses the text output 
    # and renders the component using the arguments.
    
    return f"UI Component '{title}' ({type}) generated successfully."


def register_ui_tools():
    """Registers the UI tools with the global tool registry."""
    register_tool(
        name="render_ui_component",
        func=render_ui_component,
        description="Renders a rich UI component (table, chart, etc) in the user's chat.",
        args_schema=UiComponentRequest
    )
