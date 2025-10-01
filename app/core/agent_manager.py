
import json
import logging
import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from enum import Enum
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
from app.core.llm_manager import get_llm_client, ModelRole, ModelPriority
from app.core.memory_core import memory_core
from app.core.prompt_loader import get_prompt
from app.models.schemas import Experience
from app.core.resilience import CircuitBreaker, CircuitOpenError
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Constantes configuráveis
MAX_ATTEMPTS = 3
INITIAL_BACKOFF = 1.0  # segundos
MAX_BACKOFF = 10.0  # segundos
OP_TIMEOUT = 30.0  # timeout por tentativa (segundos)
MAX_QUESTION_LENGTH = 10000  # caracteres


class AgentType(Enum):
    """Define os papéis especializados dos agentes."""
    ORCHESTRATOR = "orchestrator"
    TOOL_USER = "tool_user"
    META_AGENT = "meta_agent"


agent_circuit_breakers = {
    agent_type: CircuitBreaker(failure_threshold=3, recovery_timeout=60)
    for agent_type in AgentType
}


class AgentManager:
    """
    Centraliza a criação, configuração e execução de agentes especializados.
    """

    def __init__(self):
        """
        Inicializa o gerenciador de agentes, carregando o cliente LLM centralizado.
        """
        try:
            # Usa um modelo de alta qualidade para as tarefas de orquestração do agente
            self.llm_client = get_llm_client(
                role=ModelRole.ORCHESTRATOR, priority=ModelPriority.HIGH_QUALITY
            )
            if not self.llm_client:
                raise RuntimeError("LLM client retornou None.")
        except Exception as e:
            logger.critical(f"Falha crítica ao inicializar LLM Client: {e}", exc_info=True)
            raise RuntimeError(
                f"AgentManager não pode operar sem LLM. Causa: {e}"
            ) from e

    def _validate_question(self, question: str):
        """Valida a pergunta/instrução antes de processar."""
        if not question or not question.strip():
            raise ValueError("A pergunta não pode ser vazia.")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Pergunta excede o tamanho máximo de {MAX_QUESTION_LENGTH} caracteres.")

    def _get_agent_config(self, agent_type: AgentType) -> Tuple[str, List[BaseTool]]:
        """Retorna a configuração (prompt e ferramentas) para um tipo de agente."""
        if agent_type in [AgentType.ORCHESTRATOR, AgentType.TOOL_USER]:
            return get_prompt("react_agent"), get_tools_for_agent(agent_type)
        elif agent_type == AgentType.META_AGENT:
            return get_prompt("meta_agent_supervisor"), get_tools_for_agent(agent_type)
        else:
            raise ValueError(f"Configuração para o tipo de agente '{agent_type}' não encontrada.")

    def _create_agent_executor(self, agent_type: AgentType) -> AgentExecutor:
        """Cria uma instância de AgentExecutor para um tipo de agente específico."""
        prompt_template_str, tools = self._get_agent_config(agent_type)
        prompt = hub.pull("hwchase17/openai-tools-agent")
        
        # Usa o LLM base do nosso cliente, que é a instância do BaseChatModel
        agent = create_openai_tools_agent(self.llm_client.base, tools, prompt)

        error_handler = lambda error: (
            f"Erro: Ferramenta indisponível. Detalhes: {error}. Use uma das ferramentas disponíveis."
        )

        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=error_handler,
            return_intermediate_steps=True
        )

    async def run_agent_async(
        self,
        question: str,
        request: Optional[Request] = None,
        agent_type: AgentType = AgentType.TOOL_USER
    ) -> dict:
        """Executa um agente de forma totalmente assíncrona."""
        self._validate_question(question)
        correlation_id = getattr(request, "state", {}).correlation_id or "no-id"
        circuit_breaker = agent_circuit_breakers[agent_type]

        logger.info(f"[trace_id={correlation_id}] Iniciando execução async do agente '{agent_type.name}'")

        agent_executor = self._create_agent_executor(agent_type)
        last_error = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                async def protected_invoke():
                    return await agent_executor.ainvoke({"input": question}, {"recursion_limit": 5})

                protected_call = circuit_breaker(protected_invoke)
                result = await asyncio.wait_for(protected_call(), timeout=OP_TIMEOUT)

                logger.info(f"[trace_id={correlation_id}] Agente async '{agent_type.name}' concluiu com sucesso.")
                self._handle_successful_run(result, agent_type, question, correlation_id)
                return self._format_success_response(result)

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"[trace_id={correlation_id}] Timeout na tentativa {attempt + 1} do agente async.")
                await self._handle_retry_backoff(attempt, correlation_id)

            except CircuitOpenError as e:
                last_error = e
                logger.error(f"[trace_id={correlation_id}] Circuit Breaker aberto para '{agent_type.name}'. Abortando.")
                break

            except (PydanticValidationError, ValueError, TypeError) as e:
                logger.warning(f"[trace_id={correlation_id}] Erro de validação na ferramenta: {e}. Abortando.")
                return self._format_validation_error_response(e)

            except Exception as e:
                last_error = e
                logger.error(f"[trace_id={correlation_id}] Erro inesperado na tentativa {attempt + 1}: {e}", exc_info=True)
                await self._handle_retry_backoff(attempt, correlation_id)

        return self._format_failure_response(last_error, agent_type, correlation_id)

    async def _handle_retry_backoff(self, attempt: int, correlation_id: str):
        if attempt + 1 >= MAX_ATTEMPTS:
            return
        backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
        jitter = backoff_duration * 0.1 * random.random()
        sleep_time = backoff_duration + jitter
        logger.warning(f"[trace_id={correlation_id}] Aguardando {sleep_time:.2f}s antes de tentar novamente.")
        await asyncio.sleep(sleep_time)

    def _format_success_response(self, result: dict) -> dict:
        final_answer = result.get("output", "A tarefa foi concluída.")
        if isinstance(final_answer, AgentFinish):
            final_answer = final_answer.return_values.get("output", str(final_answer))
        return {"answer": final_answer, "intermediate_steps": result.get("intermediate_steps", [])}

    def _format_validation_error_response(self, error: Exception) -> dict:
        error_text = str(error)
        final_answer = (
            "Thought: A ação falhou devido a um erro de validação. Devo parar e informar o erro.\n"
            f"Final Answer: Falha ao usar a ferramenta. Detalhes: {error_text}. "
            "Verifique se todos os argumentos obrigatórios foram fornecidos."
        )
        return {"answer": final_answer, "intermediate_steps": []}

    def _format_failure_response(self, error: Optional[Exception], agent_type: AgentType, correlation_id: str) -> dict:
        error_msg = str(error) if error else "O agente falhou em todas as tentativas."
        logger.error(f"[trace_id={correlation_id}] Todas as {MAX_ATTEMPTS} tentativas falharam. Último erro: {error_msg}")
        return {
            "error": f"Falha ao executar agente '{agent_type.name}' após {MAX_ATTEMPTS} tentativas. Último erro: {error_msg}",
            "trace_id": correlation_id
        }

    def run_agent(
        self,
        question: str,
        request: Optional[Request] = None,
        agent_type: AgentType = AgentType.TOOL_USER
    ) -> dict:
        """Executa um agente especializado para responder a uma pergunta ou completar uma tarefa."""
        try:
            self._validate_question(question)
        except ValueError as e:
            logger.error(f"Validação de entrada falhou: {e}")
            return {"error": str(e)}

        correlation_id = getattr(request, "state", {}).correlation_id or "no-id"

        try:
            circuit_breaker = agent_circuit_breakers[agent_type]
            logger.info(f"[trace_id={correlation_id}] Iniciando execução do agente '{agent_type.name}' para: '{question[:200]}...'")
            agent_executor = self._create_agent_executor(agent_type)

            last_error = None
            for attempt in range(MAX_ATTEMPTS):
                executor = None
                try:
                    logger.info(f"[trace_id={correlation_id}] Invocando AgentExecutor, Tentativa {attempt + 1}/{MAX_ATTEMPTS}...")

                    invoke_func = lambda: agent_executor.invoke({"input": question}, {"recursion_limit": 5})
                    protected_invoke = circuit_breaker(invoke_func)

                    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"agent_{agent_type.name}")
                    future = executor.submit(protected_invoke)
                    result = future.result(timeout=OP_TIMEOUT)
                    
                    logger.info(f"[trace_id={correlation_id}] Agente '{agent_type.name}' concluiu com sucesso.")
                    self._handle_successful_run(result, agent_type, question, correlation_id)
                    return self._format_success_response(result)

                except (PydanticValidationError, ValueError, TypeError) as e:
                    logger.warning(f"[trace_id={correlation_id}] Erro de validação na ferramenta: {e}. Abortando.")
                    return self._format_validation_error_response(e)
                
                except (CircuitOpenError, TimeoutError) as e:
                    last_error = e
                    logger.warning(f"[trace_id={correlation_id}] Erro na tentativa {attempt + 1}: {e}")
                    if isinstance(e, CircuitOpenError):
                        break # Aborta se o circuito estiver aberto
                    
                    backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                    time.sleep(backoff_duration + random.uniform(0, backoff_duration * 0.1))

                except Exception as e:
                    last_error = e
                    logger.error(f"[trace_id={correlation_id}] Erro inesperado na tentativa {attempt + 1}: {e}", exc_info=True)
                    backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                    time.sleep(backoff_duration + random.uniform(0, backoff_duration * 0.1))

                finally:
                    if executor:
                        executor.shutdown(wait=False, cancel_futures=True)

            return self._format_failure_response(last_error, agent_type, correlation_id)

        except Exception as e:
            logger.critical(f"[trace_id={correlation_id}] Erro CRÍTICO ao executar o agente '{agent_type.name}': {e}", exc_info=True)
            return self._format_failure_response(e, agent_type, correlation_id)

    def _handle_successful_run(self, result: dict, agent_type: AgentType, question: str, correlation_id: str):
        """Memoriza experiências de sucesso."""
        intermediate_steps = result.get("intermediate_steps", [])
        if not intermediate_steps:
            return

        try:
            last_step = intermediate_steps[-1]
            action, observation = last_step
            if "Erro:" not in str(observation):
                experience_content = (
                    f"Ao receber a tarefa '{question}', "
                    f"usei a ferramenta '{action.tool}' com os parâmetros '{json.dumps(action.tool_input, ensure_ascii=False)}'. "
                    f"O resultado foi: '{observation}'"
                )
                experience = Experience(
                    type="action_success",
                    content=experience_content,
                    metadata={
                        "agent_type": agent_type.name,
                        "tool_used": action.tool,
                        "tool_input": action.tool_input,
                        "original_question": question,
                        "trace_id": correlation_id
                    }
                )
                memory_core.memorize(experience)
                logger.info(f"[trace_id={correlation_id}] Experiência de sucesso com '{action.tool}' foi memorizada.")
        except Exception as e:
            logger.warning(f"[trace_id={correlation_id}] Falha ao memorizar experiência: {e}", exc_info=False)

# Instância única para ser usada na aplicação
agent_manager = AgentManager()
