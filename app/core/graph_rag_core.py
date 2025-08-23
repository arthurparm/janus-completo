# app/core/graph_rag_core.py
import logging
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.prompt_loader import get_prompt

logger = logging.getLogger(__name__)

# Inicializa o grafo (opcionalmente desativado se houver falhas de configuração)
try:
    graph = Neo4jGraph(
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD.get_secret_value(),
    )
    graph.refresh_schema()
    logger.info("Graph RAG Core: Conexão com Neo4j estabelecida e schema atualizado.")
except Exception as e:
    logger.error(f"Graph RAG Core: Falha ao inicializar Neo4jGraph: {e}", exc_info=True)
    graph = None

try:
    cypher_prompt = PromptTemplate.from_template(get_prompt("cypher_generation"))
    qa_prompt = PromptTemplate.from_template(get_prompt("qa_synthesis"))
except KeyError as e:
    logger.critical(f"Graph RAG Core: FATAL - Falha ao carregar prompts. Erro: {e}")
    graph = None


def _get_full_schema_text() -> str:
    """Obtém o schema completo como texto. Compatível com diferentes versões do LangChain Neo4jGraph."""
    if graph is None:
        return ""
    try:
        # Algumas versões expõem como método, outras como propriedade
        schema_val = graph.get_schema() if callable(getattr(graph, "get_schema", None)) else getattr(graph, "schema", "")
        return f"{schema_val}\n(:Function)-[:CALLS]->(:Function)"
    except Exception as e:
        logger.warning(f"Graph RAG Core: Não foi possível obter o schema do grafo: {e}")
        return "(:Function)-[:CALLS]->(:Function)"


def query_knowledge_graph(question: str) -> str:
    """
    Função de alto nível que executa o fluxo de RAG completo sobre o grafo.
    """
    if graph is None:
        raise ConnectionError("Graph RAG Core não está disponível.")

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL_NAME,
        temperature=0,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )

    cypher_chain = cypher_prompt | llm | StrOutputParser()
    qa_chain = qa_prompt | llm | StrOutputParser()

    full_schema = _get_full_schema_text()

    # Etapa 1: Gerar Cypher
    llm_response_cypher = cypher_chain.invoke({"schema": full_schema, "question": question})

    cypher_match = re.search(r"```(?:cypher)?\s*(.*?)\s*```", llm_response_cypher, re.DOTALL | re.IGNORECASE)
    cypher_query = (
        cypher_match.group(1).strip()
        if cypher_match
        else llm_response_cypher.split("Consulta Cypher:")[-1].strip()
    )

    if not cypher_query or cypher_query.startswith("//"):
        return "Não foi possível gerar uma consulta Cypher válida para esta pergunta."

    # Etapa 2: Executar consulta
    graph_result = graph.query(cypher_query)

    # Etapa 3: Sintetizar resposta
    llm_response_qa = qa_chain.invoke({"context": str(graph_result), "question": question})

    final_answer_match = re.search(r"Resposta Útil:\s*(.*)", llm_response_qa, re.DOTALL | re.IGNORECASE)
    return final_answer_match.group(1).strip() if final_answer_match else llm_response_qa.strip()
