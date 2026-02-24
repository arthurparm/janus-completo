import asyncio
import json
from typing import Any

import structlog
from fastapi import Depends

from app.core.monitoring import HealthMonitor, get_health_monitor
from app.core.monitoring.poison_pill_handler import (
    PoisonPillHandler,
    QuarantinedMessage,
    get_poison_pill_handler,
)
from app.db.graph import get_graph_db
from app.db import db
from app.db.vector_store import aget_collection_info
from app.models.autonomy_models import AutonomyRun, AutonomyStep
from app.models.user_models import AuditEvent, Message
from app.models.user_models import Session as ChatSession

logger = structlog.get_logger(__name__)


class ObservabilityRepositoryError(Exception):
    """Base exception for observability repository errors."""

    pass


class ObservabilityRepository:
    """
    Camada de Repositório para Observabilidade.
    Abstrai todas as interações diretas com os monitores de saúde e handlers de poison pill.
    """

    def __init__(self, monitor: HealthMonitor, pp_handler: PoisonPillHandler):
        self._monitor = monitor
        self._pp_handler = pp_handler

    async def get_system_health(self) -> dict[str, Any]:
        logger.debug("observability_repo_system_health_requested")
        try:
            return self._monitor.get_system_health()
        except Exception as e:
            logger.exception("observability_repo_system_health_failed", error=str(e))
            raise ObservabilityRepositoryError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> dict[str, dict[str, Any]]:
        logger.debug("observability_repo_check_all_components_requested")
        try:
            results = await self._monitor.check_all_components()
            return {name: r.to_dict() for name, r in results.items()}
        except Exception as e:
            logger.exception("observability_repo_check_all_components_failed", error=str(e))
            raise ObservabilityRepositoryError("Falha ao executar os health checks.") from e

    async def get_component_health(self, component: str) -> dict[str, Any]:
        logger.debug("observability_repo_component_health_requested", component=component)
        try:
            result = await self._monitor.check_component(component)
            return result.to_dict()
        except Exception as e:
            logger.exception(
                "observability_repo_component_health_failed",
                component=component,
                error=str(e),
            )
            raise ObservabilityRepositoryError(
                f"Falha ao verificar health do componente '{component}'."
            ) from e

    async def get_llm_router_health(self) -> dict[str, Any]:
        return await self.get_component_health("llm_router")

    async def get_multi_agent_system_health(self) -> dict[str, Any]:
        return await self.get_component_health("multi_agent_system")

    async def get_poison_pill_handler_health(self) -> dict[str, Any]:
        return await self.get_component_health("poison_pill_handler")

    def get_quarantined_messages(self, queue: str | None = None) -> list[QuarantinedMessage]:
        logger.debug("observability_repo_quarantine_messages_requested", queue=queue)
        return self._pp_handler.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.debug(
            "observability_repo_quarantine_release_requested",
            message_id=message_id,
            allow_retry=allow_retry,
        )
        msg = self._pp_handler.release_from_quarantine(message_id, allow_retry)
        if not msg:
            raise ObservabilityRepositoryError(
                f"Mensagem com ID '{message_id}' não encontrada na quarentena."
            )
        return msg

    def cleanup_expired_quarantine(self) -> int:
        logger.debug("observability_repo_quarantine_cleanup_requested")
        try:
            return self._pp_handler.cleanup_expired_quarantine()
        except Exception as e:
            logger.exception("observability_repo_quarantine_cleanup_failed", error=str(e))
            raise ObservabilityRepositoryError("Falha ao limpar quarentena expirada.") from e

    def get_poison_pill_stats(self, queue: str | None = None) -> dict[str, Any]:
        logger.debug("observability_repo_poison_pill_stats_requested", queue=queue)
        return self._pp_handler.get_failure_stats(queue=queue)

    def get_metrics_summary(self) -> dict[str, Any]:
        logger.debug("observability_repo_metrics_summary_requested")
        from app.core.agents import get_multi_agent_system
        from app.core.llm import get_circuit_breaker_snapshot, get_llm_pool_summary

        pool_summary = get_llm_pool_summary()
        cb_snapshot = get_circuit_breaker_snapshot()

        llm_stats = {
            "pool_keys": pool_summary["pool_keys"],
            "pool_total_instances": pool_summary["pool_total_instances"],
            "circuit_breakers": {
                provider: {
                    "state": details.get("state"),
                    "failure_count": details.get("failure_count"),
                }
                for provider, details in cb_snapshot.items()
            },
        }

        ma_system = get_multi_agent_system()
        ma_stats = {
            "active_agents": len(ma_system.agents),
            "workspace_tasks": len(ma_system.workspace.tasks),
            "workspace_artifacts": len(ma_system.workspace.artifacts),
        }

        pp_stats = self._pp_handler.get_health_status()

        return {"llm": llm_stats, "multi_agent": ma_stats, "poison_pills": pp_stats}

    async def get_user_metrics(self, user_id: str) -> dict[str, Any]:
        def _compute_sql_metrics() -> dict[str, Any]:
            s = db.get_session_direct()
            try:
                convs = s.query(ChatSession).filter(ChatSession.user_id == int(user_id)).all()
                conversations_count = len(convs)
                total_messages = 0
                in_tokens = 0
                out_tokens = 0
                for c in convs:
                    msgs = s.query(Message).filter(Message.session_id == c.id).all()
                    total_messages += len(msgs)
                    for m in msgs:
                        tlen = len(m.text or "")
                        approx_tokens = max(1, int(tlen / 4))
                        if (m.role or "").lower() == "user":
                            in_tokens += approx_tokens
                        else:
                            out_tokens += approx_tokens
                return {
                    "user_id": user_id,
                    "conversations": conversations_count,
                    "messages": total_messages,
                    "approx_in_tokens": in_tokens,
                    "approx_out_tokens": out_tokens,
                }
            finally:
                s.close()

        metrics = await asyncio.to_thread(_compute_sql_metrics)
        try:
            info = await aget_collection_info(f"user_{user_id}")
            metrics["vector_points"] = int(info.get("points_count") or 0)
        except Exception:
            metrics["vector_points"] = 0
        return metrics

    def get_user_activity(self, user_id: str) -> dict[str, Any]:
        s = db.get_session_direct()
        try:
            runs = s.query(AutonomyRun).filter(AutonomyRun.user_id == user_id).all()
            runs_count = len(runs)
            steps_count = (
                s.query(AutonomyStep)
                .join(AutonomyRun, AutonomyStep.run_id == AutonomyRun.id)
                .filter(AutonomyRun.user_id == user_id)
                .count()
            )
            durations = [
                float(x.duration_seconds)
                for x in s.query(AutonomyStep.duration_seconds)
                .join(AutonomyRun, AutonomyStep.run_id == AutonomyRun.id)
                .filter(AutonomyRun.user_id == user_id)
                .all()
            ]
            avg_step_duration = (sum(durations) / len(durations)) if durations else 0.0
            return {
                "user_id": user_id,
                "autonomy_runs": runs_count,
                "autonomy_steps": steps_count,
                "avg_step_duration_seconds": round(avg_step_duration, 4),
            }
        finally:
            s.close()

    async def get_graph_audit_report(self) -> dict[str, Any]:
        """
        Executa consultas de auditoria no Neo4j para avaliar a higiene do grafo.

        Retorna:
            - relationship_types_present: lista de tipos presentes no grafo
            - relationship_types_registered: lista de tipos registrados em RelationshipType
            - relationship_types_unregistered: presentes mas não registrados
            - relationship_types_nonstandard: tipos que não estão em UPPERCASE/UNDERSCORE
            - quarantine_count: quantidade de nós Quarantine
            - mentions_count: quantidade de relações MENTIONS
        """
        try:
            db = await get_graph_db()
            rel_types_rows = await db.query(
                "MATCH ()-[r]->() RETURN DISTINCT type(r) AS rel ORDER BY rel",
                operation="audit_rel_types",
            )
            rel_types_present = [row.get("rel") for row in rel_types_rows]

            registered_rows = await db.query(
                "MATCH (t:RelationshipType) RETURN DISTINCT t.name AS name ORDER BY name",
                operation="audit_registered_rel_types",
            )
            rel_types_registered = [row.get("name") for row in registered_rows]

            unregistered_rows = await db.query(
                "MATCH ()-[r]->() WITH DISTINCT type(r) AS rel MATCH (t:RelationshipType) RETURN rel WHERE NOT rel IN collect(t.name)",
                operation="audit_unregistered_rel_types",
            )
            rel_types_unregistered = [row.get("rel") for row in unregistered_rows]

            nonstandard_rows = await db.query(
                "MATCH ()-[r]->() WITH DISTINCT type(r) AS t WHERE NOT t =~ '^[A-Z_]+$' RETURN t",
                operation="audit_nonstandard_rel_types",
            )
            rel_types_nonstandard = [row.get("t") for row in nonstandard_rows]

            quarantine_rows = await db.query(
                "MATCH (q:Quarantine) RETURN COUNT(q) AS total", operation="audit_quarantine_count"
            )
            quarantine_count = (quarantine_rows[0].get("total") if quarantine_rows else 0) or 0

            mentions_rows = await db.query(
                "MATCH (:Experience)-[r:MENTIONS]->() RETURN COUNT(r) AS total",
                operation="audit_mentions_count",
            )
            mentions_count = (mentions_rows[0].get("total") if mentions_rows else 0) or 0

            return {
                "relationship_types_present": rel_types_present,
                "relationship_types_registered": rel_types_registered,
                "relationship_types_unregistered": rel_types_unregistered,
                "relationship_types_nonstandard": rel_types_nonstandard,
                "quarantine_count": quarantine_count,
                "mentions_count": mentions_count,
            }
        except Exception as e:
            logger.exception("observability_repo_graph_audit_failed", error=str(e))
            raise ObservabilityRepositoryError("Falha ao executar auditoria do grafo.") from e

    async def get_graph_quarantine_items(self, limit: int = 100) -> list[dict[str, Any]]:
        try:
            db = await get_graph_db()
            rows = await db.query(
                "MATCH (q:Quarantine) RETURN id(q) AS node_id, q.reason AS reason, q.type AS type, q.from_name AS from_name, q.to_name AS to_name, q.confidence AS confidence, q.source_snippet AS source_snippet ORDER BY q.created_at DESC LIMIT $limit",
                params={"limit": limit},
                operation="list_quarantine_items",
            )
            return rows
        except Exception as e:
            logger.exception(
                "observability_repo_graph_quarantine_list_failed",
                limit=limit,
                error=str(e),
            )
            raise ObservabilityRepositoryError(
                "Falha ao listar itens de quarentena do grafo."
            ) from e

    async def promote_quarantine_item(self, node_id: int) -> dict[str, Any]:
        try:
            db = await get_graph_db()
            async with await db.get_session() as session:
                tx = await session.begin_transaction()
                rec = await tx.run(
                    "MATCH (q:Quarantine) WHERE id(q) = $id RETURN q.reason AS reason, q.type AS type, q.from_name AS from_name, q.to_name AS to_name, q.confidence AS confidence, q.source_snippet AS source_snippet",
                    id=node_id,
                )
                qrow = await rec.single()
                if not qrow:
                    await tx.close()
                    raise ObservabilityRepositoryError("Item de quarentena não encontrado.")
                rel_type = qrow.get("type")
                await db.register_relationship_type(tx, rel_type)
                await tx.run(
                    f"""
                    MATCH (a {{name: $from_name}})
                    MATCH (b {{name: $to_name}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    ON CREATE SET r.confidence = $confidence, r.discovered_at = datetime(), r.first_seen = datetime(), r.occurrences = 1, r.source_snippet = $source_snippet
                    ON MATCH SET r.confidence = CASE WHEN $confidence > coalesce(r.confidence, 0) THEN $confidence ELSE r.confidence END, r.last_seen = datetime(), r.occurrences = coalesce(r.occurrences, 0) + 1, r.source_snippet = coalesce(r.source_snippet, $source_snippet)
                    """,
                    from_name=qrow.get("from_name"),
                    to_name=qrow.get("to_name"),
                    confidence=float(qrow.get("confidence") or 0.0),
                    source_snippet=qrow.get("source_snippet"),
                )
                await tx.run(
                    "MATCH (q:Quarantine) WHERE id(q) = $id SET q.status = 'promoted', q.promoted_at = datetime()",
                    id=node_id,
                )
                await tx.commit()
                return {
                    "node_id": node_id,
                    "status": "promoted",
                    "type": rel_type,
                }
        except Exception as e:
            logger.exception(
                "observability_repo_graph_quarantine_promote_failed",
                node_id=node_id,
                error=str(e),
            )
            raise ObservabilityRepositoryError("Falha ao promover item de quarentena.") from e

    def record_audit_event(self, event: dict[str, Any]) -> None:
        s = db.get_session_direct()
        try:
            # Converte user_id para int apenas se for um valor numérico válido
            raw_user_id = event.get("user_id")
            user_id_int = None
            if raw_user_id is not None and str(raw_user_id) not in ("-", "", "None"):
                try:
                    user_id_int = int(raw_user_id)
                except (ValueError, TypeError):
                    user_id_int = None
            ae = AuditEvent(
                user_id=user_id_int,
                endpoint=str(event.get("endpoint")),
                action=str(event.get("action")),
                tool=event.get("tool"),
                status=str(event.get("status")),
                latency_ms=int(event.get("latency_ms"))
                if event.get("latency_ms") is not None
                else None,
                trace_id=str(event.get("trace_id")) if event.get("trace_id") is not None else None,
                details_json=(
                    event.get("details_json")
                    if event.get("details_json") is not None
                    else (
                        json.dumps(event.get("detail")) if event.get("detail") is not None else None
                    )
                ),
            )
            s.add(ae)
            s.commit()
        except Exception as e:
            s.rollback()
            logger.exception("observability_repo_audit_event_record_failed", error=str(e))
            raise ObservabilityRepositoryError("Falha ao registrar evento de auditoria.") from e
        finally:
            s.close()

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
        s = db.get_session_direct()
        try:
            q = s.query(AuditEvent)
            if user_id is not None:
                try:
                    q = q.filter(AuditEvent.user_id == int(user_id))
                except Exception:
                    q = q.filter(AuditEvent.user_id == -1)
            if tool is not None:
                q = q.filter(AuditEvent.tool == str(tool))
            if status is not None:
                q = q.filter(AuditEvent.status == str(status))
            if endpoint is not None:
                q = q.filter(AuditEvent.endpoint == str(endpoint))
            if start_ts is not None:
                from datetime import datetime

                q = q.filter(AuditEvent.created_at >= datetime.fromtimestamp(float(start_ts)))
            if end_ts is not None:
                from datetime import datetime

                q = q.filter(AuditEvent.created_at <= datetime.fromtimestamp(float(end_ts)))
            q = q.order_by(AuditEvent.created_at.desc())
            q = q.offset(int(offset)).limit(int(limit))
            rows = q.all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "endpoint": r.endpoint,
                    "action": r.action,
                    "tool": r.tool,
                    "status": r.status,
                    "latency_ms": r.latency_ms,
                    "trace_id": r.trace_id,
                    "justification": r.justification,
                    "created_at": r.created_at.timestamp()
                    if getattr(r, "created_at", None)
                    else None,
                    "details_json": r.details_json,
                }
                for r in rows
            ]
        except Exception as e:
            logger.exception(
                "observability_repo_audit_events_query_failed",
                user_id=user_id,
                tool=tool,
                status=status,
                endpoint=endpoint,
                limit=limit,
                offset=offset,
                error=str(e),
            )
            raise ObservabilityRepositoryError("Falha ao consultar eventos de auditoria.") from e
        finally:
            s.close()

    def get_audit_events_by_trace_id(
        self, trace_id: str, limit: int = 2000, offset: int = 0
    ) -> list[dict[str, Any]]:
        s = db.get_session_direct()
        try:
            q = (
                s.query(AuditEvent)
                .filter(AuditEvent.trace_id == str(trace_id))
                .order_by(AuditEvent.created_at.asc())
                .offset(int(offset))
                .limit(int(limit))
            )
            rows = q.all()
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "endpoint": r.endpoint,
                    "action": r.action,
                    "tool": r.tool,
                    "status": r.status,
                    "latency_ms": r.latency_ms,
                    "trace_id": r.trace_id,
                    "justification": r.justification,
                    "created_at": r.created_at.timestamp()
                    if getattr(r, "created_at", None)
                    else None,
                    "details_json": r.details_json,
                }
                for r in rows
            ]
        except Exception as e:
            logger.exception(
                "observability_repo_audit_events_by_trace_id_failed",
                trace_id=trace_id,
                limit=limit,
                offset=offset,
                error=str(e),
            )
            raise ObservabilityRepositoryError(
                "Falha ao consultar eventos de auditoria por trace_id."
            ) from e
        finally:
            s.close()

    def get_audit_events_count(
        self,
        user_id: str | None,
        tool: str | None,
        status: str | None,
        start_ts: float | None,
        end_ts: float | None,
    ) -> int:
        s = db.get_session_direct()
        try:
            q = s.query(AuditEvent)
            if user_id is not None:
                try:
                    q = q.filter(AuditEvent.user_id == int(user_id))
                except Exception:
                    q = q.filter(AuditEvent.user_id == -1)
            if tool is not None:
                q = q.filter(AuditEvent.tool == str(tool))
            if status is not None:
                q = q.filter(AuditEvent.status == str(status))
            if start_ts is not None:
                from datetime import datetime

                q = q.filter(AuditEvent.created_at >= datetime.fromtimestamp(float(start_ts)))
            if end_ts is not None:
                from datetime import datetime

                q = q.filter(AuditEvent.created_at <= datetime.fromtimestamp(float(end_ts)))
            return int(q.count())
        except Exception as e:
            logger.exception(
                "observability_repo_audit_events_count_failed",
                user_id=user_id,
                tool=tool,
                status=status,
                error=str(e),
            )
            raise ObservabilityRepositoryError("Falha ao contar eventos de auditoria.") from e
        finally:
            s.close()


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---


async def get_observability_repository(
    monitor: HealthMonitor = Depends(get_health_monitor),
    pp_handler: PoisonPillHandler = Depends(get_poison_pill_handler),
) -> ObservabilityRepository:
    return ObservabilityRepository(monitor, pp_handler)


# Helper direto para registrar eventos de auditoria
def record_audit_event_direct(event: dict[str, Any]) -> None:
    s = db.get_session_direct()
    try:
        # Converte user_id para int apenas se for um valor numérico válido
        raw_user_id = event.get("user_id")
        user_id_int = None
        if raw_user_id is not None and str(raw_user_id) not in ("-", "", "None"):
            try:
                user_id_int = int(raw_user_id)
            except (ValueError, TypeError):
                user_id_int = None
        ae = AuditEvent(
            user_id=user_id_int,
            endpoint=str(event.get("endpoint")),
            action=str(event.get("action")),
            tool=event.get("tool"),
            status=str(event.get("status")),
            latency_ms=int(event.get("latency_ms"))
            if event.get("latency_ms") is not None
            else None,
            trace_id=str(event.get("trace_id")) if event.get("trace_id") is not None else None,
            details_json=(
                event.get("details_json")
                if event.get("details_json") is not None
                else (json.dumps(event.get("detail")) if event.get("detail") is not None else None)
            ),
        )
        s.add(ae)
        s.commit()
    except Exception as e:
        try:
            s.rollback()
        except Exception:
            pass
        logger.exception("observability_repo_audit_event_record_direct_failed", error=str(e))
    finally:
        s.close()
