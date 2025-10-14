from typing import Optional

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
import structlog

from app.services.context_service import ContextService, get_context_service
from app.core.infrastructure.context_manager import ContextInfo, WebSearchResult

router = APIRouter(tags=["Context"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---

class EnrichedContextRequest(BaseModel):
    query: Optional[str] = None
    include_web_search: bool = False
    max_web_results: int = 3

# --- Endpoints ---

@router.get("/current", response_model=ContextInfo, summary="Obtém contexto ambiental atual")
async def get_current_context(service: ContextService = Depends(get_context_service)):
    """Delega a busca do contexto ambiental atual para o ContextService."""
    # ContextServiceError é tratado pelo exception handler central -> 500
    return service.get_current_context()


@router.get("/web-search", response_model=WebSearchResult, summary="Busca informações na web")
async def search_web(
        query: str = Query(..., description="Query de busca"),
        max_results: int = Query(5, ge=1, le=10, description="Número máximo de resultados"),
        search_depth: str = Query("basic", regex="^(basic|advanced)$", description="Profundidade da busca"),
        service: ContextService = Depends(get_context_service)
):
    """Delega a busca na web para o ContextService."""
    return service.perform_web_search(
        query=query,
        max_results=max_results,
        search_depth=search_depth
    )


@router.post("/enriched", summary="Obtém contexto enriquecido")
async def get_enriched_context(
        request: EnrichedContextRequest,
        service: ContextService = Depends(get_context_service)
):
    """Delega a busca por contexto enriquecido para o ContextService."""
    return service.get_enriched_context(
        query=request.query,
        include_web_search=request.include_web_search,
        max_web_results=request.max_web_results
    )


@router.get("/format-prompt", summary="Formata contexto para prompt")
async def format_context_for_prompt(
        include_datetime: bool = Query(True, description="Incluir data/hora"),
        include_system: bool = Query(False, description="Incluir informações do sistema"),
        web_query: Optional[str] = Query(None, description="Query opcional para busca web"),
        service: ContextService = Depends(get_context_service)
):
    """Delega a formatação de contexto para o ContextService."""
    formatted_context = service.get_formatted_context_for_prompt(
        include_datetime=include_datetime,
        include_system=include_system,
        web_query=web_query
    )
    return {"formatted_context": formatted_context}
