from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
import structlog

from app.services.context_service import context_service, ContextServiceError
from app.core.infrastructure.context_manager import ContextInfo, WebSearchResult

router = APIRouter()
logger = structlog.get_logger(__name__)


# --- Pydantic Models (DTOs) ---

class EnrichedContextRequest(BaseModel):
    query: Optional[str] = None
    include_web_search: bool = False
    max_web_results: int = 3


# --- Endpoints ---

@router.get(
    "/current",
    response_model=ContextInfo,
    summary="Obtém contexto ambiental atual",
    tags=["Context"]
)
async def get_current_context():
    """Delega a busca do contexto ambiental atual para o ContextService."""
    try:
        return context_service.get_current_context()
    except ContextServiceError as e:
        logger.error("Erro no serviço de contexto ao buscar contexto atual", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/web-search",
    response_model=WebSearchResult,
    summary="Busca informações na web",
    tags=["Context"]
)
async def search_web(
        query: str = Query(..., description="Query de busca"),
        max_results: int = Query(5, ge=1, le=10, description="Número máximo de resultados"),
        search_depth: str = Query("basic", regex="^(basic|advanced)$", description="Profundidade da busca")
):
    """Delega a busca na web para o ContextService."""
    try:
        return context_service.perform_web_search(
            query=query,
            max_results=max_results,
            search_depth=search_depth
        )
    except ContextServiceError as e:
        logger.error("Erro no serviço de contexto ao realizar busca na web", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post(
    "/enriched",
    summary="Obtém contexto enriquecido",
    tags=["Context"]
)
async def get_enriched_context(request: EnrichedContextRequest):
    """Delega a busca por contexto enriquecido para o ContextService."""
    try:
        return context_service.get_enriched_context(
            query=request.query,
            include_web_search=request.include_web_search,
            max_web_results=request.max_web_results
        )
    except ContextServiceError as e:
        logger.error("Erro no serviço de contexto ao buscar contexto enriquecido", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/format-prompt",
    summary="Formata contexto para prompt",
    tags=["Context"]
)
async def format_context_for_prompt(
        include_datetime: bool = Query(True, description="Incluir data/hora"),
        include_system: bool = Query(False, description="Incluir informações do sistema"),
        web_query: Optional[str] = Query(None, description="Query opcional para busca web")
):
    """Delega a formatação de contexto para o ContextService."""
    try:
        formatted_context = context_service.get_formatted_context_for_prompt(
            include_datetime=include_datetime,
            include_system=include_system,
            web_query=web_query
        )
        return {"formatted_context": formatted_context}
    except ContextServiceError as e:
        logger.error("Erro no serviço de contexto ao formatar para prompt", exc_info=e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
