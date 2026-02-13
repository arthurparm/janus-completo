import json
from collections import Counter
from typing import Any

import structlog
from fastapi import Request

from app.core.monitoring.poison_pill_handler import QuarantinedMessage
from app.repositories.observability_repository import (
    ObservabilityRepository,
    ObservabilityRepositoryError,
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

    async def get_llm_manager_health(self) -> dict[str, Any]:
        logger.info("Checando saúde do LLM Manager via serviço.")
        try:
            return await self._repo.get_llm_manager_health()
        except ObservabilityRepositoryError as e:
            logger.error("Erro no repositório ao checar LLM Manager", exc_info=e)
            raise ObservabilityServiceError("Falha ao buscar saúde do LLM Manager.") from e

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
