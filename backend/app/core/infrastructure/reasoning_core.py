import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from langchain.agents import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from app.core.infrastructure.prompt_loader import get_prompt
from app.core.llm.types import ModelPriority, ModelRole

logger = logging.getLogger(__name__)


async def _resolve_memory_db() -> Any:
    from app.core.memory.memory_core import get_memory_db

    return await get_memory_db()


# --- Ferramentas de Raciocínio (Exemplos) ---


@tool
async def search_memory(query: str, limit: int = 5) -> str:
    """
    Busca na memória episódica por experiências relevantes.

    Args:
        query: A consulta em linguagem natural.
        limit: Número máximo de resultados.

    Returns:
        Uma string JSON com as experiências encontradas.
    """
    try:
        memory_db = await _resolve_memory_db()
        results = await memory_db.arecall(query=query, limit=limit)
        return json.dumps(results, ensure_ascii=False)
    except Exception as exc:
        error_payload: Dict[str, str] = {
            "error": str(exc),
            "error_type": type(exc).__name__,
        }
        logger.error(
            "Erro ao buscar na memória",
            exc_info=True,
            extra={
                "error_type": type(exc).__name__,
                "question_size": len(query or ""),
            },
        )
        return json.dumps(error_payload, ensure_ascii=False)


class ReasoningSession:
    """
    Gerencia uma sessão de raciocínio para um agente.
    """

    def __init__(
        self,
        llm_provider: Callable[..., Awaitable[Any]],
        tools: list[Any],
        prompt_name: str = "reasoning_session",
    ):
        self.llm_provider = llm_provider
        self.tools = tools
        self.prompt: Optional[PromptTemplate] = None
        self.agent_executor = None
        self.prompt_name = prompt_name

    async def _ensure_agent(self) -> None:
        if self.agent_executor:
            return

        prompt_text = await get_prompt(self.prompt_name)
        if not prompt_text:
            raise ValueError(f"Prompt '{self.prompt_name}' nao encontrado.")

        self.prompt = PromptTemplate.from_template(prompt_text)
        llm = await self.llm_provider(
            role=ModelRole.REASONER,
            priority=ModelPriority.HIGH_QUALITY,
        )
        self.agent_executor = create_react_agent(llm, self.tools, self.prompt)

    async def _invoke_executor(self, payload: dict[str, Any]) -> Any:
        if self.agent_executor is None:
            raise RuntimeError("Agent executor não inicializado.")

        if hasattr(self.agent_executor, "ainvoke"):
            return await self.agent_executor.ainvoke(payload)
        if hasattr(self.agent_executor, "invoke"):
            return await asyncio.to_thread(self.agent_executor.invoke, payload)
        raise TypeError("Agent executor não suporta invoke/ainvoke.")

    @staticmethod
    def _normalize_output(result: Any) -> str:
        if isinstance(result, dict):
            if "output" in result:
                return str(result["output"])
            return json.dumps(result, ensure_ascii=False, default=str)
        if isinstance(result, str):
            return result
        return json.dumps({"output": str(result)}, ensure_ascii=False)

    async def solve_question(self, question: str) -> str:
        try:
            await self._ensure_agent()
            result = await self._invoke_executor({"input": question})
            return self._normalize_output(result)
        except Exception as exc:
            logger.error(
                "Erro na sessão de raciocínio",
                exc_info=True,
                extra={
                    "prompt_name": self.prompt_name,
                    "error_type": type(exc).__name__,
                    "question_size": len(question or ""),
                },
            )
            return f"Erro ao processar a pergunta: {exc}"
