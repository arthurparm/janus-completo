"""
Endpoints de Contexto Ambiental - Sprint 3
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.infrastructure import context_manager, ContextInfo, WebSearchResult

router = APIRouter()


class EnrichedContextRequest(BaseModel):
    """Request para contexto enriquecido."""
    query: Optional[str] = None
    include_web_search: bool = False
    max_web_results: int = 3


@router.get(
    "/current",
    response_model=ContextInfo,
    summary="Obtém contexto ambiental atual",
    tags=["Context"]
)
def get_current_context():
    """
    Retorna informações sobre o contexto ambiental atual:
    - Data/hora UTC
    - Informações detalhadas de data e hora
    - Informações do sistema
    - Ambiente de execução
    """
    try:
        return context_manager.get_current_context()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/web-search",
    response_model=WebSearchResult,
    summary="Busca informações na web",
    tags=["Context"]
)
def search_web(
        query: str = Query(..., description="Query de busca"),
        max_results: int = Query(5, ge=1, le=10, description="Número máximo de resultados"),
        search_depth: str = Query("basic", regex="^(basic|advanced)$", description="Profundidade da busca")
):
    """
    Realiza busca na web usando Tavily API.

    - **query**: Texto a ser buscado
    - **max_results**: Quantidade de resultados (1-10)
    - **search_depth**: 'basic' ou 'advanced'
    """
    try:
        return context_manager.search_web(
            query=query,
            max_results=max_results,
            search_depth=search_depth
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/enriched",
    summary="Obtém contexto enriquecido",
    tags=["Context"]
)
def get_enriched_context(request: EnrichedContextRequest):
    """
    Retorna contexto ambiental completo, opcionalmente incluindo busca na web.

    Útil para enriquecer o contexto do agente antes de tomar decisões.
    """
    try:
        return context_manager.get_enriched_context(
            query=request.query,
            include_web_search=request.include_web_search,
            max_web_results=request.max_web_results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format-prompt",
    summary="Formata contexto para prompt",
    tags=["Context"]
)
def format_context_for_prompt(
        include_datetime: bool = Query(True, description="Incluir data/hora"),
        include_system: bool = Query(False, description="Incluir informações do sistema"),
        web_query: Optional[str] = Query(None, description="Query opcional para busca web")
):
    """
    Formata o contexto como string otimizada para inclusão em prompts de LLM.

    Retorna uma string formatada que pode ser diretamente incluída no contexto do agente.
    """
    try:
        web_results = None
        if web_query:
            web_results = context_manager.search_web(web_query, max_results=3)

        formatted = context_manager.format_context_for_prompt(
            include_datetime=include_datetime,
            include_system=include_system,
            web_results=web_results
        )

        return {"formatted_context": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
