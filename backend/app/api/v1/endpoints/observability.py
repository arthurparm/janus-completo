import csv
import json
from io import StringIO
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.exception_handlers import get_error_taxonomy_catalog
from app.core.security.request_guard import require_admin_actor
from app.services.observability_service import (
    ObservabilityService,
    get_observability_service,
    observe_ux_metric_record,
)

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


@router.get("/health/components/llm_router", summary="Health do componente LLM Router")
async def health_llm_router(service: ObservabilityService = Depends(get_observability_service)):
    return await service.get_llm_router_health()


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


@router.get(
    "/slo/domains",
    summary="SLOs por domÃ­nio (chat/rag/tools/workers) com alertas ativos",
)
async def domain_slo_report(
    window_minutes: int | None = None,
    min_events: int | None = None,
    service: ObservabilityService = Depends(get_observability_service),
):
    logger.info(
        "observability_endpoint_domain_slo_report_requested",
        operation="domain_slo_report",
        window_minutes=window_minutes,
        min_events=min_events,
    )
    result = await service.get_domain_slo_report(window_minutes=window_minutes, min_events=min_events)
    logger.info(
        "observability_endpoint_domain_slo_report_completed",
        operation="domain_slo_report",
        status=result.get("status"),
        domain_count=len(result.get("domains") or []),
        alert_count=len(result.get("active_alerts") or []),
    )
    return result


@router.get(
    "/anomalies/predictive",
    summary="Deteccao preditiva de anomalias (latencia, erro e filas)",
)
async def predictive_anomalies(
    window_hours: int | None = None,
    bucket_minutes: int | None = None,
    min_events: int | None = None,
    service: ObservabilityService = Depends(get_observability_service),
):
    logger.info(
        "observability_endpoint_predictive_anomalies_requested",
        operation="predictive_anomaly_report",
        window_hours=window_hours,
        bucket_minutes=bucket_minutes,
        min_events=min_events,
    )
    result = await service.get_predictive_anomaly_report(
        window_hours=window_hours,
        bucket_minutes=bucket_minutes,
        min_events=min_events,
    )
    logger.info(
        "observability_endpoint_predictive_anomalies_completed",
        operation="predictive_anomaly_report",
        status=result.get("status"),
        anomaly_count=len(result.get("anomalies") or []),
    )
    return result


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
    logger.info("observability_endpoint_graph_audit_requested", operation="graph_audit_report")
    result = await service.get_graph_audit_report()
    logger.info(
        "observability_endpoint_graph_audit_completed",
        operation="graph_audit_report",
        quarantine_count=result.get("quarantine_count"),
        mentions_count=result.get("mentions_count"),
    )
    return result


@router.get("/graph/quarantine", summary="Lista itens de quarentena do grafo")
async def graph_quarantine_list(
    limit: int = 100, service: ObservabilityService = Depends(get_observability_service)
):
    logger.info(
        "observability_endpoint_graph_quarantine_list_requested",
        operation="graph_quarantine_list",
        limit=limit,
    )
    items = await service.get_graph_quarantine_items(limit)
    logger.info(
        "observability_endpoint_graph_quarantine_list_completed",
        operation="graph_quarantine_list",
        limit=limit,
        row_count=len(items),
    )
    return items


class PromoteQuarantineRequest(BaseModel):
    node_id: int


@router.post(
    "/graph/quarantine/promote", summary="Promove item de quarentena para relação no grafo"
)
async def graph_quarantine_promote(
    request: PromoteQuarantineRequest,
    service: ObservabilityService = Depends(get_observability_service),
):
    logger.info(
        "observability_endpoint_graph_quarantine_promote_requested",
        operation="graph_quarantine_promote",
        node_id=request.node_id,
    )
    result = await service.promote_quarantine_item(request.node_id)
    logger.info(
        "observability_endpoint_graph_quarantine_promote_completed",
        operation="graph_quarantine_promote",
        node_id=request.node_id,
        status=result.get("status"),
    )
    return result


class UserSummaryResponse(BaseModel):
    conversations_count: int
    last_conversation_updated_at: float | None
    vector_points_count: int | None


@router.get(
    "/user_summary", response_model=UserSummaryResponse, summary="Resumo de uso por usuário"
)
async def user_summary(request: Request, user_id: str | None = None):
    if user_id is None:
        user_id = getattr(request.state, "actor_user_id", "default_user")
    chat_repo = getattr(request.app.state, "chat_repo", None)
    items = []
    if chat_repo is not None:
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
        from app.db.vector_store import aget_total_points, get_user_collection_names

        points = await aget_total_points(list(get_user_collection_names(user_id).values()))
    except Exception:
        points = None
    return UserSummaryResponse(
        user_id=user_id,
        conversations_count=conversations_count,
        last_conversation_updated_at=last_updated,
        vector_points_count=points,
    )


class UserMetricsResponse(BaseModel):
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
    logger.info(
        "observability_endpoint_audit_events_requested",
        operation="audit_events_query",
        user_id=user_id,
        tool=tool,
        status=status,
        limit=limit,
        offset=offset,
    )
    events = service.get_audit_events(user_id, tool, status, start_ts, end_ts, limit=limit, offset=offset)
    total = service.get_audit_events_count(user_id, tool, status, start_ts, end_ts)
    logger.info(
        "observability_endpoint_audit_events_completed",
        operation="audit_events_query",
        total=total,
        row_count=len(events),
    )
    return {"total": total, "events": events}


@router.get(
    "/pending-actions/legacy-residue",
    summary="Resumo administrativo do resíduo legado bloqueado de pending_actions",
)
async def pending_actions_legacy_residue(
    request: Request,
    limit: int = 20,
    service: ObservabilityService = Depends(get_observability_service),
):
    require_admin_actor(request)
    safe_limit = max(1, int(limit))
    logger.info(
        "observability_endpoint_pending_actions_legacy_residue_requested",
        operation="pending_actions_legacy_residue",
        limit=safe_limit,
    )
    result = service.get_pending_actions_legacy_residue_summary(limit=safe_limit)
    logger.info(
        "observability_endpoint_pending_actions_legacy_residue_completed",
        operation="pending_actions_legacy_residue",
        limit=safe_limit,
        total_without_owner=result.get("total_without_owner"),
        pending_without_owner=result.get("pending_without_owner"),
        item_count=len(result.get("items") or []),
    )
    return result


@router.get("/audit/ledger/integrity", summary="Verifica integridade do audit ledger (hash-chain + assinatura)")
async def audit_ledger_integrity(
    request: Request,
    max_errors: int = 25,
):
    require_admin_actor(request)
    from app.repositories.audit_ledger_repository import audit_ledger_repository

    return audit_ledger_repository.verify_integrity(max_errors=max(1, int(max_errors)))


class IncidentOpenRequest(BaseModel):
    severity: str
    category: str
    summary: str
    details: dict[str, Any] | None = None


class IncidentEvidenceRequest(BaseModel):
    incident_id: str
    evidence_type: str
    evidence_text: str | None = None
    evidence_uri: str | None = None
    metadata: dict[str, Any] | None = None


class IncidentCloseRequest(BaseModel):
    incident_id: str
    resolution_summary: str
    root_cause: str | None = None
    corrective_actions: list[str] | None = None
    validation_evidence: dict[str, Any] | None = None


def _sha256_hex(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _generate_incident_id() -> str:
    import secrets
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"INC-{stamp}-{secrets.token_hex(4).upper()}"


@router.post("/incidents/open", summary="Abre um incidente e ancora o registro no audit ledger")
async def incident_open(
    payload: IncidentOpenRequest,
    request: Request,
):
    actor = require_admin_actor(request)
    incident_id = _generate_incident_id()

    from app.repositories.observability_repository import record_audit_event_direct

    record_audit_event_direct(
        user_id=int(actor),
        endpoint="incident_response",
        action="incident_opened",
        tool="incident_runbook",
        status="open",
        details_json={
            "incident_id": incident_id,
            "severity": payload.severity,
            "category": payload.category,
            "summary": payload.summary,
            "details": payload.details or {},
        },
    )

    return {"incident_id": incident_id}


@router.post("/incidents/evidence", summary="Anexa evidência imutável ao incidente via audit ledger")
async def incident_add_evidence(
    payload: IncidentEvidenceRequest,
    request: Request,
):
    actor = require_admin_actor(request)
    canonical = json.dumps(
        {
            "incident_id": payload.incident_id,
            "evidence_type": payload.evidence_type,
            "evidence_text": payload.evidence_text,
            "evidence_uri": payload.evidence_uri,
            "metadata": payload.metadata or {},
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    evidence_hash = _sha256_hex(canonical)

    from app.repositories.observability_repository import record_audit_event_direct

    record_audit_event_direct(
        user_id=int(actor),
        endpoint="incident_response",
        action="incident_evidence_added",
        tool="incident_runbook",
        status="evidence",
        details_json={
            "incident_id": payload.incident_id,
            "evidence_type": payload.evidence_type,
            "evidence_hash": evidence_hash,
            "evidence_uri": payload.evidence_uri,
            "evidence_text": payload.evidence_text,
            "metadata": payload.metadata or {},
        },
    )

    return {"incident_id": payload.incident_id, "evidence_hash": evidence_hash}


@router.post("/incidents/close", summary="Encerra o incidente registrando resolução e validações no audit ledger")
async def incident_close(
    payload: IncidentCloseRequest,
    request: Request,
):
    actor = require_admin_actor(request)
    from app.repositories.observability_repository import record_audit_event_direct

    record_audit_event_direct(
        user_id=int(actor),
        endpoint="incident_response",
        action="incident_closed",
        tool="incident_runbook",
        status="resolved",
        details_json={
            "incident_id": payload.incident_id,
            "resolution_summary": payload.resolution_summary,
            "root_cause": payload.root_cause,
            "corrective_actions": payload.corrective_actions or [],
            "validation_evidence": payload.validation_evidence or {},
        },
    )

    return {"incident_id": payload.incident_id, "status": "resolved"}


@router.get("/incidents", summary="Lista incidentes ancorados no audit ledger")
async def list_incidents(
    request: Request,
    limit: int = 100,
    offset: int = 0,
):
    require_admin_actor(request)
    from app.repositories.audit_ledger_repository import audit_ledger_repository

    events = audit_ledger_repository.list_events(
        user_id=None,
        tool="incident_runbook",
        status=None,
        endpoint="incident_response",
        start_ts=None,
        end_ts=None,
        limit=5000,
        offset=0,
    )

    incidents: dict[str, dict[str, Any]] = {}
    for ev in events:
        payload = ev.payload_json or {}
        incident_id = str(payload.get("incident_id") or "")
        if not incident_id:
            continue
        inc = incidents.get(incident_id) or {
            "incident_id": incident_id,
            "severity": None,
            "category": None,
            "summary": None,
            "opened_at": None,
            "closed_at": None,
            "status": None,
            "evidence_count": 0,
        }
        if ev.action == "incident_opened":
            inc["severity"] = payload.get("severity")
            inc["category"] = payload.get("category")
            inc["summary"] = payload.get("summary")
            inc["opened_at"] = (
                ev.created_at.timestamp() if getattr(ev, "created_at", None) else None
            )
            inc["status"] = "open"
        elif ev.action == "incident_evidence_added":
            inc["evidence_count"] = int(inc.get("evidence_count") or 0) + 1
        elif ev.action == "incident_closed":
            inc["closed_at"] = (
                ev.created_at.timestamp() if getattr(ev, "created_at", None) else None
            )
            inc["status"] = "resolved"
        incidents[incident_id] = inc

    ordered = sorted(
        incidents.values(),
        key=lambda x: x.get("opened_at") or 0,
        reverse=True,
    )
    sliced = ordered[int(offset) : int(offset) + int(limit)]
    return {"total": len(ordered), "incidents": sliced}


@router.get("/incidents/{incident_id}/events", summary="Lista eventos (evidências) do incidente no audit ledger")
async def incident_events(
    incident_id: str,
    request: Request,
    limit: int = 2000,
    offset: int = 0,
):
    require_admin_actor(request)
    from app.repositories.audit_ledger_repository import audit_ledger_repository

    rows = audit_ledger_repository.list_events(
        user_id=None,
        tool="incident_runbook",
        status=None,
        endpoint="incident_response",
        start_ts=None,
        end_ts=None,
        limit=5000,
        offset=0,
    )
    filtered = [
        {
            "id": int(r.id),
            "action": r.action,
            "status": r.status,
            "trace_id": r.trace_id,
            "created_at": r.created_at.timestamp() if getattr(r, "created_at", None) else None,
            "details_json": r.payload_json,
            "prev_hash": r.prev_hash,
            "entry_hash": r.entry_hash,
            "signature": r.signature,
        }
        for r in rows
        if str((r.payload_json or {}).get("incident_id") or "") == incident_id
    ]
    filtered.sort(key=lambda x: x.get("created_at") or 0)
    sliced = filtered[int(offset) : int(offset) + int(limit)]
    return {"total": len(filtered), "events": sliced}


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
    logger.info(
        "observability_endpoint_request_pipeline_dashboard_requested",
        operation="request_pipeline_dashboard",
        request_id=request_id,
        limit=limit,
        include_details=include_details,
    )
    result = service.get_request_pipeline_dashboard(
        request_id=request_id,
        limit=limit,
        include_details=include_details,
    )
    logger.info(
        "observability_endpoint_request_pipeline_dashboard_completed",
        operation="request_pipeline_dashboard",
        request_id=request_id,
        found=result.get("found"),
        total_events=((result.get("summary") or {}).get("total_events")),
    )
    return result


@router.get("/audit/export", summary="Exporta eventos de auditoria")
async def export_audit_events(
    user_id: str | None = None,
    format: str = "csv",
    fields: str | None = None,
    tool: str | None = None,
    status: str | None = None,
    start_ts: float | None = None,
    end_ts: float | None = None,
    limit: int = 1000,
    offset: int = 0,
    service: ObservabilityService = Depends(get_observability_service),
):
    logger.info(
        "observability_endpoint_audit_export_requested",
        operation="audit_export",
        format=format,
        user_id=user_id,
        tool=tool,
        status=status,
        limit=limit,
        offset=offset,
    )
    events = service.get_audit_events(user_id, tool, status, start_ts, end_ts, limit=limit, offset=offset)
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
        logger.info(
            "observability_endpoint_audit_export_completed",
            operation="audit_export",
            format="json",
            row_count=len(rows),
            field_count=len(field_list),
        )
        return Response(content=payload, media_type="application/json")

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=field_list, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        normalized = {k: _normalize_export_value(v) for k, v in row.items()}
        writer.writerow(normalized)
    logger.info(
        "observability_endpoint_audit_export_completed",
        operation="audit_export",
        format="csv",
        row_count=len(rows),
        field_count=len(field_list),
    )
    return Response(content=output.getvalue(), media_type="text/csv")


@router.get(
    "/metrics/user", response_model=UserMetricsResponse, summary="Métricas agregadas por usuário"
)
async def user_metrics(
    user_id: str | None = None,
    service: ObservabilityService = Depends(get_observability_service)
):
    m = await service.get_user_metrics(user_id)
    return UserMetricsResponse(**m)


class UserActivityResponse(BaseModel):
    autonomy_runs: int
    autonomy_steps: int
    avg_step_duration_seconds: float


@router.get(
    "/activity/user", response_model=UserActivityResponse, summary="Atividade agregada por usuário"
)
async def user_activity(
    user_id: str | None = None,
    service: ObservabilityService = Depends(get_observability_service)
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
    observe_ux_metric_record(
        outcome=item.outcome,
        provider=item.provider,
        ttft_ms=item.ttft_ms,
        latency_ms=item.latency_ms,
    )
    logger.info(
        "observability_endpoint_ux_metric_recorded",
        operation="ux_metric_record",
        ttft_ms=item.ttft_ms,
        latency_ms=item.latency_ms,
        outcome=item.outcome,
        retries=item.retries,
        provider=item.provider,
        model=item.model,
        timestamp=item.timestamp,
    )
    return {"status": "recorded"}
