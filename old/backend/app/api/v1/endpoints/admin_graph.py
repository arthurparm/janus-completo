import structlog
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy import text
from pydantic import BaseModel

from app.db.postgres_config import get_db_session, postgres_db
from app.core.agents.graph_orchestrator import GRAPH_SCHEMA_VERSION

router = APIRouter(tags=["Admin"], prefix="/admin/graph")
logger = structlog.get_logger(__name__)

class CleanupResult(BaseModel):
    deleted_threads_count: int
    message: str

async def _purge_incompatible_threads_task():
    """
    Background task to find and delete threads incompatible with current schema version.
    In a real implementation, this would deserialize blobs.
    Here we implement a simplified SQL logic assuming we can check metadata or just purge everything for safety if flag is set.
    
    Actually, LangGraph's checkpointer saves 'metadata' column.
    We assume we should have saved 'schema_version' in metadata.
    
    Since we just added schema_version to AgentState, old threads won't have it in the state.
    We can treat any thread without schema_version in the latest snapshot as incompatible.
    """
    # NOTE: Accessing internal langgraph tables
    # checkpoints table usually has: thread_id, checkpoint, metadata
    # The 'checkpoint' column is a msgpack blob of the state.
    # The 'metadata' column is a jsonb/msgpack blob of metadata.
    
    # It is hard to query msgpack blob in SQL.
    # We will iterate threads using LangGraph API if possible, or raw SQL.
    # Since we can't easily iterate via LangGraph API efficiently yet, we use raw SQL to find IDs.
    
    # STRATEGY: 
    # 1. Select all thread_ids.
    # 2. For each, load latest checkpoint.
    # 3. Check 'schema_version'.
    # 4. If mismatch, delete from checkpoints, writes, blobs.
    
    # This is heavy. For MVP, we will assume a "nuclear" option or just log them.
    # Let's implement a 'soft' check: if we can't load it, it's bad.
    
    # Optimized Strategy for MVP:
    # Delete threads where we CANNOT detect schema_version in the state.
    # Since we store state as msgpack, we can't query it easily without pl/python or similar.
    # We will implement a 'dry run' logic here that just logs for now, or deletes if forced.
    
    async with postgres_db.get_session_async() as session:
        # Warning: This is dangerous.
        pass

@router.post("/purge_incompatible", response_model=CleanupResult)
async def purge_incompatible_threads(
    force: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Purges threads that are incompatible with the current graph schema version.
    This is critical after deployments that change the state structure.
    """
    async with postgres_db.get_session_async() as session:
        try:
            check_table = await session.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'checkpoints');")
            )
            table_exists = check_table.scalar()
            if not table_exists:
                return CleanupResult(deleted_threads_count=0, message="Tabela 'checkpoints' não encontrada.")

            count_query = text(
                "SELECT COUNT(DISTINCT thread_id) FROM checkpoints "
                "WHERE metadata->>'schema_version' IS NULL OR metadata->>'schema_version' != :ver"
            )
            res = await session.execute(count_query, {"ver": str(GRAPH_SCHEMA_VERSION)})
            count = res.scalar() or 0

            if not force:
                return CleanupResult(
                    deleted_threads_count=count,
                    message=f"Dry run. Identificadas {count} thread(s) incompatíveis para a versão {GRAPH_SCHEMA_VERSION}. Use force=true para remover."
                )

            if count > 0:
                delete_query = text(
                    "DELETE FROM checkpoints "
                    "WHERE metadata->>'schema_version' IS NULL OR metadata->>'schema_version' != :ver"
                )
                await session.execute(delete_query, {"ver": str(GRAPH_SCHEMA_VERSION)})
                await session.commit()

            return CleanupResult(
                deleted_threads_count=count,
                message=f"Removidas com sucesso {count} thread(s) incompatíveis para a versão {GRAPH_SCHEMA_VERSION}."
            )
        except Exception as e:
            logger.error("Erro ao remover threads incompatíveis", exc_info=e)
            return CleanupResult(deleted_threads_count=0, message=f"Erro durante remoção: {str(e)}")


from app.services.knowledge_graph_service import get_knowledge_graph_service

@router.get("/contextual", summary="Retorna subgrafo contextual para visualização")
async def get_contextual_graph(
    query: str | None = None,
    conversation_id: str | None = None,
    limit: int = 50,
    hops: int = 1
):
    """
    Retorna um subgrafo otimizado para visualização no frontend.
    Pode usar uma 'query' (busca por similaridade ou exata de nós)
    ou 'conversation_id' (busca contexto relevante da conversa).
    """
    service = get_knowledge_graph_service()

    node_names = []
    if query:
        parts = query.replace(",", "").split()
        node_names = [p for p in parts if len(p) > 2]
    
    if conversation_id and not node_names:
        node_names = [conversation_id]

    if not node_names:
        return {"nodes": [], "edges": []}

    return await service.get_subgraph_from_context(node_names, hops=hops)
