import asyncio
import json
import re
from typing import Any

import structlog

from app.core.tools import action_registry

logger = structlog.get_logger(__name__)


class ToolExecutorService:
    """
    Service responsible for parsing tool calls from LLM output and executing them.
    """

    def parse_tool_calls(self, text: str) -> list[dict[str, Any]]:
        """Extrai chamadas de ferramenta XML do texto."""
        calls = []
        # Regex para capturar blocos <tool_use>...</tool_use>
        # Flags: DOTALL para pegar quebras de linha
        pattern = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL)
        matches = pattern.findall(text)

        for content in matches:
            try:
                name_match = re.search(r"<name>(.*?)</name>", content, re.DOTALL)
                args_match = re.search(r"<args>(.*?)</args>", content, re.DOTALL)

                if name_match and args_match:
                    name = name_match.group(1).strip()
                    args_str = args_match.group(1).strip()

                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        # Tenta fallback frouxo se o modelo alucinar aspas
                        args = {"raw_args": args_str}

                    calls.append({"name": name, "args": args})
            except Exception as e:
                logger.warning(f"Failed to parse tool call block: {e}")

        return calls

    async def execute_tool_calls(self, calls: list[dict[str, Any]]) -> list[dict[str, str]]:
        outputs = []
        for call in calls:
            name = call["name"]
            args = call["args"]

            tool = action_registry.get_tool(name)
            if not tool:
                outputs.append({"name": name, "result": f"Error: Tool '{name}' not found."})
                continue

            try:
                # Executa a ferramenta
                # Suporta async e sync
                import inspect

                # LangChain tools usually implement invoke (sync) and ainvoke (async)
                if hasattr(tool, "ainvoke"):
                    result = await tool.ainvoke(args)
                elif inspect.iscoroutinefunction(tool.func) or (
                    hasattr(tool, "coroutine") and tool.coroutine
                ):
                    result = await tool.func(**args)
                else:
                    result = await asyncio.to_thread(tool.invoke, args)

                outputs.append({"name": name, "result": str(result)})
            except Exception as e:
                logger.error(f"Tool execution failed for {name}", exc_info=e)
                outputs.append(
                    {"name": name, "result": f"System: Tool Error (STOP and rethink): {e!s}"}
                )

        return outputs
