# app/core/reasoning_core.py
import logging
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from app.config import settings
# MELHORIA: Importa a lista de ferramentas unificada.
from app.core.agent_tools import unified_tools

logger = logging.getLogger(__name__)


def run_agent_executor(question: str) -> dict:
    """
    Cria e executa um agente com acesso a todas as ferramentas disponíveis.
    """
    try:
        logger.info(f"Recebida a instrução para o agente unificado: '{question}'")
        
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0,
            api_key=settings.OPENAI_API_KEY.get_secret_value()
        )

        prompt = hub.pull("hwchase17/openai-tools-agent")
        
        # O agente agora é criado com o conjunto completo de ferramentas.
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