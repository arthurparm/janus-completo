import logging
from typing import List

from langsmith import traceable
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import (
    OpenAIEmbeddings,  # Assuming we use OpenAI or similar compatible interface
)
from neo4j_graphrag.retrievers import HybridRetriever
from neo4j_graphrag.types import RetrieverResultItem

from app.config import settings
from app.core.infrastructure.prompt_fallback import get_formatted_prompt
from app.core.llm.llm_manager import ModelRole, get_llm

logger = logging.getLogger(__name__)

# Compat: algumas versões usam .index_name e a classe tem __slots__=().
# Criamos uma property que devolve vector_index_name e aceita setter sem quebrar __slots__.
try:  # pragma: no cover

    def _get_index_name(self):
        try:
            return getattr(self, "vector_index_name", None)
        except Exception:
            return None

    def _set_index_name(self, value):
        try:
            object.__setattr__(self, "vector_index_name", value)
        except Exception:
            pass

    HybridRetriever.index_name = property(_get_index_name, _set_index_name)  # type: ignore[attr-defined]
except Exception:
    pass


class HybridRetrieverShim:
    """
    Wrapper de composição para contornar bug de atributo ausente (index_name) no HybridRetriever.
    Expõe .search e .index_name para compatibilidade sem tocar na classe base.
    """

    def __init__(
        self,
        driver,
        vector_index_name: str,
        fulltext_index_name: str,
        embedder=None,
        return_properties=None,
    ):
        self._inner = HybridRetriever(
            driver=driver,
            vector_index_name=vector_index_name,
            fulltext_index_name=fulltext_index_name,
            embedder=embedder,
            return_properties=return_properties,
        )
        self.index_name = vector_index_name

    def search(self, *args, **kwargs):
        return self._inner.search(*args, **kwargs)


# Initialize Driver
try:
    driver = GraphDatabase.driver(
        settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value())
    )
except Exception as e:
    logger.error(f"Failed to initialize Neo4j driver: {e}")
    driver = None


class NativeGraphRAG:
    def __init__(self):
        self.driver = driver
        self.retriever = None
        self._initialize_retriever()

    def _initialize_retriever(self):
        if not self.driver:
            return

        # Initialize Embeddings (Wrapper around existing embedding service or OpenAI)
        # For simplicity, assuming OpenAI config is present or we wrap our own.
        # Here we construct a simple wrapper if needed, or use the library's if available.
        # Let's assume we use the library's OpenAIEmbeddings if key is present.
        try:
            embedder = OpenAIEmbeddings(
                api_key=(
                    settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else ""
                )
            )

            self.retriever = HybridRetrieverShim(
                driver=self.driver,
                vector_index_name="janus_vector_index",
                fulltext_index_name="janus_fulltext_index",
                embedder=embedder,
                return_properties=["name", "description", "content"],
            )
        except Exception as e:
            msg = str(e)
            if "No index with name" in msg:
                logger.info(
                    "GraphRAG retriever disabled (index missing). "
                    "Create janus_vector_index/janus_fulltext_index to enable."
                )
            else:
                logger.warning(f"Could not initialize Native GraphRAG retriever: {e}")
            self.retriever = None

    @traceable(name="GraphRAG.query", run_type="retriever")
    async def query(self, question: str, limit: int = 5) -> str:
        if not self.retriever:
            return "Graph RAG not initialized."

        try:
            # HyDE Integration
            query_text = question
            if getattr(settings, "RAG_HYDE_ENABLED", False):
                try:
                    # Import dynamic to avoid circular dependency (Core -> Services)
                    from app.services.reasoning_rag_service import generate_hypothetical_answer

                    logger.info("Generating HyDE answer for query", question=question)
                    hypothetical = await generate_hypothetical_answer(question)

                    # Use hypothetical answer for retrieval if it differs significantly
                    if hypothetical and hypothetical != question:
                        query_text = hypothetical
                        logger.debug("Using HyDE query", hypothetical=hypothetical)
                except Exception as e:
                    logger.warning(
                        f"HyDE generation failed: {e}, falling back to original question"
                    )

            # neo4j-graphrag retrievers are typically synchronous or have async methods.
            # Checking library convention: typically sync methods in v1.
            # We wrap in standard async execution if needed, or just call if it's fast.
            # Usually retrieval involves network I/O.

            results: List[RetrieverResultItem] = self.retriever.search(
                query_text=query_text, top_k=limit
            )

            # Format results
            formatted = []
            for item in results:
                formatted.append(f"Node: {item.content}")

            context = "\n".join(formatted)

            if not context:
                return "No context found."

            # Synthesis
            # We can use the existing LLM service for synthesis
            llm = await get_llm(role=ModelRole.KNOWLEDGE_CURATOR)
            prompt = await get_formatted_prompt(
                "graph_rag_synthesis",
                is_hyde=query_text != question,
                context=context,
                question=question,
            )
            response = await llm.ainvoke(prompt)

            return str(response.content)

        except Exception as e:
            logger.error(f"Error in Native GraphRAG query: {e}")
            return f"Error retrieving information: {e}"


# Global instance
_native_rag = NativeGraphRAG()


async def query_knowledge_graph(question: str, limit: int = 10) -> str:
    """
    Public API replacement using native neo4j_graphrag
    """
    return await _native_rag.query(question, limit)
