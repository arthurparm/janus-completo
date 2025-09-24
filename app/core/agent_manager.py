# app/core/agent_manager.py
# REFATORAÇÃO SPRINT 11: Evoluído de 'reasoning_core.py' para suportar uma arquitetura multiagente.
# Este módulo agora atua como uma fábrica e executor para diferentes tipos de agentes especializados.

import json
import logging
import time
from enum import Enum
from typing import List, Tuple

from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.tools import BaseTool
from langchain_core.agents import AgentFinish

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

            MAX_ATTEMPTS = 3
            result = None
            last_error = None

            start = time.time()
            for attempt in range(MAX_ATTEMPTS):
                try:
                    logger.info(f"Invocando AgentExecutor (tipo: {agent_type.name}), Tentativa {attempt + 1}/{MAX_ATTEMPTS}...")
                    result = agent_executor.invoke(
                        {"input": question},
                        {"recursion_limit": 5}
                    )
                    logger.info(f"AgentExecutor (tipo: {agent_type.name}) concluiu a execução com sucesso.")
                    break  # Sai do loop se a execução for bem-sucedida
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Tentativa {attempt + 1} falhou para o agente '{agent_type.name}' com o erro: {e}. "
                        f"Aguardando 2 segundos antes de tentar novamente."
                    )
                    time.sleep(2)
            
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
