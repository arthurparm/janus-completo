import logging

from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor

from app.core.agent_tools import unified_tools
from app.core.llm_manager import get_llm

logger = logging.getLogger(__name__)


def run_agent_executor(question: str) -> dict:
    """
    Cria e executa um agente com acesso a todas as ferramentas disponíveis,
    utilizando o LLM fornecido pelo gestor central.
    """
    try:
        logger.info(f"Recebida a instrução para o agente unificado: '{question}'")

        llm = get_llm()

        prompt = hub.pull("hwchase17/openai-tools-agent")

        agent = create_openai_tools_agent(llm, unified_tools, prompt)

        agent_executor = AgentExecutor(agent=agent, tools=unified_tools, verbose=True)

        logger.info("Invocando o AgentExecutor unificado...")
        result = agent_executor.invoke({"input": question})

        logger.info("AgentExecutor unificado concluiu a execução.")

        return {
            "answer": result.get("output", "A tarefa foi concluída."),
            "intermediate_steps": result.get("intermediate_steps", [])
        }

    except Exception as e:
        logger.error(f"Erro ao executar o agente unificado: {e}", exc_info=True)
        return {"error": "Ocorreu um erro durante a execução do agente."}
