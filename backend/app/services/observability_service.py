import json
import time
from collections import Counter
from typing import Any

import structlog
from fastapi import Request
from prometheus_client import Counter as PromCounter
from prometheus_client import Histogram as PromHistogram
from prometheus_client import REGISTRY

from app.config import settings
from app.core.monitoring.poison_pill_handler import QuarantinedMessage
from app.repositories.observability_repository import (
    ObservabilityRepository,
    ObservabilityRepositoryError,
)
from app.services.predictive_anomaly_detection_service import (
    get_predictive_anomaly_detection_service,
)

logger = structlog.get_logger(__name__)


def _get_or_create_counter(name: str, documentation: str, labelnames: list[str]) -> PromCounter:
    try:
        return PromCounter(name, documentation, labelnames)
    except ValueError:
        return REGISTRY._names_to_collectors[name]  # type: ignore[index]


def _get_or_create_histogram(
    name: str,
    documentation: str,
    labelnames: list[str],
    *,
    buckets: tuple[float, ...] | None = None,
) -> PromHistogram:
    try:
        kwargs = {"buckets": buckets} if buckets is not None else {}
        return PromHistogram(name, documentation, labelnames, **kwargs)
    except ValueError:
        return REGISTRY._names_to_collectors[name]  # type: ignore[index]


_OBS_OPERATIONS_TOTAL = _get_or_create_counter(
    "janus_observability_operations_total",
    "Total de operacoes do dominio observability por resultado",
    ["operation", "outcome"],
)
_OBS_OPERATION_DURATION_SECONDS = _get_or_create_histogram(
    "janus_observability_operation_duration_seconds",
    "Latencia das operacoes do dominio observability",
    ["operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
)
_OBS_RESULT_ITEMS = _get_or_create_histogram(
    "janus_observability_result_items",
    "Distribuicao do tamanho de resultados do dominio observability",
    ["operation", "kind"],
)
_OBS_UX_METRICS_TOTAL = _get_or_create_counter(
    "janus_observability_ux_metrics_total",
    "Total de metricas de UX registradas por provider e resultado",
    ["outcome", "provider"],
)
_OBS_UX_LATENCY_SECONDS = _get_or_create_histogram(
    "janus_observability_ux_latency_seconds",
    "Latencias de UX registradas em segundos",
    ["metric", "outcome"],
)

# --- Custom Service-Layer Exceptions ---


class ObservabilityServiceError(Exception):
    """Base exception for observability service errors."""

    pass


class MessageNotFoundError(ObservabilityServiceError):
    """Raised when a message is not found in quarantine."""

    pass


# --- Observability Service ---


class ObservabilityService:
    """
    Camada de serviço para observabilidade, saúde do sistema e resiliência.
    Orquestra a lógica de negócio, delegando o acesso à infraestrutura para o repositório.
    """

    def __init__(self, repo: ObservabilityRepository):
        self._repo = repo

    @staticmethod
    def _observe_operation_start(operation: str, **_attrs: Any) -> float:
        return time.perf_counter()

    @staticmethod
    def _observe_operation_success(operation: str, start_ts: float, **_attrs: Any) -> None:
        _OBS_OPERATIONS_TOTAL.labels(operation=operation, outcome="success").inc()
        elapsed = max(0.0, time.perf_counter() - start_ts)
        _OBS_OPERATION_DURATION_SECONDS.labels(operation=operation).observe(elapsed)

    @staticmethod
    def _observe_operation_failure(
        operation: str, start_ts: float, error: Exception, **_attrs: Any
    ) -> None:
        _ = error
        _OBS_OPERATIONS_TOTAL.labels(operation=operation, outcome="error").inc()
        elapsed = max(0.0, time.perf_counter() - start_ts)
        _OBS_OPERATION_DURATION_SECONDS.labels(operation=operation).observe(elapsed)

    @staticmethod
    def _observe_result_size(operation: str, kind: str, size: int) -> None:
        if size < 0:
            return
        _OBS_RESULT_ITEMS.labels(operation=operation, kind=kind).observe(float(size))

    async def get_system_health(self) -> dict[str, Any]:
        op = "system_health"
        op_start = self._observe_operation_start(op)
        logger.info("observability_system_health_requested", operation="system_health")
        try:
            result = await self._repo.get_system_health()
            self._observe_operation_success(op, op_start)
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_system_health_failed",
                operation="system_health",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> dict[str, dict[str, Any]]:
        op = "check_all_components"
        op_start = self._observe_operation_start(op)
        logger.info("observability_check_all_components_requested", operation="check_all_components")
        try:
            result = await self._repo.check_all_components()
            self._observe_operation_success(op, op_start)
            self._observe_result_size(op, "rows", len(result))
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_check_all_components_failed",
                operation="check_all_components",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao executar os health checks.") from e

    async def get_llm_router_health(self) -> dict[str, Any]:
        op = "llm_router_health"
        op_start = self._observe_operation_start(op)
        logger.info("observability_llm_router_health_requested", operation="llm_router_health")
        try:
            result = await self._repo.get_llm_router_health()
            self._observe_operation_success(op, op_start)
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_llm_router_health_failed",
                operation="llm_router_health",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao buscar saúde do LLM Router.") from e

    async def get_multi_agent_system_health(self) -> dict[str, Any]:
        op = "multi_agent_system_health"
        op_start = self._observe_operation_start(op)
        logger.info(
            "observability_multi_agent_health_requested",
            operation="multi_agent_system_health",
        )
        try:
            result = await self._repo.get_multi_agent_system_health()
            self._observe_operation_success(op, op_start)
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_multi_agent_health_failed",
                operation="multi_agent_system_health",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao buscar saúde do sistema multi-agente.") from e

    async def get_poison_pill_handler_health(self) -> dict[str, Any]:
        op = "poison_pill_handler_health"
        op_start = self._observe_operation_start(op)
        logger.info(
            "observability_poison_pill_health_requested",
            operation="poison_pill_handler_health",
        )
        try:
            result = await self._repo.get_poison_pill_handler_health()
            self._observe_operation_success(op, op_start)
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_poison_pill_health_failed",
                operation="poison_pill_handler_health",
                error=str(e),
            )
            raise ObservabilityServiceError(
                "Falha ao buscar saúde do handler de poison pills."
            ) from e

    def get_quarantined_messages(self, queue: str | None = None) -> list[QuarantinedMessage]:
        logger.info(
            "observability_quarantine_messages_requested",
            operation="quarantine_messages",
            queue=queue,
        )
        return self._repo.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.info(
            "observability_quarantine_release_requested",
            operation="quarantine_release",
            message_id=message_id,
            allow_retry=allow_retry,
        )
        try:
            msg = self._repo.release_from_quarantine(message_id, allow_retry)
            if not msg:
                raise MessageNotFoundError(
                    f"Mensagem com ID '{message_id}' não encontrada na quarentena."
                )
            return msg
        except ObservabilityRepositoryError as e:
            logger.exception(
                "observability_quarantine_release_failed",
                operation="quarantine_release",
                message_id=message_id,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao liberar mensagem da quarentena.") from e

    def cleanup_expired_quarantine(self) -> dict[str, Any]:
        logger.info(
            "observability_quarantine_cleanup_requested",
            operation="quarantine_cleanup",
        )
        try:
            removed = self._repo.cleanup_expired_quarantine()
            return {"removed": removed}
        except ObservabilityRepositoryError as e:
            logger.exception(
                "observability_quarantine_cleanup_failed",
                operation="quarantine_cleanup",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao limpar a quarentena expirada.") from e

    def get_poison_pill_stats(self, queue: str | None = None) -> dict[str, Any]:
        logger.info(
            "observability_poison_pill_stats_requested",
            operation="poison_pill_stats",
            queue=queue,
        )
        return self._repo.get_poison_pill_stats(queue=queue)

    def get_metrics_summary(self) -> dict[str, Any]:
        op = "metrics_summary"
        op_start = self._observe_operation_start(op)
        logger.info("observability_metrics_summary_requested", operation="metrics_summary")
        try:
            result = self._repo.get_metrics_summary()
            self._observe_operation_success(op, op_start)
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_metrics_summary_failed",
                operation="metrics_summary",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao gerar o resumo de métricas.") from e

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        idx = int(round((len(ordered) - 1) * max(0.0, min(1.0, p))))
        idx = max(0, min(len(ordered) - 1, idx))
        return float(ordered[idx])

    @staticmethod
    def _status_is_error(status: Any) -> bool:
        if status is None:
            return False
        text = str(status).strip().lower()
        if not text:
            return False
        if text in {"ok", "success", "passed", "pass", "completed"}:
            return False
        if text in {"error", "failed", "failure", "timeout", "exception", "critical"}:
            return True
        if text.startswith("5") and len(text) >= 3 and text[:3].isdigit():
            return True
        if text in {"5xx", "server_error"}:
            return True
        return False

    @staticmethod
    def _classify_event_domain(event: dict[str, Any]) -> str:
        endpoint = str(event.get("endpoint") or "").strip().lower()
        action = str(event.get("action") or "").strip().lower()

        if "/api/v1/workers" in endpoint or endpoint.startswith("workers"):
            return "workers"
        if "worker" in action:
            return "workers"

        if "/api/v1/rag" in endpoint or endpoint.startswith("rag"):
            return "rag"

        if "/api/v1/chat" in endpoint or endpoint.startswith("chat"):
            return "chat"

        if "/api/v1/tools" in endpoint or endpoint.startswith("tool:"):
            return "tools"
        if "tool_" in action or action.startswith("tool"):
            return "tools"

        return "other"

    @staticmethod
    def _get_domain_slo_thresholds() -> dict[str, dict[str, float]]:
        return {
            "chat": {
                "max_error_rate_pct": float(getattr(settings, "OQ_SLO_CHAT_MAX_ERROR_RATE_PCT", 5.0)),
                "max_p95_latency_ms": float(getattr(settings, "OQ_SLO_CHAT_MAX_P95_LATENCY_MS", 3500.0)),
            },
            "rag": {
                "max_error_rate_pct": float(getattr(settings, "OQ_SLO_RAG_MAX_ERROR_RATE_PCT", 5.0)),
                "max_p95_latency_ms": float(getattr(settings, "OQ_SLO_RAG_MAX_P95_LATENCY_MS", 4500.0)),
            },
            "tools": {
                "max_error_rate_pct": float(getattr(settings, "OQ_SLO_TOOLS_MAX_ERROR_RATE_PCT", 3.0)),
                "max_p95_latency_ms": float(getattr(settings, "OQ_SLO_TOOLS_MAX_P95_LATENCY_MS", 2500.0)),
            },
            "workers": {
                "max_error_rate_pct": float(
                    getattr(settings, "OQ_SLO_WORKERS_MAX_ERROR_RATE_PCT", 3.0)
                ),
                "max_p95_latency_ms": float(
                    getattr(settings, "OQ_SLO_WORKERS_MAX_P95_LATENCY_MS", 4000.0)
                ),
            },
        }

    async def get_domain_slo_report(
        self,
        *,
        window_minutes: int | None = None,
        min_events: int | None = None,
    ) -> dict[str, Any]:
        op = "domain_slo_report"
        op_start = self._observe_operation_start(op)
        now_ts = float(time.time())
        wm = max(1, int(window_minutes or getattr(settings, "OQ_SLO_WINDOW_MINUTES", 15) or 15))
        me = max(
            1,
            int(min_events or getattr(settings, "OQ_SLO_MIN_EVENTS_PER_DOMAIN", 20) or 20),
        )
        logger.info(
            "observability_domain_slo_report_requested",
            operation="domain_slo_report",
            window_minutes=wm,
            min_events=me,
        )
        start_ts = now_ts - (wm * 60.0)
        thresholds = self._get_domain_slo_thresholds()

        try:
            events = self._repo.get_audit_events(
                user_id=None,
                tool=None,
                status=None,
                start_ts=start_ts,
                end_ts=now_ts,
                endpoint=None,
                limit=20000,
                offset=0,
            )
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_domain_slo_events_query_failed",
                operation="domain_slo_report",
                window_minutes=wm,
                min_events=me,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao coletar eventos para SLO por domÃ­nio.") from e

        by_domain: dict[str, list[dict[str, Any]]] = {k: [] for k in thresholds.keys()}
        for ev in events:
            domain = self._classify_event_domain(ev)
            if domain in by_domain:
                by_domain[domain].append(ev)

        domain_reports: list[dict[str, Any]] = []
        active_alerts: list[dict[str, Any]] = []

        for domain, cfg in thresholds.items():
            rows = by_domain.get(domain) or []
            total = len(rows)
            errors = sum(1 for row in rows if self._status_is_error(row.get("status")))
            error_rate_pct = round((errors / total) * 100.0, 2) if total else 0.0
            availability_pct = round(max(0.0, 100.0 - error_rate_pct), 2)

            latencies = [
                lat
                for lat in (self._safe_float(row.get("latency_ms")) for row in rows)
                if lat is not None and lat >= 0.0
            ]
            p95_latency_ms = round(self._percentile(latencies, 0.95), 2) if latencies else 0.0

            breaches: list[dict[str, Any]] = []
            status = "ok"
            if total < me:
                status = "insufficient_data"
            else:
                if error_rate_pct > cfg["max_error_rate_pct"]:
                    breaches.append(
                        {
                            "type": "error_rate",
                            "observed": error_rate_pct,
                            "threshold": cfg["max_error_rate_pct"],
                            "message": (
                                f"Taxa de erro acima do limite: {error_rate_pct:.2f}% > "
                                f"{cfg['max_error_rate_pct']:.2f}%"
                            ),
                        }
                    )
                if p95_latency_ms > cfg["max_p95_latency_ms"]:
                    breaches.append(
                        {
                            "type": "latency_p95_ms",
                            "observed": p95_latency_ms,
                            "threshold": cfg["max_p95_latency_ms"],
                            "message": (
                                f"P95 de latÃªncia acima do limite: {p95_latency_ms:.2f}ms > "
                                f"{cfg['max_p95_latency_ms']:.2f}ms"
                            ),
                        }
                    )
                if breaches:
                    status = "breach"
                    active_alerts.append(
                        {
                            "domain": domain,
                            "severity": "warning",
                            "breaches": breaches,
                        }
                    )

            domain_reports.append(
                {
                    "domain": domain,
                    "status": status,
                    "window": {
                        "start_ts": start_ts,
                        "end_ts": now_ts,
                        "window_minutes": wm,
                    },
                    "sli": {
                        "total_events": total,
                        "error_events": errors,
                        "availability_pct": availability_pct,
                        "error_rate_pct": error_rate_pct,
                        "latency_p95_ms": p95_latency_ms,
                    },
                    "slo": {
                        "max_error_rate_pct": cfg["max_error_rate_pct"],
                        "max_p95_latency_ms": cfg["max_p95_latency_ms"],
                        "min_events": me,
                    },
                    "breaches": breaches,
                }
            )

        if active_alerts:
            overall_status = "degraded"
        elif all(item["status"] == "insufficient_data" for item in domain_reports):
            overall_status = "insufficient_data"
        else:
            overall_status = "ok"

        logger.info(
            "oq002_domain_slo_report_generated",
            status=overall_status,
            window_minutes=wm,
            active_alerts=len(active_alerts),
            domains=len(domain_reports),
            total_events=len(events),
        )
        self._observe_result_size(op, "domains", len(domain_reports))
        self._observe_result_size(op, "alerts", len(active_alerts))
        self._observe_result_size(op, "events", len(events))
        self._observe_operation_success(op, op_start)

        return {
            "status": overall_status,
            "window": {"start_ts": start_ts, "end_ts": now_ts, "window_minutes": wm},
            "domains": domain_reports,
            "active_alerts": active_alerts,
        }

    async def get_predictive_anomaly_report(
        self,
        *,
        window_hours: int | None = None,
        bucket_minutes: int | None = None,
        min_events: int | None = None,
    ) -> dict[str, Any]:
        op = "predictive_anomaly_report"
        op_start = self._observe_operation_start(op)
        if not bool(getattr(settings, "AI_ANOMALY_DETECTION_ENABLED", True)):
            logger.info(
                "observability_predictive_anomaly_report_skipped",
                operation="predictive_anomaly_report",
                reason="feature_flag_disabled",
            )
            self._observe_operation_success(op, op_start)
            return {
                "status": "disabled",
                "risk": {
                    "score": 0,
                    "level": "low",
                    "should_alert": False,
                    "reasons": ["feature_flag_disabled"],
                },
                "anomalies": [],
            }

        now_ts = float(time.time())
        wh = max(1, int(window_hours or getattr(settings, "AI_ANOMALY_WINDOW_HOURS", 6) or 6))
        bm = max(
            1,
            int(bucket_minutes or getattr(settings, "AI_ANOMALY_BUCKET_MINUTES", 10) or 10),
        )
        me = max(5, int(min_events or getattr(settings, "AI_ANOMALY_MIN_EVENTS", 30) or 30))
        logger.info(
            "observability_predictive_anomaly_report_requested",
            operation="predictive_anomaly_report",
            window_hours=wh,
            bucket_minutes=bm,
            min_events=me,
        )
        start_ts = now_ts - (wh * 3600.0)

        try:
            events = self._repo.get_audit_events(
                user_id=None,
                tool=None,
                status=None,
                start_ts=start_ts,
                end_ts=now_ts,
                endpoint=None,
                limit=10000,
                offset=0,
            )
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_predictive_anomaly_events_query_failed",
                operation="predictive_anomaly_report",
                window_hours=wh,
                bucket_minutes=bm,
                min_events=me,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao coletar eventos de auditoria.") from e

        queue_snapshots: list[dict[str, Any]] = []
        try:
            from app.core.infrastructure.message_broker import get_broker

            broker = await get_broker()
            queue_names = list(getattr(settings, "AI_ANOMALY_QUEUE_NAMES", []) or [])
            for queue_name in queue_names:
                try:
                    info = await broker.get_queue_info(str(queue_name))
                    if info:
                        queue_snapshots.append(info)
                except Exception as queue_err:
                    logger.warning(
                        "ai014_queue_info_failed",
                        queue_name=str(queue_name),
                        error=str(queue_err),
                    )
        except Exception as e:
            logger.warning("ai014_broker_unavailable", error=str(e))

        detector = get_predictive_anomaly_detection_service()
        report = detector.analyze(
            events=events,
            queue_snapshots=queue_snapshots,
            start_ts=start_ts,
            end_ts=now_ts,
            bucket_minutes=bm,
            min_events=me,
        )

        logger.info(
            "ai014_predictive_anomaly_report_generated",
            status=report.get("status"),
            risk_level=(report.get("risk") or {}).get("level"),
            risk_score=(report.get("risk") or {}).get("score"),
            anomaly_count=len(report.get("anomalies") or []),
            total_events=((report.get("window") or {}).get("total_events")),
        )
        self._observe_result_size(op, "events", len(events))
        self._observe_result_size(op, "alerts", len(report.get("anomalies") or []))
        self._observe_operation_success(op, op_start)
        return report

    async def get_user_metrics(self, user_id: str) -> dict[str, Any]:
        logger.info(
            "observability_user_metrics_requested",
            operation="user_metrics",
            user_id=user_id,
        )
        try:
            return await self._repo.get_user_metrics(user_id)
        except ObservabilityRepositoryError as e:
            logger.exception(
                "observability_user_metrics_failed",
                operation="user_metrics",
                user_id=user_id,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao gerar métricas por usuário.") from e

    def get_user_activity(self, user_id: str) -> dict[str, Any]:
        logger.info(
            "observability_user_activity_requested",
            operation="user_activity",
            user_id=user_id,
        )
        try:
            return self._repo.get_user_activity(user_id)
        except ObservabilityRepositoryError as e:
            logger.exception(
                "observability_user_activity_failed",
                operation="user_activity",
                user_id=user_id,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao gerar atividade por usuário.") from e

    async def get_graph_audit_report(self) -> dict[str, Any]:
        op = "graph_audit_report"
        op_start = self._observe_operation_start(op)
        logger.info("observability_graph_audit_requested", operation="graph_audit_report")
        try:
            report = await self._repo.get_graph_audit_report()
            self._observe_operation_success(op, op_start)
            logger.info(
                "observability_graph_audit_completed",
                operation="graph_audit_report",
                quarantine_count=report.get("quarantine_count"),
                mentions_count=report.get("mentions_count"),
                relationship_types_present=len(report.get("relationship_types_present") or []),
            )
            return report
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_graph_audit_failed",
                operation="graph_audit_report",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao auditar o grafo.") from e

    async def get_graph_quarantine_items(self, limit: int = 100) -> list[dict[str, Any]]:
        logger.info(
            "observability_graph_quarantine_list_requested",
            operation="graph_quarantine_list",
            limit=limit,
        )
        try:
            items = await self._repo.get_graph_quarantine_items(limit)
            logger.info(
                "observability_graph_quarantine_list_completed",
                operation="graph_quarantine_list",
                limit=limit,
                row_count=len(items),
            )
            return items
        except ObservabilityRepositoryError as e:
            logger.exception(
                "observability_graph_quarantine_list_failed",
                operation="graph_quarantine_list",
                limit=limit,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao listar itens de quarentena.") from e

    async def promote_quarantine_item(self, node_id: int) -> dict[str, Any]:
        logger.info(
            "observability_graph_quarantine_promote_requested",
            operation="graph_quarantine_promote",
            node_id=node_id,
        )
        try:
            result = await self._repo.promote_quarantine_item(node_id)
            logger.info(
                "observability_graph_quarantine_promote_completed",
                operation="graph_quarantine_promote",
                node_id=node_id,
                status=result.get("status"),
            )
            return result
        except ObservabilityRepositoryError as e:
            logger.exception(
                "observability_graph_quarantine_promote_failed",
                operation="graph_quarantine_promote",
                node_id=node_id,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao promover item de quarentena.") from e

    def record_audit_event(self, event: dict[str, Any]) -> None:
        op = "record_audit_event"
        op_start = self._observe_operation_start(op)
        safe_event = {k: v for k, v in event.items() if k not in {"detail", "details_json"}}
        logger.info("observability_audit_event_record_requested", operation="record_audit_event", **safe_event)
        try:
            self._repo.record_audit_event(event)
            self._observe_operation_success(op, op_start)
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_audit_event_record_failed",
                operation="record_audit_event",
                error=str(e),
            )
            # Não propaga como fatal para não quebrar requisições; registra apenas o erro.
            pass

    def get_audit_events(
        self,
        user_id: str | None,
        tool: str | None,
        status: str | None,
        start_ts: float | None,
        end_ts: float | None,
        endpoint: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        op = "audit_events_query"
        op_start = self._observe_operation_start(op)
        logger.info(
            "observability_audit_events_query_requested",
            operation="audit_events_query",
            user_id=user_id,
            tool=tool,
            status=status,
            endpoint=endpoint,
            limit=limit,
            offset=offset,
        )
        try:
            result = self._repo.get_audit_events(
                user_id, tool, status, start_ts, end_ts, endpoint, limit, offset
            )
            self._observe_result_size(op, "events", len(result))
            self._observe_operation_success(op, op_start)
            return result
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_audit_events_query_failed",
                operation="audit_events_query",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao consultar eventos de auditoria.") from e

    def get_audit_events_count(
        self,
        user_id: str | None,
        tool: str | None,
        status: str | None,
        start_ts: float | None,
        end_ts: float | None,
    ) -> int:
        op = "audit_events_count"
        op_start = self._observe_operation_start(op)
        logger.info(
            "observability_audit_events_count_requested",
            operation="audit_events_count",
            user_id=user_id,
            tool=tool,
            status=status,
        )
        try:
            count = self._repo.get_audit_events_count(user_id, tool, status, start_ts, end_ts)
            self._observe_result_size(op, "rows", count)
            self._observe_operation_success(op, op_start)
            logger.info(
                "observability_audit_events_count_completed",
                operation="audit_events_count",
                count=count,
            )
            return count
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_audit_events_count_failed",
                operation="audit_events_count",
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao contar eventos de auditoria.") from e

    def get_llm_usage_summary(self, start_ts: float | None, end_ts: float | None) -> dict[str, Any]:
        op = "llm_usage_summary"
        op_start = self._observe_operation_start(op)
        logger.info(
            "observability_llm_usage_summary_requested",
            operation="llm_usage_summary",
            start_ts=start_ts,
            end_ts=end_ts,
        )
        try:
            o = self._repo.get_audit_events(
                None, "openai", "ok", start_ts, end_ts, limit=10000, offset=0
            )
            g = self._repo.get_audit_events(
                None, "google_gemini", "ok", start_ts, end_ts, limit=10000, offset=0
            )
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_llm_usage_summary_failed",
                operation=op,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao gerar resumo de uso de LLMs.") from e

        def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
            import json as _json

            c = len(rows)
            s_in = 0
            s_out = 0
            s_cost = 0.0
            for r in rows:
                d = r.get("details_json")
                if not d:
                    continue
                try:
                    dj = _json.loads(d)
                    s_in += int(dj.get("input_tokens") or 0)
                    s_out += int(dj.get("output_tokens") or 0)
                    s_cost += float(dj.get("cost_usd") or 0.0)
                except Exception as e:
                    logger.debug(
                        "observability_llm_usage_details_parse_failed",
                        operation="llm_usage_summary",
                        error=str(e),
                    )
            return {
                "calls": c,
                "avg_input_tokens": (s_in / c) if c else 0,
                "avg_output_tokens": (s_out / c) if c else 0,
                "avg_cost_usd": (s_cost / c) if c else 0.0,
            }

        a_o = agg(o)
        a_g = agg(g)
        summary = {
            "openai": a_o,
            "gemini": a_g,
            "total_calls": a_o["calls"] + a_g["calls"],
            "window": {"start_ts": start_ts, "end_ts": end_ts},
        }
        logger.info(
            "observability_llm_usage_summary_completed",
            operation="llm_usage_summary",
            total_calls=summary["total_calls"],
            openai_calls=a_o["calls"],
            gemini_calls=a_g["calls"],
        )
        self._observe_result_size(op, "rows", int(summary["total_calls"]))
        self._observe_operation_success(op, op_start)
        return summary

    @staticmethod
    def _normalize_counter_key(value: Any) -> str:
        if value is None:
            return "unknown"
        text = str(value).strip()
        return text if text else "unknown"

    @staticmethod
    def _parse_details_payload(details_json: Any) -> dict[str, Any] | None:
        if details_json is None:
            return None
        if isinstance(details_json, dict):
            return details_json
        if isinstance(details_json, str):
            raw = details_json.strip()
            if not raw:
                return None
            try:
                parsed = json.loads(raw)
            except Exception:
                return {"raw": raw}
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        return {"raw": str(details_json)}

    def get_request_pipeline_dashboard(
        self, request_id: str, limit: int = 2000, include_details: bool = False
    ) -> dict[str, Any]:
        op = "request_pipeline_dashboard"
        op_start = self._observe_operation_start(op)
        request_id = str(request_id or "").strip()
        if not request_id:
            raise ObservabilityServiceError("request_id cannot be empty.")
        logger.info(
            "observability_request_pipeline_dashboard_requested",
            operation="request_pipeline_dashboard",
            request_id=request_id,
            limit=limit,
            include_details=include_details,
        )

        try:
            events = self._repo.get_audit_events_by_trace_id(
                trace_id=request_id, limit=limit, offset=0
            )
        except ObservabilityRepositoryError as e:
            self._observe_operation_failure(op, op_start, e)
            logger.exception(
                "observability_request_pipeline_dashboard_failed",
                operation="request_pipeline_dashboard",
                request_id=request_id,
                limit=limit,
                include_details=include_details,
                error=str(e),
            )
            raise ObservabilityServiceError("Falha ao montar dashboard por request_id.") from e

        if not events:
            logger.info(
                "observability_request_pipeline_dashboard_completed",
                operation="request_pipeline_dashboard",
                request_id=request_id,
                found=False,
                event_count=0,
            )
            self._observe_result_size(op, "timeline", 0)
            self._observe_operation_success(op, op_start)
            return {
                "request_id": request_id,
                "found": False,
                "summary": {
                    "total_events": 0,
                    "start_ts": None,
                    "end_ts": None,
                    "duration_ms": 0,
                    "status_counts": {},
                    "endpoint_counts": {},
                    "action_counts": {},
                    "tool_counts": {},
                },
                "timeline": [],
            }

        events_sorted = sorted(events, key=lambda ev: float(ev.get("created_at") or 0.0))
        start_ts = float(events_sorted[0].get("created_at") or 0.0)
        end_ts = float(events_sorted[-1].get("created_at") or 0.0)
        duration_ms = int(round(max(0.0, (end_ts - start_ts) * 1000.0)))

        status_counts: Counter[str] = Counter()
        endpoint_counts: Counter[str] = Counter()
        action_counts: Counter[str] = Counter()
        tool_counts: Counter[str] = Counter()
        timeline: list[dict[str, Any]] = []

        for ev in events_sorted:
            status_key = self._normalize_counter_key(ev.get("status"))
            endpoint_key = self._normalize_counter_key(ev.get("endpoint"))
            action_key = self._normalize_counter_key(ev.get("action"))
            tool_key = self._normalize_counter_key(ev.get("tool"))
            status_counts[status_key] += 1
            endpoint_counts[endpoint_key] += 1
            action_counts[action_key] += 1
            tool_counts[tool_key] += 1

            ts = float(ev.get("created_at") or 0.0)
            details = self._parse_details_payload(ev.get("details_json"))
            stage = None
            if isinstance(details, dict):
                stage = details.get("stage") or details.get("event_type") or details.get("step")

            item = {
                "id": ev.get("id"),
                "timestamp": ts if ts > 0 else None,
                "offset_ms": int(round(max(0.0, (ts - start_ts) * 1000.0))),
                "endpoint": ev.get("endpoint"),
                "action": ev.get("action"),
                "tool": ev.get("tool"),
                "status": ev.get("status"),
                "latency_ms": ev.get("latency_ms"),
                "stage": stage,
            }
            if include_details and details is not None:
                item["details"] = details
            timeline.append(item)

        result = {
            "request_id": request_id,
            "found": True,
            "summary": {
                "total_events": len(events_sorted),
                "start_ts": start_ts if start_ts > 0 else None,
                "end_ts": end_ts if end_ts > 0 else None,
                "duration_ms": duration_ms,
                "status_counts": dict(sorted(status_counts.items())),
                "endpoint_counts": dict(sorted(endpoint_counts.items())),
                "action_counts": dict(sorted(action_counts.items())),
                "tool_counts": dict(sorted(tool_counts.items())),
            },
            "timeline": timeline,
        }
        logger.info(
            "observability_request_pipeline_dashboard_completed",
            operation="request_pipeline_dashboard",
            request_id=request_id,
            found=True,
            event_count=len(events_sorted),
            timeline_count=len(timeline),
            duration_ms=duration_ms,
        )
        self._observe_result_size(op, "timeline", len(timeline))
        self._observe_operation_success(op, op_start)
        return result


def observe_ux_metric_record(
    *,
    outcome: str,
    provider: str | None,
    ttft_ms: float | None,
    latency_ms: float | None,
) -> None:
    provider_value = (provider or "unknown").strip().lower() or "unknown"
    provider_value = provider_value[:64]
    outcome_value = (outcome or "unknown").strip().lower() or "unknown"
    _OBS_UX_METRICS_TOTAL.labels(outcome=outcome_value, provider=provider_value).inc()

    ttft = ObservabilityService._safe_float(ttft_ms)
    if ttft is not None and ttft >= 0.0:
        _OBS_UX_LATENCY_SECONDS.labels(metric="ttft", outcome=outcome_value).observe(ttft / 1000.0)

    latency = ObservabilityService._safe_float(latency_ms)
    if latency is not None and latency >= 0.0:
        _OBS_UX_LATENCY_SECONDS.labels(metric="latency", outcome=outcome_value).observe(
            latency / 1000.0
        )


# Padrão de Injeção de Dependência: Getter para o serviço
def get_observability_service(request: Request) -> ObservabilityService:
    return request.app.state.observability_service
