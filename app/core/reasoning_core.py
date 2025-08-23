# app/core/reasoning_core.py (Versão Completa e Final com Logs)

import logging
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.prompt_loader import get_prompt

logger = logging.getLogger(__name__)

# --- Bloco de Inicialização (o que estava faltando) ---
# Este código é executado uma vez quando a aplicação inicia.
try:
    # Cria a conexão com o grafo usando as configurações do .env
    graph = Neo4jGraph(
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD.get_secret_value()
    )
    # Pede ao LangChain para inspecionar o schema do banco de dados
    graph.refresh_schema()
    logger.info("LangChain connection to Neo4j established and schema refreshed.")
except Exception as e:
    logger.error(f"Failed to initialize LangChain Neo4jGraph: {e}", exc_info=True)
    graph = None

try:
    # Carrega os templates de prompt do nosso armazém de prompts
    cypher_prompt = PromptTemplate.from_template(get_prompt("cypher_generation"))
    qa_prompt = PromptTemplate.from_template(get_prompt("qa_synthesis"))
    logger.info("Prompt templates loaded successfully.")
except KeyError as e:
    logger.critical(f"FATAL: Could not load essential prompt. Application cannot start. Error: {e}")
    # Se os prompts não puderem ser carregados, definimos o grafo como None para
    # impedir que a aplicação tente usá-lo em um estado inválido.
    graph = None
# --- Fim do Bloco de Inicialização ---


def query_knowledge_graph(question: str) -> dict:
    if graph is None:
        raise ConnectionError("LangChain connection to Neo4j is not available or prompts failed to load.")

    try:
        logger.info(f"--- INÍCIO DO FLUXO DE RAG ---")
        logger.info(f"Pergunta Recebida: '{question}'")

        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            temperature=0,
            api_key=settings.OPENAI_API_KEY.get_secret_value()
        )

        # Usando a sintaxe moderna LangChain Expression Language (LCEL)
        cypher_chain = cypher_prompt | llm | StrOutputParser()
        qa_chain = qa_prompt | llm | StrOutputParser()

        full_schema = f"{graph.get_schema}\n(:Function)-[:CALLS]->(:Function)"

        logger.info(f"\n[ETAPA 1: GERAÇÃO DE CYPHER]\nSchema enviado ao LLM:\n{full_schema}")

        llm_response_cypher = cypher_chain.invoke({
            "schema": full_schema,
            "question": question
        })

        logger.info(f"Saída BRUTA do LLM de Cypher:\n---\n{llm_response_cypher}\n---")

        cypher_match = re.search(r"```(?:cypher)?\s*(.*?)\s*```", llm_response_cypher, re.DOTALL | re.IGNORECASE)
        cypher_query = cypher_match.group(1).strip() if cypher_match else llm_response_cypher.split("Consulta Cypher:")[-1].strip()

        logger.info(f"Consulta Cypher EXTRAÍDA:\n---\n{cypher_query}\n---")

        if not cypher_query or cypher_query.startswith("//"):
            logger.warning("Consulta Cypher inválida ou vazia gerada. Encerrando o fluxo.")
            return {"answer": "Não foi possível gerar uma consulta válida para sua pergunta.", "intermediate_steps": [{"query": cypher_query}]}

        # ETAPA 2: Executar a consulta no grafo
        graph_result = graph.query(cypher_query)
        logger.info(f"Resultado BRUTO do Grafo:\n---\n{graph_result}\n---")

        # ETAPA 3: Sintetizar a resposta final
        llm_response_qa = qa_chain.invoke({
            "context": str(graph_result),
            "question": question
        })

        logger.info(f"Saída BRUTA do LLM de QA:\n---\n{llm_response_qa}\n---")

        final_answer_match = re.search(r"Resposta Útil:\s*(.*)", llm_response_qa, re.DOTALL | re.IGNORECASE)
        final_answer = final_answer_match.group(1).strip() if final_answer_match else llm_response_qa.strip()

        logger.info(f"Resposta Final EXTRAÍDA:\n---\n{final_answer}\n---")

        logger.info("--- FIM DO FLUXO DE RAG ---")

        return {
            "answer": final_answer,
            "intermediate_steps": [{"query": cypher_query}]
        }

    except Exception as e:
        logger.error(f"Error processing question in manual RAG chain: {e}", exc_info=True)
        return {"error": "An error occurred while processing your question."}