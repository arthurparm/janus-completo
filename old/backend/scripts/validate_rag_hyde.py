import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend root to pythonpath
sys.path.append(str(Path(__file__).parent.parent))

# --- MOCKING DEPENDENCIES TO AVOID DB CONNECTION ---
sys.modules["app.db"] = MagicMock()
sys.modules["app.db.postgres_config"] = MagicMock()
sys.modules["app.repositories"] = MagicMock()
sys.modules["app.repositories.prompt_repository"] = MagicMock()
# We also need to mock app.core.infrastructure.prompt_loader which imports prompt_repository
sys.modules["app.core.infrastructure.prompt_loader"] = MagicMock()

# Now we can safely import config
from app.config import settings
# Force enable HyDE for validation
settings.RAG_HYDE_ENABLED = True

# We need to ensure app.core.memory can be imported even if we mock things,
# but graph_rag_core is what we want.
# But "from app.core.memory.graph_rag_core" might trigger app.core.memory.__init__
# We can bypass __init__ by importing the module directly if needed,
# but since we mocked the DB stuff, the imports in __init__ (MemoryCore) might fail
# if MemoryCore imports things we didn't mock properly.
# Let's try to mock MemoryCore too if needed.
# MemoryCore imports Qdrant, etc.

# Let's import directly from the file to be safe, using importlib?
# No, normal import is fine if dependencies are mocked.

from app.core.memory.graph_rag_core import _native_rag
import structlog

# Configure logging to stdout
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

async def main():
    print("=== Validation Script: GraphRAG with HyDE ===")
    
    # 1. Check Config
    print(f"RAG_HYDE_ENABLED: {settings.RAG_HYDE_ENABLED}")
    
    question = "Como o sistema lida com falhas de API do LLM?"
    
    print(f"\nQuestion: {question}")
    
    # 2. Run Query
    # Note: This requires a running Neo4j and LLM access.
    
    try:
        # MOCK RETRIEVER to bypass initialization check and verify HyDE logic
        if not _native_rag.retriever:
             print("\n[INFO] Mocking retriever for validation...")
             _native_rag.retriever = MagicMock()
             # Mock search return
             from neo4j_graphrag.types import RetrieverResultItem
             _native_rag.retriever.search.return_value = [
                 RetrieverResultItem(content="Doc 1 content", metadata={"score": 0.9}),
                 RetrieverResultItem(content="Doc 2 content", metadata={"score": 0.8})
             ]

        # Also need to mock get_llm or ensure it doesn't fail.
        # But generate_hypothetical_answer calls it.
        # Let's mock generate_hypothetical_answer to avoid LLM calls and verify integration
        import app.services.reasoning_rag_service
        
        async def mock_hyde(q):
            print(f"\n[MOCK] Generating HyDE for: {q}")
            return f"Hypothetical Answer for: {q}"
            
        app.services.reasoning_rag_service.generate_hypothetical_answer = mock_hyde
        
        # Mock LLM for final synthesis
        from app.core.llm import router
        mock_llm = MagicMock()
        async def mock_ainvoke(prompt):
            return MagicMock(content="Final Synthesized Answer")
        mock_llm.ainvoke = mock_ainvoke
        
        # We need to patch get_llm to return our mock_llm.
        # Since get_llm is imported in graph_rag_core, patch it in that module.
        # Keep router.get_llm patched too for consistency.
        
        async def mock_get_llm(*args, **kwargs):
            return mock_llm

        router.get_llm = mock_get_llm
        # We need to overwrite the get_llm imported in graph_rag_core
        import app.core.memory.graph_rag_core
        app.core.memory.graph_rag_core.get_llm = mock_get_llm

        print("\n--- Executing GraphRAG Query ---")
        # We expect logs showing "Generating HyDE answer" (or our print from mock)
        answer = await _native_rag.query(question, limit=3)
        print(f"\nFinal Answer:\n{answer}")
        
        # Verify retriever was called with HyDE answer
        args, _ = _native_rag.retriever.search.call_args
        print(f"\nRetriever called with query_text: '{args[0] if args else 'N/A'}'")
        
    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
