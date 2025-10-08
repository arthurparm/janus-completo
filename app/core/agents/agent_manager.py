import asyncio
import logging
import random
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

from app.core.tools.agent_tools import get_tools_for_agent
from app.core.infrastructure.enums import AgentType
from app.core.llm.llm_manager import get_llm_client, ModelRole, ModelPriority
from app.core.memory.memory_core import memory_core
from app.core.infrastructure.prompt_loader import get_prompt
from app.models.schemas import Experience
from app.core.infrastructure.resilience import CircuitBreaker, CircuitOpenError, CircuitBreakerState
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Constantes configuráveis
MAX_ATTEMPTS = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0
OP_TIMEOUT = 60.0  # Aumentado para operações async
MAX_QUESTION_LENGTH = 10000

agent_circuit_breakers = {
    agent_type: CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    for agent_type in AgentType
}


def reset_agent_circuit_breaker(agent_type: Optional[AgentType] = None):
    """Reseta o circuit breaker de um agente específico ou de todos."""
    if agent_type:
        cb = agent_circuit_breakers.get(agent_type)
        if cb:
            cb.state = CircuitBreakerState.CLOSED
            cb.failure_count = 0
            cb.last_failure_time = None
            cb._open_since = None
            logger.info(f"Circuit breaker resetado para agente: {agent_type.name}")
    else:
        for agent_t, cb in agent_circuit_breakers.items():
            cb.state = CircuitBreakerState.CLOSED
            cb.failure_count = 0
            cb.last_failure_time = None
            cb._open_since = None
        logger.info("Todos os circuit breakers de agentes foram resetados")


class AgentManager:
    """Centraliza a criação, configuração e execução de agentes especializados."""

    def __init__(self):
        try:
            self.llm_client = get_llm_client(
                role=ModelRole.ORCHESTRATOR, priority=ModelPriority.FAST_AND_CHEAP
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
        logger.info(f"[Agent] Getting config for {agent_type.name}...")
        _, tools = self._get_agent_config(agent_type)
        logger.info(f"[Agent] Got {len(tools)} tools, pulling prompt from hub...")

        try:
            prompt = hub.pull("hwchase17/openai-tools-agent")
            logger.info(f"[Agent] Prompt pulled successfully")
        except Exception as e:
            logger.error(f"[Agent] Failed to pull prompt: {e}", exc_info=True)
            raise

        try:
            agent = create_openai_tools_agent(self.llm_client.base, tools, prompt)
            logger.info(f"[Agent] Agent created successfully")
        except Exception as e:
            logger.error(f"[Agent] Failed to create agent: {e}", exc_info=True)
            raise

        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=lambda error: f"Erro de parsing: {error}",
            return_intermediate_steps=True
        )
        logger.info(f"[Agent] Executor ready")
        return executor

    async def arun_agent(
            self,
            question: str,
            request: Optional[Request] = None,
            agent_type: AgentType = AgentType.TOOL_USER
    ) -> dict:
        """Executa um agente especializado de forma assíncrona com resiliência."""
        self._validate_question(question)
        correlation_id = getattr(getattr(request, "state", None), "correlation_id", None) or "no-id"
        circuit_breaker = agent_circuit_breakers[agent_type]
        logger.info(
            f"[trace_id={correlation_id}] Iniciando execução do agente '{agent_type.name}' para: '{question[:200]}...'")
        logger.info(
            f"[trace_id={correlation_id}] Circuit breaker estado: {circuit_breaker.state.value}, failures: {circuit_breaker.failure_count}, id={id(circuit_breaker)}")

        try:
            logger.info(f"[trace_id={correlation_id}] Criando agent executor...")
            agent_executor = self._create_agent_executor(agent_type)
            logger.info(f"[trace_id={correlation_id}] Agent executor criado com sucesso")
        except Exception as e:
            logger.error(f"[trace_id={correlation_id}] Falha ao criar agent executor: {e}", exc_info=True)
            circuit_breaker._on_failure(agent_type.name)
            return {"answer": f"Erro ao inicializar agente: {e}"}

        last_error = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                logger.info(
                    f"[trace_id={correlation_id}] ANTES do check: CB state={circuit_breaker.state.value}, failures={circuit_breaker.failure_count}")
                if circuit_breaker.is_open():
                    logger.warning(f"[trace_id={correlation_id}] Circuit breaker is OPEN, abortando")
                    raise CircuitOpenError("Circuit breaker is open.")

                result = await asyncio.wait_for(
                    agent_executor.ainvoke({"input": question}, {"recursion_limit": 5}),
                    timeout=OP_TIMEOUT
                )

                circuit_breaker._on_success(agent_type.name)
                logger.info(f"[trace_id={correlation_id}] Agente '{agent_type.name}' concluiu com sucesso.")
                await self._ahandle_successful_run(result, agent_type, question, correlation_id)
                return self._format_success_response(result)

            except (PydanticValidationError, ValueError, TypeError) as e:
                logger.warning(f"[trace_id={correlation_id}] Erro de validação na ferramenta: {e}. Abortando.")
                return self._format_validation_error_response(e)

            except (CircuitOpenError, asyncio.TimeoutError) as e:
                last_error = e
                logger.warning(f"[trace_id={correlation_id}] Erro na tentativa {attempt + 1}: {type(e).__name__}")
                if isinstance(e, CircuitOpenError):
                    # Não registra falha adicional - circuit breaker já está aberto
                    break
                else:
                    # Apenas timeout deve registrar falha
                    circuit_breaker._on_failure(agent_type.name)

                backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                await asyncio.sleep(backoff_duration + random.uniform(0, backoff_duration * 0.1))

            except Exception as e:
                circuit_breaker.record_failure()
                last_error = e
                logger.error(f"[trace_id={correlation_id}] Erro inesperado na tentativa {attempt + 1}: {e}",
                             exc_info=True)
                backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                await asyncio.sleep(backoff_duration + random.uniform(0, backoff_duration * 0.1))

        return self._format_failure_response(last_error, agent_type, correlation_id)

    async def _ahandle_successful_run(self, result: dict, agent_type: AgentType, question: str, correlation_id: str):
        intermediate_steps = result.get("intermediate_steps", [])
        if not intermediate_steps:
            return

        try:
            last_step = intermediate_steps[-1]
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
                await memory_core.amemorize(experience)
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
        logger.error(
            f"[trace_id={correlation_id}] Todas as {MAX_ATTEMPTS} tentativas falharam. Último erro: {error_msg}")
        return {"error": f"Falha ao executar agente '{agent_type.name}'. Último erro: {error_msg}"}


agent_manager = AgentManager()
