# app/core/agent_manager.py
# REFATORAÇÃO SPRINT 11: Evoluído de 'reasoning_core.py' para suportar uma arquitetura multiagente.
# Este módulo agora atua como uma fábrica e executor para diferentes tipos de agentes especializados.

import json
import logging
import time
import random  # Para adicionar jitter ao backoff
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from enum import Enum
from typing import List, Tuple

from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.tools import BaseTool
from langchain_core.agents import AgentFinish

# Import opcional para detectar erros de validação de ferramentas
try:
    from pydantic import ValidationError as PydanticValidationError
except Exception:  # fallback para ambientes onde a importação não esteja disponível
    class PydanticValidationError(Exception):
        pass

# Importações adicionais para depuração e prompts
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

from app.core.agent_tools import unified_tools, recall_experiences, analyze_memory_for_failures
from app.core.llm_manager import get_llm
# --- NOVA IMPORTAÇÃO PARA O CICLO DE MEMÓRIA ---
from app.core.memory_core import memory_core
from app.core.prompt_loader import get_prompt
from app.models.schemas import Experience

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """
    Define os papéis especializados dos agentes dentro do ecossistema Janus.
    Isso permite a criação de agentes com diferentes prompts e conjuntos de ferramentas.
    """
    ORCHESTRATOR = "orchestrator"  # Agente de alto nível para decomposição de tarefas.
    TOOL_USER = "tool_user"  # Agente genérico para execução de ferramentas.
    META_AGENT = "meta_agent"  # Novo agente supervisor


class AgentManager:
    """
    Centraliza a criação, configuração e execução de agentes especializados.
    Atua como uma fábrica, garantindo que cada agente seja instanciado com o
    prompt e as ferramentas corretas para sua função.
    """

    def __init__(self):
        """
        Inicializa o gerenciador de agentes, carregando o LLM centralizado.
        """
        self.llm = get_llm()
        if not self.llm:
            raise RuntimeError("LLM não pôde ser inicializado. O AgentManager não pode operar.")

    def _get_agent_config(self, agent_type: AgentType) -> Tuple[str, List[BaseTool]]:
        """
        Retorna a configuração (prompt e ferramentas) para um tipo de agente específico.
        Esta função é o núcleo da especialização de agentes.

        Args:
            agent_type: O tipo de agente a ser configurado.

        Returns:
            Uma tupla contendo o template do prompt e a lista de ferramentas.
        """
        if agent_type == AgentType.ORCHESTRATOR:
            prompt_template = get_prompt("react_agent")
            tools: List[BaseTool] = [recall_experiences]
            logger.info(f"Configurando agente {agent_type.name} com {len(tools)} ferramentas especializadas.")
            return prompt_template, tools

        elif agent_type == AgentType.TOOL_USER:
            prompt_template = get_prompt("react_agent")
            tools: List[BaseTool] = unified_tools
            logger.info(f"Configurando agente {agent_type.name} com o conjunto de {len(tools)} ferramentas unificadas.")
            return prompt_template, tools

        # --- NOVA CONFIGURAÇÃO PARA O META-AGENTE ---
        elif agent_type == AgentType.META_AGENT:
            prompt_template = get_prompt("meta_agent_supervisor")
            tools: List[BaseTool] = [analyze_memory_for_failures]
            logger.info(f"Configurando agente {agent_type.name} com {len(tools)} ferramentas de supervisão.")
            return prompt_template, tools
        # --- FIM DA MODIFICAÇÃO ---

        else:
            raise ValueError(f"Configuração para o tipo de agente '{agent_type}' não encontrada.")

    def _create_agent_executor(self, agent_type: AgentType) -> AgentExecutor:
        """
        Cria uma instância de AgentExecutor para um tipo de agente específico.
        """
        prompt_template_str, tools = self._get_agent_config(agent_type)

        debug_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_template_str),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ]
        )
        rendered_tools = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        full_prompt_template = debug_prompt.partial(tools=rendered_tools)

        print("--- INÍCIO DO PROMPT DO AGENTE (PARA DEPURAÇÃO) ---")
        print(full_prompt_template.format(input="Exemplo de Pergunta", agent_scratchpad=[]))
        print("--- FIM DO PROMPT DO AGENTE (PARA DEPURAÇÃO) ---")


        # 3. Usar o método original e estável do hub para criar o prompt REAL.
        prompt = hub.pull("hwchase17/openai-tools-agent")

        agent = create_openai_tools_agent(self.llm, tools, prompt)

        error_handler = lambda error: (
            "Erro: Essa ferramenta não está disponível para mim. "
            f"Detalhes: {error}. Por favor, escolha uma das ferramentas disponíveis."
        )

        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=error_handler,
            return_intermediate_steps=True
        )

    def run_agent(self, question: str, agent_type: AgentType = AgentType.TOOL_USER) -> dict:
        """
        Executa um agente especializado para responder a uma pergunta ou completar uma tarefa.
        """
        try:
            logger.info(
                f"Iniciando execução do agente do tipo '{agent_type.name}' para a instrução: '{question}'"
            )

            agent_executor = self._create_agent_executor(agent_type)

            # --- POLÍTICA DE RETRY COM EXPONENTIAL BACKOFF E TIMEOUT ---
            MAX_ATTEMPTS = 3
            INITIAL_BACKOFF = 1.0  # segundos
            MAX_BACKOFF = 10.0     # segundos
            OP_TIMEOUT = 30.0      # timeout por tentativa (segundos)
            # --- FIM DA POLÍTICA ---
            result = None
            last_error = None
            state = "INIT"

            start = time.time()
            for attempt in range(MAX_ATTEMPTS):
                try:
                    state = "RUNNING"
                    logger.info(f"Invocando AgentExecutor (tipo: {agent_type.name}), Tentativa {attempt + 1}/{MAX_ATTEMPTS}...")

                    # Executa com timeout usando ThreadPoolExecutor para simular uma máquina de estados com TIMEOUT
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            agent_executor.invoke,
                            {"input": question},
                            {"recursion_limit": 5}
                        )
                        result = future.result(timeout=OP_TIMEOUT)

                    state = "SUCCESS"
                    logger.info(f"AgentExecutor (tipo: {agent_type.name}) concluiu a execução com sucesso.")
                    break  # Sai do loop se a execução for bem-sucedida
                except Exception as e:
                    # Se um erro de validação de entrada da ferramenta ocorrer, devemos PARAR imediatamente
                    # e devolver uma resposta final explicando o erro (conforme regras do prompt do agente).
                    error_text = str(e)
                    is_validation_error = (
                        isinstance(e, PydanticValidationError)
                        or e.__class__.__name__.lower().endswith("validationerror")
                        or ("validation error" in error_text.lower())
                    )
                    if is_validation_error:
                        state = "VALIDATION_ERROR"
                        logger.warning(
                            f"Erro de validação ao chamar ferramenta na tentativa {attempt + 1}: {e}. Encerrando sem novas tentativas."
                        )
                        final_answer = (
                            "Thought: Uma ação resultou em erro ao usar a ferramenta. Pela regra, devo parar e explicar o erro.\n"
                            f"Final Answer: Falha ao executar a ferramenta devido a erro de validação dos parâmetros. Detalhes: {error_text}. "
                            "Para a ferramenta 'write_file', o campo 'content' é obrigatório além de 'file_path'."
                        )
                        return {
                            "answer": final_answer,
                            "intermediate_steps": [],
                        }

                    # Lógica de exponential backoff com jitter
                    backoff_duration = min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempt))
                    jitter = backoff_duration * 0.1 * random.random()  # 10% de jitter
                    sleep_time = backoff_duration + jitter

                    last_error = e if not isinstance(e, FuturesTimeoutError) else TimeoutError(
                        f"Execução do agente excedeu o timeout de {OP_TIMEOUT}s na tentativa {attempt + 1}."
                    )

                    reason = "timeout" if isinstance(e, FuturesTimeoutError) else "erro"
                    state = "RETRY_WAIT"
                    logger.warning(
                        f"Tentativa {attempt + 1} falhou para o agente '{agent_type.name}' por {reason}: {e}. "
                        f"Aguardando {sleep_time:.2f} segundos antes de tentar novamente."
                    )
                    time.sleep(sleep_time)
            
            if result is None:
                # Se o loop terminar sem sucesso, lança a última exceção capturada.
                raise last_error if last_error else RuntimeError("O agente falhou em todas as tentativas sem um erro específico.")

            elapsed_ms = round((time.time() - start) * 1000, 1)
            intermediate_steps = result.get("intermediate_steps", [])

            # Observabilidade mínima: trace da execução
            try:
                tools_invoked = [getattr(step[0], 'tool', 'unknown') for step in intermediate_steps]
                tool_inputs = [getattr(step[0], 'tool_input', {}) for step in intermediate_steps]
                sanitized_inputs = [json.dumps(inp, ensure_ascii=False)[:500] for inp in tool_inputs]
                observations = [str(step[1])[:500] for step in intermediate_steps]
                logger.info({
                    "event": "agent_trace",
                    "agent_type": agent_type.name,
                    "question": question[:500],
                    "tools_invoked": tools_invoked,
                    "inputs": sanitized_inputs,
                    "observations": observations,
                    "latency_ms": elapsed_ms
                })
            except Exception:
                pass

            if intermediate_steps:
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
                            "original_question": question
                        }
                    )
                    memory_core.memorize(experience)
                    logger.info(f"Experiência de sucesso com a ferramenta '{action.tool}' foi memorizada.")

            final_answer = result.get("output", "A tarefa foi concluída.")
            if isinstance(final_answer, AgentFinish):
                final_answer = final_answer.return_values.get("output", str(final_answer))

            return {
                "answer": final_answer,
                "intermediate_steps": intermediate_steps,
            }

        except Exception as e:
            logger.error(f"Erro inesperado ao executar o agente '{agent_type.name}' após todas as tentativas: {e}", exc_info=True)
            return {"error": f"Ocorreu um erro crítico e inesperado durante a execução do agente '{agent_type.name}'."}


# Instância única para ser usada na aplicação, seguindo o padrão singleton.
agent_manager = AgentManager()
