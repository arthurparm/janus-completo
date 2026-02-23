import json
import time
from collections import Counter
from typing import Any

import structlog
from fastapi import Request

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

    async def get_system_health(self) -> dict[str, Any]:
        logger.info("Buscando saúde agregada do sistema via serviço.")
        try:
            return await self._repo.get_system_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao buscar saúde do sistema", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> dict[str, dict[str, Any]]:
        logger.info("Disparando health check de todos os componentes via serviço.")
        try:
            return await self._repo.check_all_components()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao executar health checks", exc_info=e)
            raise ObservabilityServiceError("Falha ao executar os health checks.") from e

    async def get_llm_router_health(self) -> dict[str, Any]:
        logger.info("Checando saúde do LLM Router via serviço.")
        try:
            return await self._repo.get_llm_router_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar LLM Router", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar saúde do LLM Router.") from e

    async def get_multi_agent_system_health(self) -> dict[str, Any]:
        logger.info("Checando saúde do Multi-Agent System via serviço.")
        try:
            return await self._repo.get_multi_agent_system_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar Multi-Agent System", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar saúde do sistema multi-agente.") from e

    async def get_poison_pill_handler_health(self) -> dict[str, Any]:
        logger.info("Checando saúde do Poison Pill Handler via serviço.")
        try:
            return await self._repo.get_poison_pill_handler_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar Poison Pill Handler", exc_info=e)
            raise ObservabilityServiceError(
                "Falha ao buscar saúde do handler de poison pills."
            ) from e

    def get_quarantined_messages(self, queue: str | None = None) -> list[QuarantinedMessage]:
        logger.info("Buscando mensagens em quarentena via serviço", queue=queue)
        return self._repo.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.info("Liberando mensagem da quarentena via serviço", message_id=message_id)
        try:
            msg = self._repo.release_from_quarantine(message_id, allow_retry)
            if not msg:
                raise MessageNotFoundError(
                    f"Mensagem com ID '{message_id}' não encontrada na quarentena."
                )
            return msg
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao liberar mensagem", exc_info=e)
            raise ObservabilityServiceError("Falha ao liberar mensagem da quarentena.") from e

    def cleanup_expired_quarantine(self) -> dict[str, Any]:
        logger.info("Limpando mensagens expiradas da quarentena via serviço.")
        try:
            removed = self._repo.cleanup_expired_quarantine()
            return {"removed": removed}
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao limpar quarentena expirada", exc_info=e)
            raise ObservabilityServiceError("Falha ao limpar a quarentena expirada.") from e

    def get_poison_pill_stats(self, queue: str | None = None) -> dict[str, Any]:
        logger.info("Buscando estatísticas de poison pills via serviço", queue=queue)
        return self._repo.get_poison_pill_stats(queue=queue)

    def get_metrics_summary(self) -> dict[str, Any]:
        logger.info("Coletando resumo de métricas do sistema via serviço.")
        try:
            return self._repo.get_metrics_summary()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao gerar resumo de métricas", exc_info=e)
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
        now_ts = float(time.time())
        wm = max(1, int(window_minutes or getattr(settings, "OQ_SLO_WINDOW_MINUTES", 15) or 15))
        me = max(
            1,
            int(min_events or getattr(settings, "OQ_SLO_MIN_EVENTS_PER_DOMAIN", 20) or 20),
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
            logger.error("Erro ao coletar eventos para OQ-002", exc_info=e)
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
        if not bool(getattr(settings, "AI_ANOMALY_DETECTION_ENABLED", True)):
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
            logger.error("Erro ao coletar eventos para AI-014", exc_info=e)
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
        return report

    async def get_user_metrics(self, user_id: str) -> dict[str, Any]:
        logger.info("Coletando métricas agregadas por usuário", user_id=user_id)
        try:
            return await self._repo.get_user_metrics(user_id)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao gerar métricas por usuário", exc_info=e)
            raise ObservabilityServiceError("Falha ao gerar métricas por usuário.") from e

    def get_user_activity(self, user_id: str) -> dict[str, Any]:
        logger.info("Coletando atividade agregada por usuário", user_id=user_id)
        try:
            return self._repo.get_user_activity(user_id)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao gerar atividade por usuário", exc_info=e)
            raise ObservabilityServiceError("Falha ao gerar atividade por usuário.") from e

    async def get_graph_audit_report(self) -> dict[str, Any]:
        logger.info("Executando auditoria de grafo via serviço.")
        try:
            return await self._repo.get_graph_audit_report()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao auditar grafo", exc_info=e)
            raise ObservabilityServiceError("Falha ao auditar o grafo.") from e

    async def get_graph_quarantine_items(self, limit: int = 100) -> list[dict[str, Any]]:
        logger.info("Listando itens em quarentena do grafo via serviço.", limit=limit)
        try:
            return await self._repo.get_graph_quarantine_items(limit)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao listar itens de quarentena", exc_info=e)
            raise ObservabilityServiceError("Falha ao listar itens de quarentena.") from e

    async def promote_quarantine_item(self, node_id: int) -> dict[str, Any]:
        logger.info("Promovendo item da quarentena do grafo via serviço.", node_id=node_id)
        try:
            return await self._repo.promote_quarantine_item(node_id)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao promover item de quarentena", exc_info=e)
            raise ObservabilityServiceError("Falha ao promover item de quarentena.") from e

    def record_audit_event(self, event: dict[str, Any]) -> None:
        logger.info(
            "Registrando evento de auditoria via serviço",
            **{k: v for k, v in event.items() if k != "detail"},
        )
        try:
            self._repo.record_audit_event(event)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao registrar evento de auditoria", exc_info=e)
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
        logger.info(
            "Consultando eventos de auditoria via serviço",
            user_id=user_id,
            tool=tool,
            status=status,
            endpoint=endpoint,
        )
        try:
            return self._repo.get_audit_events(
                user_id, tool, status, start_ts, end_ts, endpoint, limit, offset
            )
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao consultar eventos de auditoria", exc_info=e)
            raise ObservabilityServiceError("Falha ao consultar eventos de auditoria.") from e

    def get_audit_events_count(
        self,
        user_id: str | None,
        tool: str | None,
        status: str | None,
        start_ts: float | None,
        end_ts: float | None,
    ) -> int:
        try:
            return self._repo.get_audit_events_count(user_id, tool, status, start_ts, end_ts)
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositÇürio ao contar eventos de auditoria", exc_info=e)
            raise ObservabilityServiceError("Falha ao contar eventos de auditoria.") from e

    def get_llm_usage_summary(self, start_ts: float | None, end_ts: float | None) -> dict[str, Any]:
        o = self._repo.get_audit_events(
            None, "openai", "ok", start_ts, end_ts, limit=10000, offset=0
        )
        g = self._repo.get_audit_events(
            None, "google_gemini", "ok", start_ts, end_ts, limit=10000, offset=0
        )

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
                    logger.debug(f"Failed to parse usage details: {e}")
            return {
                "calls": c,
                "avg_input_tokens": (s_in / c) if c else 0,
                "avg_output_tokens": (s_out / c) if c else 0,
                "avg_cost_usd": (s_cost / c) if c else 0.0,
            }

        a_o = agg(o)
        a_g = agg(g)
        return {
            "openai": a_o,
            "gemini": a_g,
            "total_calls": a_o["calls"] + a_g["calls"],
            "window": {"start_ts": start_ts, "end_ts": end_ts},
        }

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
        request_id = str(request_id or "").strip()
        if not request_id:
            raise ObservabilityServiceError("request_id cannot be empty.")

        try:
            events = self._repo.get_audit_events_by_trace_id(
                trace_id=request_id, limit=limit, offset=0
            )
        except ObservabilityRepositoryError as e:
            logger.error(
                "Erro no repositório ao montar dashboard por request_id",
                request_id=request_id,
                exc_info=e,
            )
            raise ObservabilityServiceError("Falha ao montar dashboard por request_id.") from e

        if not events:
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

        return {
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


# Padrão de Injeção de Dependência: Getter para o serviço
def get_observability_service(request: Request) -> ObservabilityService:
    return request.app.state.observability_service
