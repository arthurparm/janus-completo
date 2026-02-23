"""
Reasoning RAG Service (HyDE & Re-Ranking).

Implements advanced RAG techniques:
1. HyDE (Hypothetical Document Embeddings): Generate a hypothetical answer before search
2. Re-Ranking: Use LLM to re-rank retrieved chunks by relevance
"""

from typing import Any

import structlog

from app.config import settings
from app.core.llm.router import ModelPriority, ModelRole, get_llm
from app.core.infrastructure.prompt_fallback import get_formatted_prompt

logger = structlog.get_logger(__name__)

# HYDE_PROMPT and RERANK_PROMPT are now loaded dynamically


async def generate_hypothetical_answer(question: str) -> str:
    """
    Generate a hypothetical ideal answer for semantic search (HyDE).

    HyDE improves retrieval by searching for the "shape" of an ideal answer
    rather than the question itself.

    Args:
        question: User's question

    Returns:
        Hypothetical answer for embedding
    """
    if not settings.RAG_HYDE_ENABLED:
        return question  # Fall back to original question

    try:
        llm = await get_llm(
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            cache_key="hyde",
        )

        prompt = await get_formatted_prompt("hyde_generation", question=question)
        response = await llm.ainvoke(prompt)
        hypothetical = response.content.strip()

        logger.debug(
            "HyDE generated",
            question=question[:50],
            hypothetical=hypothetical[:100],
        )

        return hypothetical
    except Exception as e:
        logger.warning(f"HyDE generation failed, falling back to question: {e}")
        return question


async def rerank_chunks(
    question: str,
    chunks: list[dict[str, Any]],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Re-rank retrieved chunks using LLM.

    Args:
        question: User's question
        chunks: List of retrieved chunks with 'content' field
        top_k: Number of top results to return

    Returns:
        Re-ranked list of chunks
    """
    if not settings.RAG_RERANK_ENABLED or len(chunks) <= 1:
        return chunks[:top_k] if top_k else chunks

    if top_k is None:
        top_k = settings.RAG_RERANK_TOP_K

    try:
        llm = await get_llm(
            role=ModelRole.ORCHESTRATOR,
            priority=ModelPriority.FAST_AND_CHEAP,
            cache_key="rerank",
        )

        # Format chunks for ranking
        chunks_text = "\n".join(
            [
                f"[{i}] {chunk.get('content', chunk.get('text', ''))[:200]}..."
                for i, chunk in enumerate(chunks)
            ]
        )

        prompt = await get_formatted_prompt("rerank", question=question, chunks=chunks_text)
        response = await llm.ainvoke(prompt)
        ranking_str = response.content.strip()

        # Parse ranking indices
        try:
            indices = [int(x.strip()) for x in ranking_str.split(",") if x.strip().isdigit()]
            # Validate indices
            indices = [i for i in indices if 0 <= i < len(chunks)]

            # Reorder chunks
            reranked = [chunks[i] for i in indices[:top_k]]

            logger.debug(
                "Chunks re-ranked",
                original_count=len(chunks),
                reranked_count=len(reranked),
                ranking=indices[:top_k],
            )

            return reranked
        except Exception as parse_error:
            logger.warning(f"Failed to parse ranking, using original order: {parse_error}")
            return chunks[:top_k]

    except Exception as e:
        logger.warning(f"Re-ranking failed, using original order: {e}")
        return chunks[:top_k]


async def enhanced_rag_search(
    question: str,
    search_fn,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Perform enhanced RAG search with HyDE and Re-Ranking.

    Args:
        question: User's question
        search_fn: Async function that takes a query and returns chunks
        top_k: Number of final results to return

    Returns:
        List of most relevant chunks
    """
    # Step 1: HyDE - generate hypothetical answer
    hyde_query = await generate_hypothetical_answer(question)

    # Step 2: Search with hypothetical answer
    # Request more results for re-ranking
    chunks = await search_fn(hyde_query, limit=top_k * 3)

    # Step 3: Re-rank results
    reranked = await rerank_chunks(question, chunks, top_k=top_k)

    return reranked
