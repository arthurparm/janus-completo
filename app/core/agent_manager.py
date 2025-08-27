# app/core/agent_manager.py
# REFATORAÇÃO SPRINT 11: Evoluído de 'reasoning_core.py' para suportar uma arquitetura multiagente.
# Este módulo agora atua como uma fábrica e executor para diferentes tipos de agentes especializados.

import json
import logging
from enum import Enum
from typing import List, Tuple

from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.tools import BaseTool
from langchain_core.agents import AgentFinish

from app.core.agent_tools import unified_tools, recall_experiences
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
    # Futuros agentes podem ser adicionados aqui, ex: CODE_GENERATOR, SELF_REFLECTION


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
            # O orquestrador tem um conjunto de ferramentas restrito, focado em planejamento e memória.
            prompt_template = get_prompt("react_agent")
            tools: List[BaseTool] = [recall_experiences]
            logger.info(f"Configurando agente {agent_type.name} com {len(tools)} ferramentas especializadas.")
            return prompt_template, tools

        elif agent_type == AgentType.TOOL_USER:
            # O agente de ferramentas tem acesso a todas as ferramentas para execução de tarefas.
            prompt_template = get_prompt("react_agent")
            tools: List[BaseTool] = unified_tools
            logger.info(f"Configurando agente {agent_type.name} com o conjunto de {len(tools)} ferramentas unificadas.")
            return prompt_template, tools

        else:
            raise ValueError(f"Configuração para o tipo de agente '{agent_type}' não encontrada.")

    def _create_agent_executor(self, agent_type: AgentType) -> AgentExecutor:
        """
        Cria uma instância de AgentExecutor para um tipo de agente específico.

        Args:
            agent_type: O tipo de agente a ser criado.

        Returns:
            Uma instância configurada de AgentExecutor.
        """
        prompt_template, tools = self._get_agent_config(agent_type)

        _ = prompt_template
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
            return_intermediate_steps=True  # Garante que os passos sejam sempre retornados
        )

    def run_agent(self, question: str, agent_type: AgentType = AgentType.TOOL_USER) -> dict:
        """
        Executa um agente especializado para responder a uma pergunta ou completar uma tarefa.

        Args:
            question: A instrução ou pergunta para o agente.
            agent_type: O tipo de agente a ser executado. O padrão é TOOL_USER.

        Returns:
            Um dicionário contendo a resposta e os passos intermediários.
        """
        try:
            logger.info(
                f"Iniciando execução do agente do tipo '{agent_type.name}' para a instrução: '{question}'"
            )

            agent_executor = self._create_agent_executor(agent_type)

            logger.info(f"Invocando AgentExecutor (tipo: {agent_type.name})...")
            result = agent_executor.invoke(
                {"input": question},
                {"recursion_limit": 5}
            )
            logger.info(f"AgentExecutor (tipo: {agent_type.name}) concluiu a execução.")

            # --- IMPLEMENTAÇÃO DO CICLO DE MEMÓRIA AUTOMÁTICA ---
            # Após uma execução bem-sucedida, criamos uma memória do que foi feito.
            intermediate_steps = result.get("intermediate_steps", [])
            if intermediate_steps:
                # Vamos memorizar a última ação bem-sucedida
                last_step = intermediate_steps[-1]
                action, observation = last_step

                # O 'observation' é o resultado da ferramenta. Se não for um erro, memorizamos.
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
            # Se a resposta for um objeto AgentFinish, extraímos o valor de 'return_values'
            if isinstance(final_answer, AgentFinish):
                final_answer = final_answer.return_values.get("output", str(final_answer))

            return {
                "answer": final_answer,
                "intermediate_steps": intermediate_steps,
            }

        except Exception as e:
            logger.error(f"Erro inesperado ao executar o agente '{agent_type.name}': {e}", exc_info=True)
            return {"error": f"Ocorreu um erro crítico e inesperado durante a execução do agente '{agent_type.name}'."}


# Instância única para ser usada na aplicação, seguindo o padrão singleton.
agent_manager = AgentManager()
