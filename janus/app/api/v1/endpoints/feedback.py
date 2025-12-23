"""
Feedback API Endpoints - Quick Win para coleta de feedback do usuário.

Endpoints para registrar feedback (👍/👎) e consultar métricas de satisfação.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

from app.services.feedback_service import (
    get_feedback_service,
    FeedbackRating,
    FeedbackType,
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


# --- Schemas ---

class FeedbackRatingEnum(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class FeedbackTypeEnum(str, Enum):
    message = "message"
    conversation = "conversation"
    tool = "tool"
    suggestion = "suggestion"


class FeedbackRequest(BaseModel):
    """Request para registrar feedback."""
    conversation_id: str = Field(..., description="ID da conversa")
    message_id: Optional[str] = Field(None, description="ID da mensagem (opcional)")
    rating: FeedbackRatingEnum = Field(..., description="Rating: positive, negative, ou neutral")
    feedback_type: FeedbackTypeEnum = Field(
        default=FeedbackTypeEnum.message,
        description="Tipo do feedback"
    )
    comment: Optional[str] = Field(None, description="Comentário adicional", max_length=1000)
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")


class QuickFeedbackRequest(BaseModel):
    """Request simplificada para thumbs up/down."""
    conversation_id: str = Field(..., description="ID da conversa")
    message_id: str = Field(..., description="ID da mensagem")
    comment: Optional[str] = Field(None, description="Comentário (opcional)", max_length=500)


class FeedbackResponse(BaseModel):
    """Response após registrar feedback."""
    id: str
    rating: str
    message: str


class SatisfactionReportResponse(BaseModel):
    """Response com relatório de satisfação."""
    total_feedbacks: int
    positive_count: int
    negative_count: int
    neutral_count: int
    satisfaction_rate: float
    nps_score: Optional[int]
    period_start: str
    period_end: str
    top_issues: List[str]


class FeedbackStatsResponse(BaseModel):
    """Response com estatísticas rápidas."""
    total_feedbacks: int
    positive: Optional[int]
    negative: Optional[int]
    satisfaction_rate: Optional[float]
    status: str


# --- Endpoints ---

@router.post("/", response_model=FeedbackResponse)
async def record_feedback(request: FeedbackRequest, user_id: Optional[str] = Query(None)):
    """
    Registra feedback do usuário sobre uma mensagem ou conversa.
    
    - **conversation_id**: ID da conversa
    - **message_id**: ID da mensagem específica (opcional)
    - **rating**: positive (👍), negative (👎), ou neutral (😐)
    - **feedback_type**: message, conversation, tool, ou suggestion
    - **comment**: Comentário adicional
    """
    try:
        service = get_feedback_service()
        
        feedback = await service.record_feedback(
            conversation_id=request.conversation_id,
            message_id=request.message_id,
            user_id=user_id,
            rating=FeedbackRating(request.rating.value),
            feedback_type=FeedbackType(request.feedback_type.value),
            comment=request.comment,
            context=request.context,
        )
        
        return FeedbackResponse(
            id=feedback.id,
            rating=feedback.rating.value,
            message="Obrigado pelo seu feedback! 🙏"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar feedback: {str(e)}")


@router.post("/thumbs-up", response_model=FeedbackResponse)
async def thumbs_up(request: QuickFeedbackRequest, user_id: Optional[str] = Query(None)):
    """
    Registra feedback positivo (👍) para uma mensagem.
    
    Atalho rápido para feedback positivo sem precisar especificar
    todos os campos.
    """
    try:
        service = get_feedback_service()
        
        feedback = await service.record_thumbs_up(
            conversation_id=request.conversation_id,
            message_id=request.message_id,
            user_id=user_id,
            comment=request.comment,
        )
        
        return FeedbackResponse(
            id=feedback.id,
            rating="positive",
            message="Fico feliz que tenha gostado! 👍"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar feedback: {str(e)}")


@router.post("/thumbs-down", response_model=FeedbackResponse)
async def thumbs_down(request: QuickFeedbackRequest, user_id: Optional[str] = Query(None)):
    """
    Registra feedback negativo (👎) para uma mensagem.
    
    Atalho rápido para feedback negativo. Considere adicionar um
    comentário para ajudar a melhorar as respostas.
    """
    try:
        service = get_feedback_service()
        
        feedback = await service.record_thumbs_down(
            conversation_id=request.conversation_id,
            message_id=request.message_id,
            user_id=user_id,
            comment=request.comment,
        )
        
        return FeedbackResponse(
            id=feedback.id,
            rating="negative",
            message="Agradeço o feedback! Vou me esforçar para melhorar. 🙏"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar feedback: {str(e)}")


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats():
    """
    Retorna estatísticas rápidas de feedback.
    
    Útil para dashboards e monitoramento em tempo real.
    """
    try:
        service = get_feedback_service()
        stats = service.get_stats()
        
        return FeedbackStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


@router.get("/report", response_model=SatisfactionReportResponse)
async def get_satisfaction_report(
    user_id: Optional[str] = Query(None, description="Filtrar por usuário"),
    hours: int = Query(24, description="Janela de tempo em horas", ge=1, le=720),
):
    """
    Gera relatório detalhado de satisfação.
    
    - **user_id**: Filtrar por usuário específico (opcional)
    - **hours**: Janela de tempo para análise (1-720 horas)
    
    O relatório inclui:
    - Contagem de feedbacks por tipo
    - Taxa de satisfação
    - NPS Score (se houver dados suficientes)
    - Top issues reportados
    """
    try:
        service = get_feedback_service()
        report = await service.get_satisfaction_report(user_id=user_id, hours=hours)
        
        return SatisfactionReportResponse(**report.to_dict())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")


@router.get("/suggestions")
async def get_improvement_suggestions():
    """
    Retorna sugestões de melhoria baseadas em feedbacks negativos.
    
    Usado pelo Meta-Agent para identificar padrões de insatisfação
    e propor otimizações.
    """
    try:
        service = get_feedback_service()
        suggestions = await service.get_improvement_suggestions()
        
        return {
            "suggestions": suggestions,
            "count": len(suggestions),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter sugestões: {str(e)}")


@router.get("/conversation/{conversation_id}")
async def get_conversation_feedback(conversation_id: str):
    """
    Retorna todos os feedbacks de uma conversa específica.
    
    - **conversation_id**: ID da conversa
    """
    try:
        service = get_feedback_service()
        feedbacks = await service.get_feedback_by_conversation(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "feedbacks": [f.to_dict() for f in feedbacks],
            "count": len(feedbacks),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter feedbacks: {str(e)}")
