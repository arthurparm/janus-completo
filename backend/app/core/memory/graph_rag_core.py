import logging
import time
from typing import Any, List

from neo4j import GraphDatabase
from langsmith import traceable
from neo4j_graphrag.embeddings import (
    OpenAIEmbeddings,  # Assuming we use OpenAI or similar compatible interface
)
from neo4j_graphrag.retrievers import HybridRetriever
from neo4j_graphrag.types import RetrieverResultItem

from app.config import settings
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.llm.router import get_llm
from app.core.llm.types import ModelRole

logger = logging.getLogger(__name__)

# Initialize Driver
try:
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value())
    )
except Exception as e:
    logger.error(f"Failed to initialize Neo4j driver: {e}")
    driver = None

class GraphRAGCore:
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
                api_key=settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else ""
            )
            
            self.retriever = HybridRetriever(
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
                logger.warning(f"Could not initialize GraphRAG retriever: {e}")
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
                    logger.warning(f"HyDE generation failed: {e}, falling back to original question")

            # neo4j-graphrag retrievers are typically synchronous or have async methods.
            # Checking library convention: typically sync methods in v1.
            # We wrap in standard async execution if needed, or just call if it's fast.
            # Usually retrieval involves network I/O.
            
            results: List[RetrieverResultItem] = self.retriever.search(query_text=query_text, top_k=limit)
            
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
            logger.error(f"Error in GraphRAG query: {e}")
            return f"Error retrieving information: {e}"

# Global instance
_graph_rag_core = GraphRAGCore()

async def query_knowledge_graph(question: str, limit: int = 10) -> str:
    """
    Public API using neo4j_graphrag
    """
    return await _graph_rag_core.query(question, limit)
