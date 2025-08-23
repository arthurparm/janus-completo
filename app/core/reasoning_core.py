# app/core/reasoning_core.py
import logging
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.agents import create_openai_tools_agent, AgentExecutor
from app.config import settings
# Importa a lista de ferramentas que definimos
from app.core.agent_tools import file_system_tools

logger = logging.getLogger(__name__)

# NOTA: Removemos a lógica de QA do grafo por enquanto para focar na execução de ferramentas.
# Iremos reintegrá-la como uma ferramenta na próxima sprint.

def run_agent_executor(question: str) -> dict:
    """
    Cria e executa um agente ReAct com acesso a ferramentas do sistema de arquivos.
    """
    try:
        logger.info(f"Recebida a instrução para o agente: '{question}'")
        
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0,
            api_key=settings.OPENAI_API_KEY.get_secret_value()
        )

        # O prompt do ReAct define como o agente deve raciocinar e usar ferramentas.
        # Usamos um prompt testado e aprovado do LangChain Hub.
        prompt = hub.pull("hwchase17/openai-tools-agent")

        # Agrupamos as ferramentas que o agente pode usar.
        tools = file_system_tools
        
        # Cria o agente, que é a combinação do LLM, do prompt e das ferramentas.
        agent = create_openai_tools_agent(llm, tools, prompt)
        
        # O AgentExecutor é o que de fato executa o loop de Raciocínio-Ação.
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        logger.info("Invocando o AgentExecutor...")
        result = agent_executor.invoke({"input": question})
        
        logger.info("AgentExecutor concluiu a execução.")
        
        return {
            "answer": result.get("output", "A tarefa foi concluída, mas não houve uma resposta final explícita."),
            "intermediate_steps": result.get("intermediate_steps", [])
        }

    except Exception as e:
        logger.error(f"Erro ao executar o agente: {e}", exc_info=True)
        return {"error": "Ocorreu um erro durante a execução do agente."}