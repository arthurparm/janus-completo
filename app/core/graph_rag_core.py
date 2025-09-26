import logging
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph

from app.config import settings
from app.core.llm_manager import get_llm, ModelRole
from app.core.prompt_loader import get_prompt

logger = logging.getLogger(__name__)

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
    if graph is None: return ""
    try:
        schema_val = graph.get_schema if callable(getattr(graph, "get_schema", None)) else getattr(graph, "schema", "")
        return f"{schema_val}\n(:Function)-[:CALLS]->(:Function)"
    except Exception as e:
        logger.warning(f"Graph RAG Core: Não foi possível obter o schema do grafo: {e}")
        return "(:Function)-[:CALLS]->(:Function)"


def _extract_cypher(text: str) -> str:
    """
    Extrai a consulta Cypher da resposta do LLM de forma robusta e agnóstica ao modelo.
    """
    cypher_match = re.search(r"```(?:cypher)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if cypher_match:
        return cypher_match.group(1).strip()

    lines = text.splitlines()
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line.upper().startswith("MATCH") or cleaned_line.upper().startswith("MERGE"):
            # Assume que esta é a consulta e retorna-a
            return cleaned_line

    logger.warning(f"Não foi possível extrair uma consulta Cypher da resposta: {text}")
    return ""


def query_knowledge_graph(question: str) -> str:
    """
    Função de alto nível que executa o fluxo de RAG completo sobre o grafo.
    """
    if graph is None:
        raise ConnectionError("Graph RAG Core não está disponível.")

    # Usa o modelo Curador para tarefas de RAG, que é mais otimizado para isto.
    llm = get_llm(role=ModelRole.KNOWLEDGE_CURATOR)

    cypher_chain = cypher_prompt | llm | StrOutputParser()
    qa_chain = qa_prompt | llm | StrOutputParser()

    full_schema = _get_full_schema_text()

    llm_response_cypher = cypher_chain.invoke({"schema": full_schema, "question": question})

    cypher_query = _extract_cypher(llm_response_cypher)

    if not cypher_query or cypher_query.startswith("//"):
        return "Não foi possível gerar uma consulta Cypher válida para esta pergunta."

    logger.info(f"Executando consulta Cypher gerada: {cypher_query}")
    try:
        graph_result = graph.query(cypher_query)
        if not graph_result:
            return "A consulta ao grafo foi executada com sucesso, mas não retornou resultados."
    except Exception as e:
        logger.error(f"Erro ao executar a consulta Cypher: {e}", exc_info=True)
        return f"Ocorreu um erro ao consultar o grafo: {e}"

    llm_response_qa = qa_chain.invoke({"context": str(graph_result), "question": question})

    return llm_response_qa.strip()
