# app/core/agent_manager.py
# REFATORAÇÃO SPRINT 11: Evoluído de 'reasoning_core.py' para suportar uma arquitetura multiagente.
# Este módulo agora atua como uma fábrica e executor para diferentes tipos de agentes especializados.

import logging
from enum import Enum
from typing import List, Tuple

from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.tools import BaseTool

from app.core.llm_manager import get_llm
from app.core.agent_tools import unified_tools, recall_experiences
from app.core.prompt_loader import get_prompt

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """
    Define os papéis especializados dos agentes dentro do ecossistema Janus.
    Isso permite a criação de agentes com diferentes prompts e conjuntos de ferramentas.
    """
    ORCHESTRATOR = "orchestrator"  # Agente de alto nível para decomposição de tarefas.
    TOOL_USER = "tool_user"        # Agente genérico para execução de ferramentas.
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
            # O orquestrador pode ter um primeiro prompt mais estratégico e, inicialmente, menos ferramentas.
            prompt_template = get_prompt("react_agent")  # Usando o prompt padrão por enquanto
            tools: List[BaseTool] = [recall_experiences]  # Ex: Apenas ferramentas de recuperação de memória para planejamento
            logger.info(f"Configurando agente {agent_type.name} com {len(tools)} ferramentas especializadas.")
            return prompt_template, tools

        elif agent_type == AgentType.TOOL_USER:
            # O agente de ferramentas tem acesso a todas as ferramentas para execução de tarefas.
            prompt_template = get_prompt("react_agent")  # Prompt focado em execução
            tools: List[BaseTool] = unified_tools
            logger.info(f"Configurando agente {agent_type.name} com o conjunto de {len(tools)} ferramentas unificadas.")
            return prompt_template, tools

        # Adicionar outras configurações de agente aqui...
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

        # Puxa o prompt do LangChain Hub com base no template carregado
        # No futuro, poderíamos ter diferentes prompts no hub ou customizados
        _ = prompt_template  # Mantém referência ao template carregado (pode ser usado futuramente)
        prompt = hub.pull("hwchase17/openai-tools-agent")

        agent = create_openai_tools_agent(self.llm, tools, prompt)

        return AgentExecutor(agent=agent, tools=tools, verbose=True)

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
            result = agent_executor.invoke({"input": question})
            logger.info(f"AgentExecutor (tipo: {agent_type.name}) concluiu a execução.")

            return {
                "answer": result.get("output", "A tarefa foi concluída com sucesso."),
                "intermediate_steps": result.get("intermediate_steps", []),
            }

        except Exception as e:
            logger.error(f"Erro ao executar o agente '{agent_type.name}': {e}", exc_info=True)
            return {"error": f"Ocorreu um erro durante a execução do agente '{agent_type.name}'."}


# Instância única para ser usada na aplicação, seguindo o padrão singleton.
agent_manager = AgentManager()
