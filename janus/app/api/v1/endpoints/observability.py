import csv
import json
from io import StringIO
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.exception_handlers import get_error_taxonomy_catalog
from app.services.observability_service import ObservabilityService, get_observability_service

router = APIRouter(tags=["Observability"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---


class ReleaseQuarantineRequest(BaseModel):
    message_id: str
    allow_retry: bool = False


# --- Endpoints ---


@router.get("/health/system", summary="Retorna a saúde agregada do sistema")
async def get_system_health(service: ObservabilityService = Depends(get_observability_service)):
    """Delega a busca da saúde do sistema para o ObservabilityService."""
    # ObservabilityServiceError é tratado pelo exception handler central -> 500
    return await service.get_system_health()


@router.post("/health/check-all", summary="Força a execução de todos os health checks")
async def check_all_components(service: ObservabilityService = Depends(get_observability_service)):
    """Delega a execução de todos os health checks para o ObservabilityService."""
    return await service.check_all_components()


@router.get("/health/components/llm_manager", summary="Health do componente LLM Manager")
async def health_llm_manager(service: ObservabilityService = Depends(get_observability_service)):
    return await service.get_llm_manager_health()


@router.get(
    "/health/components/multi_agent_system", summary="Health do componente Multi-Agent System"
)
async def health_multi_agent(service: ObservabilityService = Depends(get_observability_service)):
    return await service.get_multi_agent_system_health()


@router.get(
    "/health/components/poison_pill_handler", summary="Health do componente Poison Pill Handler"
)
async def health_poison_pill_handler(
    service: ObservabilityService = Depends(get_observability_service),
):
    return await service.get_poison_pill_handler_health()


@router.get("/poison-pills/quarantined", summary="Retorna mensagens em quarentena")
async def get_quarantined_messages(
    service: ObservabilityService = Depends(get_observability_service), queue: str | None = None
):
    """Delega a busca de mensagens em quarentena para o ObservabilityService."""
    messages = service.get_quarantined_messages(queue=queue)
    return {
        "total_quarantined": len(messages),
        "messages": [
            {
                "message_id": msg.message_id,
                "queue": msg.queue,
                "reason": msg.reason,
                "failure_count": msg.failure_record.failure_count,
                "quarantined_at": msg.quarantined_at.isoformat(),
            }
            for msg in messages
        ],
    }


@router.post("/poison-pills/release", summary="Libera uma mensagem da quarentena")
async def release_from_quarantine(
    request: ReleaseQuarantineRequest,
    service: ObservabilityService = Depends(get_observability_service),
):
    """Delega a liberação de uma mensagem para o ObservabilityService."""
    # MessageNotFoundError é tratado pelo exception handler central -> 404
    msg = service.release_from_quarantine(request.message_id, request.allow_retry)
    return {"message": "Mensagem liberada com sucesso", "message_id": msg.message_id}


@router.post("/poison-pills/cleanup", summary="Limpa mensagens expiradas da quarentena")
async def cleanup_quarantine(service: ObservabilityService = Depends(get_observability_service)):
    return service.cleanup_expired_quarantine()


@router.get("/poison-pills/stats", summary="Retorna estatísticas de poison pills")
async def get_poison_pill_stats(
    service: ObservabilityService = Depends(get_observability_service), queue: str | None = None
):
    """Delega a busca de estatísticas de poison pills para o ObservabilityService."""
    return service.get_poison_pill_stats(queue=queue)


@router.get("/metrics/summary", summary="Retorna um resumo de métricas chave do sistema")
async def get_metrics_summary(service: ObservabilityService = Depends(get_observability_service)):
    """Delega a geração do resumo de métricas para o ObservabilityService."""
    return service.get_metrics_summary()


@router.get("/llm/usage", summary="Resumo de uso de LLMs")
async def llm_usage(
    start_ts: float | None = None,
    end_ts: float | None = None,
    service: ObservabilityService = Depends(get_observability_service),
):
    return service.get_llm_usage_summary(start_ts, end_ts)


@router.get("/graph/audit", summary="Auditoria de higiene do grafo de conhecimento")
async def graph_audit(service: ObservabilityService = Depends(get_observability_service)):
    """Executa consultas de auditoria no grafo e retorna um relatório resumido."""
    return await service.get_graph_audit_report()


@router.get("/graph/quarantine", summary="Lista itens de quarentena do grafo")
async def graph_quarantine_list(
    limit: int = 100, service: ObservabilityService = Depends(get_observability_service)
):
    return await service.get_graph_quarantine_items(limit)


class PromoteQuarantineRequest(BaseModel):
    node_id: int


@router.post(
    "/graph/quarantine/promote", summary="Promove item de quarentena para relação no grafo"
)
async def graph_quarantine_promote(
    request: PromoteQuarantineRequest,
    service: ObservabilityService = Depends(get_observability_service),
):
    return await service.promote_quarantine_item(request.node_id)


class UserSummaryResponse(BaseModel):
    user_id: str
    conversations_count: int
    last_conversation_updated_at: float | None
    vector_points_count: int | None


@router.get(
    "/user_summary", response_model=UserSummaryResponse, summary="Resumo de uso por usuário"
)
async def user_summary(user_id: str, request: Request):
    chat_repo = request.app.state.chat_repo
    items = chat_repo.list_conversations(user_id=user_id, project_id=None, limit=1000)
    conversations_count = len(items)
    last_updated = None
    for it in items:
        ts = it.get("updated_at")
        if ts is None:
            continue
        last_updated = (
            ts if last_updated is None or float(ts) > float(last_updated) else last_updated
        )
    try:
        from app.db.vector_store import aget_collection_info

        info = await aget_collection_info(f"user_{user_id}")
        points = int(info.get("points_count") or 0)
    except Exception:
        points = None
    return UserSummaryResponse(
        user_id=user_id,
        conversations_count=conversations_count,
        last_conversation_updated_at=last_updated,
        vector_points_count=points,
    )


class UserMetricsResponse(BaseModel):
    user_id: str
    conversations: int
    messages: int
    approx_in_tokens: int
    approx_out_tokens: int
    vector_points: int


def _normalize_export_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def _filter_event_fields(event: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    if not fields:
        return event
    return {field: event.get(field) for field in fields}


@router.get("/audit/events", summary="Lista eventos de auditoria")
async def audit_events(
    user_id: str | None = None,
    tool: str | None = None,
    status: str | None = None,
    start_ts: float | None = None,
    end_ts: float | None = None,
    limit: int = 100,
    offset: int = 0,
    service: ObservabilityService = Depends(get_observability_service),
):
    events = service.get_audit_events(user_id, tool, status, start_ts, end_ts, limit, offset)
    total = service.get_audit_events_count(user_id, tool, status, start_ts, end_ts)
    return {"total": total, "events": events}


@router.get("/errors/taxonomy", summary="Catalogo padronizado de erros")
async def error_taxonomy():
    return {"items": get_error_taxonomy_catalog()}


@router.get(
    "/requests/{request_id}/dashboard",
    summary="Dashboard de pipeline por request_id",
)
async def request_pipeline_dashboard(
    request_id: str,
    limit: int = 2000,
    include_details: bool = False,
    service: ObservabilityService = Depends(get_observability_service),
):
    return service.get_request_pipeline_dashboard(
        request_id=request_id,
        limit=limit,
        include_details=include_details,
    )


@router.get("/audit/export", summary="Exporta eventos de auditoria")
async def export_audit_events(
    format: str = "csv",
    fields: str | None = None,
    user_id: str | None = None,
    tool: str | None = None,
    status: str | None = None,
    start_ts: float | None = None,
    end_ts: float | None = None,
    limit: int = 1000,
    offset: int = 0,
    service: ObservabilityService = Depends(get_observability_service),
):
    events = service.get_audit_events(user_id, tool, status, start_ts, end_ts, limit, offset)
    field_list = [f.strip() for f in fields.split(",")] if fields else []
    field_list = [f for f in field_list if f]
    if not field_list:
        field_list = [
            "id",
            "user_id",
            "endpoint",
            "action",
            "tool",
            "status",
            "latency_ms",
            "trace_id",
            "justification",
            "details_json",
            "created_at",
        ]

    rows = [_filter_event_fields(ev, field_list) for ev in events]

    if format.lower() == "json":
        payload = json.dumps(rows, ensure_ascii=True)
        return Response(content=payload, media_type="application/json")

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=field_list, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        normalized = {k: _normalize_export_value(v) for k, v in row.items()}
        writer.writerow(normalized)
    return Response(content=output.getvalue(), media_type="text/csv")


@router.get(
    "/metrics/user", response_model=UserMetricsResponse, summary="Métricas agregadas por usuário"
)
async def user_metrics(
    user_id: str, service: ObservabilityService = Depends(get_observability_service)
):
    m = await service.get_user_metrics(user_id)
    return UserMetricsResponse(**m)


class UserActivityResponse(BaseModel):
    user_id: str
    autonomy_runs: int
    autonomy_steps: int
    avg_step_duration_seconds: float


@router.get(
    "/activity/user", response_model=UserActivityResponse, summary="Atividade agregada por usuário"
)
async def user_activity(
    user_id: str, service: ObservabilityService = Depends(get_observability_service)
):
    a = service.get_user_activity(user_id)
    return UserActivityResponse(**a)


class UxMetricItem(BaseModel):
    ttft_ms: float | None = None
    latency_ms: float | None = None
    outcome: str
    retries: int | None = None
    provider: str | None = None
    model: str | None = None
    timestamp: float


@router.post("/metrics/ux", summary="Registra métrica de UX de chat")
async def record_ux_metric(
    item: UxMetricItem, service: ObservabilityService = Depends(get_observability_service)
):
    """Registra uma métrica de UX para análise de desempenho do chat."""
    # Por enquanto, apenas loga a métrica. Em produção, poderia ser armazenada em banco de dados
    logger.info(
        "ux_metric_recorded",
        ttft_ms=item.ttft_ms,
        latency_ms=item.latency_ms,
        outcome=item.outcome,
        retries=item.retries,
        provider=item.provider,
        model=item.model,
        timestamp=item.timestamp,
    )
    return {"status": "recorded"}
