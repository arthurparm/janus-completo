
import json
import logging
import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Tuple, Optional

from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.tools import BaseTool
from langchain_core.agents import AgentFinish

try:
    from pydantic import ValidationError as PydanticValidationError
except ImportError:
    class PydanticValidationError(Exception):
        pass

from app.core.agent_tools import get_tools_for_agent
from app.core.enums import AgentType  # <-- Corrigido
from app.core.llm_manager import get_llm_client, ModelRole, ModelPriority
from app.core.memory_core import memory_core
from app.core.prompt_loader import get_prompt
from app.models.schemas import Experience
from app.core.resilience import CircuitBreaker, CircuitOpenError
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Constantes configuráveis
MAX_ATTEMPTS = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0
OP_TIMEOUT = 30.0
MAX_QUESTION_LENGTH = 10000

agent_circuit_breakers = {
    agent_type: CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    for agent_type in AgentType
}

class AgentManager:
    """Centraliza a criação, configuração e execução de agentes especializados."""

    def __init__(self):
        try:
            self.llm_client = get_llm_client(
                role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY
            )
            if not self.llm_client:
                raise RuntimeError("LLM client retornou None.")
        except Exception as e:
            logger.critical(f"Falha crítica ao inicializar LLM Client: {e}", exc_info=True)
            raise RuntimeError(f"AgentManager não pode operar sem LLM. Causa: {e}") from e

    def _validate_question(self, question: str):
        if not question or not question.strip():
            raise ValueError("A pergunta não pode ser vazia.")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Pergunta excede o tamanho máximo de {MAX_QUESTION_LENGTH} caracteres.")

    def _get_agent_config(self, agent_type: AgentType) -> Tuple[str, List[BaseTool]]:
        if agent_type in [AgentType.ORCHESTRATOR, AgentType.TOOL_USER]:
            return get_prompt("react_agent"), get_tools_for_agent(agent_type)
        elif agent_type == AgentType.META_AGENT:
            return get_prompt("meta_agent_supervisor"), get_tools_for_agent(agent_type)
        else:
            raise ValueError(f"Configuração para o tipo de agente '{agent_type}' não encontrada.")

    def _create_agent_executor(self, agent_type: AgentType) -> AgentExecutor:
        _, tools = self._get_agent_config(agent_type)
        prompt = hub.pull("hwchase17/openai-tools-agent")
        agent = create_openai_tools_agent(self.llm_client.base, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=lambda error: f"Erro de parsing: {error}",
            return_intermediate_steps=True
        )

    def run_agent(
        self,
        question: str,
        request: Optional[Request] = None,
        agent_type: AgentType = AgentType.TOOL_USER
    ) -> dict:
        """Executa um agente especializado de forma síncrona com resiliência."""
        self._validate_question(question)
        correlation_id = getattr(request, "state", {}).correlation_id or "no-id"
        circuit_breaker = agent_circuit_breakers[agent_type]
        logger.info(f"[trace_id={correlation_id}] Iniciando execução do agente '{agent_type.name}' para: '{question[:200]}...'")
        
        agent_executor = self._create_agent_executor(agent_type)
        last_error = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                invoke_func = lambda: agent_executor.invoke({"input": question}, {"recursion_limit": 5})
                protected_invoke = circuit_breaker(invoke_func)

                with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"agent_{agent_type.name}") as executor:
                    future = executor.submit(protected_invoke)
                    result = future.result(timeout=OP_TIMEOUT)

                logger.info(f"[trace_id={correlation_id}] Agente '{agent_type.name}' concluiu com sucesso.")
                self._handle_successful_run(result, agent_type, question, correlation_id)
                return self._format_success_response(result)

            except (PydanticValidationError, ValueError, TypeError) as e:
                logger.warning(f"[trace_id={correlation_id}] Erro de validação na ferramenta: {e}. Abortando.")
                return self._format_validation_error_response(e)
            
            except (CircuitOpenError, FuturesTimeoutError, TimeoutError) as e:
                last_error = e
                logger.warning(f"[trace_id={correlation_id}] Erro na tentativa {attempt + 1}: {type(e).__name__}")
                if isinstance(e, CircuitOpenError):
                    break
                
                backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                time.sleep(backoff_duration + random.uniform(0, backoff_duration * 0.1))

            except Exception as e:
                last_error = e
                logger.error(f"[trace_id={correlation_id}] Erro inesperado na tentativa {attempt + 1}: {e}", exc_info=True)
                backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                time.sleep(backoff_duration + random.uniform(0, backoff_duration * 0.1))

        return self._format_failure_response(last_error, agent_type, correlation_id)

    def _handle_successful_run(self, result: dict, agent_type: AgentType, question: str, correlation_id: str):
        intermediate_steps = result.get("intermediate_steps", [])
        if not intermediate_steps:
            return

        try:
            last_step = intermediate_steps[-1] # <-- Corrigido
            action, observation = last_step
            if "Erro:" not in str(observation):
                experience = Experience(
                    type="action_success",
                    content=f"Ao receber a tarefa '{question}', usei a ferramenta '{action.tool}' e obtive: '{observation}'",
                    metadata={
                        "agent_type": agent_type.name,
                        "tool_used": action.tool,
                        "tool_input": action.tool_input,
                        "trace_id": correlation_id
                    }
                )
                memory_core.memorize(experience)
                logger.info(f"[trace_id={correlation_id}] Experiência de sucesso com '{action.tool}' foi memorizada.")
        except Exception as e:
            logger.warning(f"[trace_id={correlation_id}] Falha ao memorizar experiência: {e}", exc_info=False)

    def _format_success_response(self, result: dict) -> dict:
        final_answer = result.get("output", "A tarefa foi concluída.")
        if isinstance(final_answer, AgentFinish):
            final_answer = final_answer.return_values.get("output", str(final_answer))
        return {"answer": final_answer, "intermediate_steps": result.get("intermediate_steps", [])}

    def _format_validation_error_response(self, error: Exception) -> dict:
        return {"answer": f"Final Answer: Falha de validação ao usar a ferramenta. Detalhes: {error}"}

    def _format_failure_response(self, error: Optional[Exception], agent_type: AgentType, correlation_id: str) -> dict:
        error_msg = str(error) if error else "O agente falhou em todas as tentativas."
        logger.error(f"[trace_id={correlation_id}] Todas as {MAX_ATTEMPTS} tentativas falharam. Último erro: {error_msg}")
        return {"error": f"Falha ao executar agente '{agent_type.name}'. Último erro: {error_msg}"}

agent_manager = AgentManager()
