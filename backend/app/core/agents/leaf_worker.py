from typing import Any, Callable, List, Type
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import logging
import inspect

from langsmith import traceable

from app.core.tools.sandbox_executor import sandbox
from app.core.infrastructure.prompt_loader import get_formatted_prompt

logger = logging.getLogger(__name__)

class WorkerResult(BaseModel):
    response: str
    tool_calls: List[str] = Field(default_factory=list)

class LeafWorker:
    """
    A leaf worker agent implemented using PydanticAI.
    It provides type-safe tool execution and structured outputs.
    Automatically wraps unsafe tools in sandbox execution.
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
                self.agent.tool(self._create_sandboxed_wrapper(tool))
            else:
                self.agent.tool(tool)
    
    def _create_sandboxed_wrapper(self, original_tool: Callable) -> Callable:
        """
        Creates a wrapper that executes the tool logic inside sandbox if it involves code execution,
        or just blocks filesystem access if that's the intent.
        
        However, for generic tools like 'run_command', we want to execute them IN the sandbox.
        Since we don't have the implementation of 'run_command' here, we assume the tool
        accepts a command string.
        """
        # Get signature to preserve Pydantic validation
        sig = inspect.signature(original_tool)
        
        async def sandboxed_tool(ctx: RunContext, *args, **kwargs) -> str:
            logger.warning(f"Intercepting unsafe tool {original_tool.__name__} for sandbox execution")
            
            # Construct a python script that calls the tool? 
            # Or if the tool IS 'execute_python', we just pass the code.
            # If the tool is 'run_command', we can't easily map it to sandbox without changing tool signature
            # unless the sandbox supports running shell commands (which it does via python subprocess)
            
            # Simplified Logic:
            # If tool is 'run_python' or similar, extract code and run in sandbox.
            # If tool is 'run_command', wrap in os.system inside python sandbox.
            
            if original_tool.__name__ == "run_command":
                cmd = kwargs.get("command") or args[0]
                # Wrap shell command in python
                python_code = f"import subprocess; print(subprocess.check_output('{cmd}', shell=True).decode())"
                stdout, stderr = sandbox.run_code(python_code)
                if stderr:
                    return f"Error: {stderr}"
                return stdout
                
            # For other tools, we might just warn or block if not compatible
            # Ideally, we should have a generic 'execute_in_sandbox' tool instead.
            return f"Tool {original_tool.__name__} blocked by security policy (not fully adapted for sandbox)."

        # Copy metadata
        sandboxed_tool.__name__ = original_tool.__name__
        sandboxed_tool.__doc__ = original_tool.__doc__
        # We might need to copy annotations too for PydanticAI to work
        # But changing implementation dynamically is tricky with PydanticAI's static analysis
        # For now, let's assume we register the sandbox tool DIRECTLY instead of wrapping if possible.
        
        return sandboxed_tool
            
    @traceable(name="LeafWorker.run", run_type="chain")
    async def run(self, prompt: str, context: dict = None) -> WorkerResult:
        """
        Executes the worker with the given prompt.
        """
        logger.info(f"Worker {self.name} starting task: {prompt[:50]}...")
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
            logger.error(f"Worker {self.name} failed: {e}")
            raise

# Example usage/factory
async def create_coder_worker() -> LeafWorker:
    system_prompt = await get_formatted_prompt("leaf_worker_coder")
    return LeafWorker(
        name="Coder",
        system_prompt=system_prompt,
        # Add actual tools here
    )
