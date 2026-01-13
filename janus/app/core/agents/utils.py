import json
import logging
import re
from functools import wraps
from typing import Any
import inspect

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class AgentEventCallbackHandler(BaseCallbackHandler):
    """Callback handler para transmitir eventos do agente via callback assíncrono."""

    def __init__(self, async_callback):
        self.async_callback = async_callback

    async def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        try:
            await self.async_callback(
                "tool_start", f"Starting tool {serialized.get('name')}: {input_str}"
            )
        except Exception as e:
            logger.warning(f"Error in callback: {e}")

    async def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        try:
            await self.async_callback("tool_end", f"Tool output: {output[:200]}...")
        except Exception as e:
            logger.warning(f"Error in callback: {e}")

    async def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        try:
            # action tem .tool e .tool_input
            content = f"Thought: I need to use {action.tool} with input {action.tool_input}"
            await self.async_callback("agent_thought", content)
        except Exception as e:
            logger.warning(f"Error in callback: {e}")


def _clean_json_output(text: str) -> str:
    """
    Remove markdown code blocks e limpa o output para parsing JSON.

    Args:
        text: Texto que pode conter JSON envolto em markdown

    Returns:
        JSON limpo sem markdown
    """
    if not text:
        return text

    # Remove markdown code blocks (```json ... ``` ou ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    return text


def _create_tool_wrapper(tool):
    """
    Cria um wrapper para ferramentas que trata o input corretamente.

    O LangChain às vezes passa o JSON inteiro como string no primeiro parâmetro.
    Este wrapper detecta isso e faz o parse correto, suportando sync e async.
    """

    logger.info(f"[WRAPPER INIT] Criando wrapper para {tool.name} - type={type(tool)}")

    # Detecta qual método usar
    if hasattr(tool, "func") and callable(tool.func):
        original_func = tool.func
        logger.info(f"[WRAPPER INIT] {tool.name} - Usando tool.func")
    elif hasattr(tool, "_run") and callable(tool._run):
        original_func = tool._run
        logger.info(f"[WRAPPER INIT] {tool.name} - Usando tool._run")
    else:
        logger.warning(
            f"[WRAPPER INIT] {tool.name} - Nenhum método encontrado, retornando original"
        )
        return tool

    is_async = inspect.iscoroutinefunction(original_func)

    if is_async:

        @wraps(original_func)
        async def async_wrapper(*args, **kwargs):
            tool_name = getattr(tool, "name", "unknown")
            logger.debug(f"[WRAPPER ASYNC] {tool_name} - args={args}, kwargs={kwargs}")

            # Se recebeu apenas 1 argumento e ele parece ser um JSON string
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
                arg = args[0]
                logger.debug(f"[WRAPPER] {tool_name} - Argumento string recebido: {arg[:150]}")

                try:
                    # Limpa o argumento de forma agressiva
                    cleaned = arg.strip()

                    # Remove markdown code fences (```json, ```, etc)
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                    cleaned = cleaned.strip()

                    # Remove quebras de linha e espaços extras dentro do JSON
                    # (mas preserva \n dentro de strings)
                    if cleaned.startswith("{") and cleaned.endswith("}"):
                        logger.debug(
                            f"[WRAPPER] {tool_name} - JSON detectado após limpeza: {cleaned[:150]}"
                        )
                        parsed = json.loads(cleaned)

                        if isinstance(parsed, dict):
                            logger.info(
                                f"[WRAPPER] {tool_name} - ✅ JSON parseado: {list(parsed.keys())}"
                            )
                            # Chama a função com os parâmetros corretos
                            return await original_func(**parsed)

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[WRAPPER] {tool_name} - ❌ Falha ao parsear: {e}")
                    logger.debug(f"[WRAPPER] {tool_name} - String que falhou: {arg[:200]}")

            # Se não conseguiu fazer parse ou não era JSON, chama normalmente
            return await original_func(*args, **kwargs)

        # Substitui AMBOS func e _run
        if hasattr(tool, "func"):
            tool.func = async_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool.func substituído (async)")
        if hasattr(tool, "_run"):
            tool._run = async_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool._run substituído (async)")

    else:

        @wraps(original_func)
        def sync_wrapper(*args, **kwargs):
            tool_name = getattr(tool, "name", "unknown")
            logger.debug(f"[WRAPPER SYNC] {tool_name} - args={args}, kwargs={kwargs}")

            # Se recebeu apenas 1 argumento e ele parece ser um JSON string
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
                arg = args[0]
                logger.debug(f"[WRAPPER] {tool_name} - Argumento string recebido: {arg[:150]}")

                try:
                    # Limpa o argumento de forma agressiva
                    cleaned = arg.strip()

                    # Remove markdown code fences (```json, ```, etc)
                    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                    cleaned = cleaned.strip()

                    # Remove quebras de linha e espaços extras dentro do JSON
                    # (mas preserva \n dentro de strings)
                    if cleaned.startswith("{") and cleaned.endswith("}"):
                        logger.debug(
                            f"[WRAPPER] {tool_name} - JSON detectado após limpeza: {cleaned[:150]}"
                        )
                        parsed = json.loads(cleaned)

                        if isinstance(parsed, dict):
                            logger.info(
                                f"[WRAPPER] {tool_name} - ✅ JSON parseado: {list(parsed.keys())}"
                            )
                            # Chama a função com os parâmetros corretos
                            return original_func(**parsed)

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[WRAPPER] {tool_name} - ❌ Falha ao parsear: {e}")
                    logger.debug(f"[WRAPPER] {tool_name} - String que falhou: {arg[:200]}")

            # Se não conseguiu fazer parse ou não era JSON, chama normalmente
            return original_func(*args, **kwargs)

        # Substitui AMBOS func e _run
        if hasattr(tool, "func"):
            tool.func = sync_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool.func substituído (sync)")
        if hasattr(tool, "_run"):
            tool._run = sync_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool._run substituído (sync)")

    return tool
