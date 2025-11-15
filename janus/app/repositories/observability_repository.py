import structlog
from typing import Dict, Any, List, Optional
from fastapi import Depends

from app.core.monitoring import get_health_monitor, HealthMonitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler, PoisonPillHandler, QuarantinedMessage
from app.db.graph import get_graph_db
from app.db.mysql_config import mysql_db
from app.models.user_models import Session as ChatSession, Message, AuditEvent
from app.db.vector_store import get_collection_info

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

    async def get_system_health(self) -> Dict[str, Any]:
        logger.debug("Buscando saúde agregada do sistema via repositório.")
        try:
            return self._monitor.get_system_health()
        except Exception as e:
            logger.error("Erro no repositório ao buscar saúde do sistema", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao buscar a saúde do sistema.") from e

    async def check_all_components(self) -> Dict[str, Dict[str, Any]]:
        logger.debug("Disparando health check de todos os componentes via repositório.")
        try:
            results = await self._monitor.check_all_components()
            return {name: r.to_dict() for name, r in results.items()}
        except Exception as e:
            logger.error("Erro no repositório ao executar health checks", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao executar os health checks.") from e

    async def get_component_health(self, component: str) -> Dict[str, Any]:
        logger.debug("Checando saúde de componente via repositório", component=component)
        try:
            result = await self._monitor.check_component(component)
            return result.to_dict()
        except Exception as e:
            logger.error("Erro no repositório ao verificar componente", component=component, exc_info=e)
            raise ObservabilityRepositoryError(f"Falha ao verificar health do componente '{component}'.") from e

    async def get_llm_manager_health(self) -> Dict[str, Any]:
        return await self.get_component_health("llm_manager")

    async def get_multi_agent_system_health(self) -> Dict[str, Any]:
        return await self.get_component_health("multi_agent_system")

    async def get_poison_pill_handler_health(self) -> Dict[str, Any]:
        return await self.get_component_health("poison_pill_handler")

    def get_quarantined_messages(self, queue: Optional[str] = None) -> List[QuarantinedMessage]:
        logger.debug("Buscando mensagens em quarentena via repositório", queue=queue)
        return self._pp_handler.get_quarantined_messages(queue=queue)

    def release_from_quarantine(self, message_id: str, allow_retry: bool) -> QuarantinedMessage:
        logger.debug("Liberando mensagem da quarentena via repositório", message_id=message_id)
        msg = self._pp_handler.release_from_quarantine(message_id, allow_retry)
        if not msg:
            raise ObservabilityRepositoryError(f"Mensagem com ID '{message_id}' não encontrada na quarentena.")
        return msg

    def cleanup_expired_quarantine(self) -> int:
        logger.debug("Limpando mensagens expiradas da quarentena via repositório")
        try:
            return self._pp_handler.cleanup_expired_quarantine()
        except Exception as e:
            logger.error("Erro no repositório ao limpar quarentena expirada", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao limpar quarentena expirada.") from e

    def get_poison_pill_stats(self, queue: Optional[str] = None) -> Dict[str, Any]:
        logger.debug("Buscando estatísticas de poison pills via repositório", queue=queue)
        return self._pp_handler.get_failure_stats(queue=queue)

    def get_metrics_summary(self) -> Dict[str, Any]:
        logger.debug("Coletando resumo de métricas do sistema via repositório.")
        from app.core.llm import _provider_circuit_breakers, _llm_pool
        from app.core.agents import get_multi_agent_system

        llm_stats = {
            "pool_keys": len(_llm_pool),
            "pool_total_instances": sum(len(v) for v in _llm_pool.values()),
            "circuit_breakers": {
                provider: {"state": cb.state.value, "failure_count": cb.failure_count}
                for provider, cb in _provider_circuit_breakers.items()
            }
        }

        ma_system = get_multi_agent_system()
        ma_stats = {
            "active_agents": len(ma_system.agents),
            "workspace_tasks": len(ma_system.workspace.tasks),
            "workspace_artifacts": len(ma_system.workspace.artifacts)
        }

        pp_stats = self._pp_handler.get_health_status()

        return {
            "llm": llm_stats,
            "multi_agent": ma_stats,
            "poison_pills": pp_stats
        }

    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        s = mysql_db.get_session_direct()
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
                    tlen = len((m.text or ""))
                    approx_tokens = max(1, int(tlen / 4))
                    if (m.role or "").lower() == "user":
                        in_tokens += approx_tokens
                    else:
                        out_tokens += approx_tokens
            try:
                info = get_collection_info(f"user_{user_id}")
                points_count = int(info.get("points_count") or 0)
            except Exception:
                points_count = 0
            return {
                "user_id": user_id,
                "conversations": conversations_count,
                "messages": total_messages,
                "approx_in_tokens": in_tokens,
                "approx_out_tokens": out_tokens,
                "vector_points": points_count,
            }
        finally:
            s.close()

    def get_user_activity(self, user_id: str) -> Dict[str, Any]:
        s = mysql_db.get_session_direct()
        try:
            runs = s.query(AutonomyRun).filter(AutonomyRun.user_id == user_id).all()
            runs_count = len(runs)
            steps_count = s.query(AutonomyStep).join(AutonomyRun, AutonomyStep.run_id == AutonomyRun.id).filter(AutonomyRun.user_id == user_id).count()
            import math
            durations = [float(x.duration_seconds) for x in s.query(AutonomyStep.duration_seconds).join(AutonomyRun, AutonomyStep.run_id == AutonomyRun.id).filter(AutonomyRun.user_id == user_id).all()]
            avg_step_duration = (sum(durations) / len(durations)) if durations else 0.0
            return {
                "user_id": user_id,
                "autonomy_runs": runs_count,
                "autonomy_steps": steps_count,
                "avg_step_duration_seconds": round(avg_step_duration, 4),
            }
        finally:
            s.close()

    async def get_graph_audit_report(self) -> Dict[str, Any]:
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
                operation="audit_rel_types"
            )
            rel_types_present = [row.get("rel") for row in rel_types_rows]

            registered_rows = await db.query(
                "MATCH (t:RelationshipType) RETURN DISTINCT t.name AS name ORDER BY name",
                operation="audit_registered_rel_types"
            )
            rel_types_registered = [row.get("name") for row in registered_rows]

            unregistered_rows = await db.query(
                "MATCH ()-[r]->() WITH DISTINCT type(r) AS rel MATCH (t:RelationshipType) RETURN rel WHERE NOT rel IN collect(t.name)",
                operation="audit_unregistered_rel_types"
            )
            rel_types_unregistered = [row.get("rel") for row in unregistered_rows]

            nonstandard_rows = await db.query(
                "MATCH ()-[r]->() WITH DISTINCT type(r) AS t WHERE NOT t =~ '^[A-Z_]+$' RETURN t",
                operation="audit_nonstandard_rel_types"
            )
            rel_types_nonstandard = [row.get("t") for row in nonstandard_rows]

            quarantine_rows = await db.query(
                "MATCH (q:Quarantine) RETURN COUNT(q) AS total",
                operation="audit_quarantine_count"
            )
            quarantine_count = (quarantine_rows[0].get("total") if quarantine_rows else 0) or 0

            mentions_rows = await db.query(
                "MATCH (:Experience)-[r:MENTIONS]->() RETURN COUNT(r) AS total",
                operation="audit_mentions_count"
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
            logger.error("Erro ao executar auditoria do grafo", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao executar auditoria do grafo.") from e

    async def get_graph_quarantine_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            db = await get_graph_db()
            rows = await db.query(
                "MATCH (q:Quarantine) RETURN id(q) AS node_id, q.reason AS reason, q.type AS type, q.from_name AS from_name, q.to_name AS to_name, q.confidence AS confidence, q.source_snippet AS source_snippet ORDER BY q.created_at DESC LIMIT $limit",
                params={"limit": limit},
                operation="list_quarantine_items",
            )
            return rows
        except Exception as e:
            logger.error("Erro ao listar itens de quarentena do grafo", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao listar itens de quarentena do grafo.") from e

    async def promote_quarantine_item(self, node_id: int) -> Dict[str, Any]:
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
            logger.error("Erro ao promover item de quarentena", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao promover item de quarentena.") from e

    def record_audit_event(self, event: Dict[str, Any]) -> None:
        s = mysql_db.get_session_direct()
        try:
            ae = AuditEvent(
                user_id=int(event.get("user_id")) if event.get("user_id") is not None else None,
                endpoint=str(event.get("endpoint")),
                action=str(event.get("action")),
                tool=event.get("tool"),
                status=str(event.get("status")),
                latency_ms=int(event.get("latency_ms")) if event.get("latency_ms") is not None else None,
                trace_id=str(event.get("trace_id")) if event.get("trace_id") is not None else None,
            )
            s.add(ae)
            s.commit()
        except Exception as e:
            s.rollback()
            logger.error("Erro ao registrar evento de auditoria", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao registrar evento de auditoria.") from e
        finally:
            s.close()

    def get_audit_events(self, user_id: Optional[str], tool: Optional[str], status: Optional[str], start_ts: Optional[float], end_ts: Optional[float], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        s = mysql_db.get_session_direct()
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
                    "created_at": getattr(r, "created_at").timestamp() if getattr(r, "created_at", None) else None,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error("Erro ao consultar eventos de auditoria", exc_info=e)
            raise ObservabilityRepositoryError("Falha ao consultar eventos de auditoria.") from e
        finally:
            s.close()


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

async def get_observability_repository(
        monitor: HealthMonitor = Depends(get_health_monitor),
        pp_handler: PoisonPillHandler = Depends(get_poison_pill_handler)
) -> ObservabilityRepository:
    return ObservabilityRepository(monitor, pp_handler)
