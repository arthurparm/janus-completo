from typing import Callable, List

import structlog
from langsmith import traceable
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from app.core.infrastructure.prompt_loader import get_formatted_prompt

logger = structlog.get_logger(__name__)

class WorkerResult(BaseModel):
    response: str
    tool_calls: List[str] = Field(default_factory=list)

class LeafWorker:
    """
    A leaf worker agent implemented using PydanticAI.
    It provides type-safe tool execution and structured outputs.
    Unsafe tools are replaced by deterministic blockers with security alerts.
    """

    def __init__(
        self,
        name: str,
        model: str = "openai:gpt-4o",
        system_prompt: str = "",
        tools: List[Callable] = None
    ):
        self.name = name
        self.agent = Agent(
            model,
            system_prompt=system_prompt,
            output_type=WorkerResult
        )
        self._register_tools(tools or [])

    def _register_tools(self, tools: List[Callable]):
        for tool in tools:
            # Check if tool is marked as unsafe
            # We assume a naming convention or attribute for now
            # e.g., tools decorated with @unsafe or named run_command
            is_unsafe = getattr(tool, "unsafe", False) or tool.__name__ in ["run_command", "write_file", "read_file"]

            if is_unsafe:
                self.agent.tool(self._create_blocked_wrapper(tool))
            else:
                self.agent.tool(tool)

    def _create_blocked_wrapper(self, original_tool: Callable) -> Callable:
        async def blocked_tool(ctx: RunContext, *args, **kwargs) -> str:
            del ctx, args, kwargs
            from app.core.security.security_alerts import emit_security_alert

            logger.warning(
                "unsafe_tool_execution_blocked",
                tool_name=original_tool.__name__,
            )
            emit_security_alert(
                "removed_tool_execution_blocked",
                {"tool_name": original_tool.__name__},
            )
            return f"Tool {original_tool.__name__} blocked by security policy."

        blocked_tool.__name__ = original_tool.__name__
        blocked_tool.__doc__ = original_tool.__doc__
        return blocked_tool

    @traceable(name="LeafWorker.run", run_type="chain")
    async def run(self, prompt: str, context: dict = None) -> WorkerResult:
        """
        Executes the worker with the given prompt.
        """
        logger.info("log_info", message=f"Worker {self.name} starting task: {prompt[:50]}...")
        try:
            # PydanticAI run method
            result = await self.agent.run(prompt)
            output = result.output
            if isinstance(output, WorkerResult):
                return output
            if isinstance(output, dict):
                return WorkerResult(**output)
            return WorkerResult(response=str(output))
        except Exception as e:
            logger.error("log_error", message=f"Worker {self.name} failed: {e}")
            raise

# Example usage/factory
async def create_coder_worker() -> LeafWorker:
    system_prompt = await get_formatted_prompt("leaf_worker_coder")
    return LeafWorker(
        name="Coder",
        system_prompt=system_prompt,
        # Add actual tools here
    )
