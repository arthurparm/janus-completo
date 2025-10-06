import logging
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_neo4j import Neo4jGraph
from prometheus_client import Counter, Histogram

from app.config import settings
from app.core.llm.llm_manager import get_llm, ModelRole
from app.core.memory.memory_core import memory_core
from app.core.infrastructure.prompt_loader import get_prompt

logger = logging.getLogger(__name__)

# Metrics
_RAG_STAGE_LAT = Histogram(
    "rag_stage_latency_seconds", "Latência por estágio do Graph RAG", ["stage", "outcome"]
)
_RAG_EVENTS = Counter(
    "rag_events_total", "Eventos por estágio do Graph RAG", ["stage", "outcome"]
)
_RAG_CACHE = Counter(
    "rag_cache_total", "Cache hits/misses do contexto", ["outcome"]  # hit/miss
)

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


class _ContextCache:
    def __init__(self, max_items: int = 128, ttl_seconds: int = 300):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        value = self._store.get(key)
        if not value:
            _RAG_CACHE.labels("miss").inc()
            return None
        ts, payload = value
        if now - ts > self.ttl_seconds:
            self._store.pop(key, None)
            _RAG_CACHE.labels("miss").inc()
            return None
        self._store.move_to_end(key)
        _RAG_CACHE.labels("hit").inc()
        return payload

    def put(self, key: str, payload: Any) -> None:
        self._store[key] = (time.time(), payload)
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)


_CONTEXT_CACHE = _ContextCache()


class VectorRetriever:
    def retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        t0 = time.perf_counter()
        try:
            res = memory_core.recall(query=query, n_results=k)
            _RAG_EVENTS.labels("vector_retrieval", "success").inc()
            _RAG_STAGE_LAT.labels("vector_retrieval", "success").observe(time.perf_counter() - t0)
            return res or []
        except Exception as e:
            _RAG_EVENTS.labels("vector_retrieval", "error").inc()
            _RAG_STAGE_LAT.labels("vector_retrieval", "error").observe(time.perf_counter() - t0)
            logger.error(f"Graph RAG: erro no VectorRetriever: {e}")
            return []


class GraphRetriever:
    def __init__(self, graph_ref: Optional[Neo4jGraph]):
        self.graph_ref = graph_ref

    def retrieve_with_llm(self, question: str) -> List[Dict[str, Any]]:
        if self.graph_ref is None:
            raise ConnectionError("Graph RAG Core não está disponível.")
        llm = get_llm(role=ModelRole.KNOWLEDGE_CURATOR)
        cypher_chain = cypher_prompt | llm | StrOutputParser()
        t0 = time.perf_counter()
        try:
            full_schema = _get_full_schema_text()
            llm_response_cypher = cypher_chain.invoke({"schema": full_schema, "question": question})
            cypher_query = _extract_cypher(llm_response_cypher)
            if not cypher_query or cypher_query.startswith("//"):
                _RAG_EVENTS.labels("generate_cypher", "empty").inc()
                _RAG_STAGE_LAT.labels("generate_cypher", "empty").observe(time.perf_counter() - t0)
                return []
            _RAG_EVENTS.labels("generate_cypher", "success").inc()
            _RAG_STAGE_LAT.labels("generate_cypher", "success").observe(time.perf_counter() - t0)
        except Exception as e:
            _RAG_EVENTS.labels("generate_cypher", "error").inc()
            _RAG_STAGE_LAT.labels("generate_cypher", "error").observe(time.perf_counter() - t0)
            logger.error(f"Graph RAG: erro na geração de Cypher: {e}", exc_info=True)
            return []

        t1 = time.perf_counter()
        try:
            result = self.graph_ref.query(cypher_query)
            _RAG_EVENTS.labels("graph_query", "success").inc()
            _RAG_STAGE_LAT.labels("graph_query", "success").observe(time.perf_counter() - t1)
            return result or []
        except Exception as e:
            _RAG_EVENTS.labels("graph_query", "error").inc()
            _RAG_STAGE_LAT.labels("graph_query", "error").observe(time.perf_counter() - t1)
            logger.error(f"Erro ao executar a consulta Cypher: {e}", exc_info=True)
            return []


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


def _rerank(graph_ctx: List[Dict[str, Any]], vector_ctx: List[Dict[str, Any]]):
    """Reranker opcional: placeholder que mantém a ordem, com métricas de estágio."""
    t0 = time.perf_counter()
    try:
        # Placeholder: no-op; em ambientes com re-ranker, ordenar por heurística/score.
        _RAG_EVENTS.labels("rerank", "success").inc()
        _RAG_STAGE_LAT.labels("rerank", "success").observe(time.perf_counter() - t0)
        return graph_ctx, vector_ctx
    except Exception:
        _RAG_EVENTS.labels("rerank", "error").inc()
        _RAG_STAGE_LAT.labels("rerank", "error").observe(time.perf_counter() - t0)
        return graph_ctx, vector_ctx


def query_knowledge_graph(question: str) -> str:
    """
    Pipeline Graph RAG com estágios: cache -> (graph_retrieval + opcional vector_retrieval) -> rerank -> síntese -> guardas.
    Mantém a assinatura anterior e retorna resposta em texto.
    """
    if graph is None:
        raise ConnectionError("Graph RAG Core não está disponível.")

    # Modelo para curadoria/síntese
    llm = get_llm(role=ModelRole.KNOWLEDGE_CURATOR)
    qa_chain = qa_prompt | llm | StrOutputParser()

    qkey = question.strip().lower()
    context = _CONTEXT_CACHE.get(qkey)
    graph_ctx: List[Dict[str, Any]] = []
    vector_ctx: List[Dict[str, Any]] = []
    if context is None:
        # Retrieve from graph via LLM-generated Cypher
        graph_ret = GraphRetriever(graph)
        graph_ctx = graph_ret.retrieve_with_llm(question)
        # Optional: additional vector retrieval from episodic memory
        vector_ret = VectorRetriever()
        vector_ctx = vector_ret.retrieve(question, k=5)
        # Simple fusion: keep both; store compact context in cache
        fused_ctx = {
            "graph": graph_ctx,
            "vector": [{"id": v.get("id"), "content": v.get("content", "")} for v in vector_ctx],
        }
        _CONTEXT_CACHE.put(qkey, fused_ctx)
    else:
        graph_ctx = context.get("graph", [])
        vector_ctx = context.get("vector", [])

    # Optional rerank/fusion stage
    graph_ctx, vector_ctx = _rerank(graph_ctx, vector_ctx)

    if not graph_ctx and not vector_ctx:
        return "Não encontrei contexto relevante no grafo ou na memória para responder à pergunta."

    # Prepare context text
    vector_texts = []
    try:
        vector_texts = [str(v.get("content", "")) for v in vector_ctx][:5]
    except Exception:
        vector_texts = []
    context_text = f"Graph: {graph_ctx}\nVector: {vector_texts}" if vector_texts else f"Graph: {graph_ctx}"

    t_synth = time.perf_counter()
    try:
        answer = qa_chain.invoke({"context": context_text, "question": question}).strip()
        _RAG_EVENTS.labels("synthesis", "success").inc()
        _RAG_STAGE_LAT.labels("synthesis", "success").observe(time.perf_counter() - t_synth)
    except Exception as e:
        _RAG_EVENTS.labels("synthesis", "error").inc()
        _RAG_STAGE_LAT.labels("synthesis", "error").observe(time.perf_counter() - t_synth)
        logger.error(f"Erro durante a síntese de resposta: {e}", exc_info=True)
        return f"Ocorreu um erro ao sintetizar a resposta: {e}"

    # Hallucination guard: enforce basic citations presence
    citation_present = bool(re.search(r"\[[0-9]+\]", answer))
    if not citation_present:
        # Compose a lightweight references note
        refs = []
        if graph_ctx:
            refs.append(f"KG:{len(graph_ctx)} nós/linhas")
        if vector_ctx:
            try:
                refs.append("MEM:" + ",".join([str(v.get("id")) for v in vector_ctx[:3]]))
            except Exception:
                refs.append(f"MEM:{len(vector_ctx)} itens")
        if refs:
            answer = f"{answer}\n\n[Referências] {', '.join(refs)}"
        else:
            answer = f"{answer} [AVISO: sem citações]"

    return answer
