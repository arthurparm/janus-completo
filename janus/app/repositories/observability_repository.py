import structlog
from typing import Dict, Any, List, Optional
from fastapi import Depends

from app.core.monitoring import get_health_monitor, HealthMonitor
from app.core.monitoring.poison_pill_handler import get_poison_pill_handler, PoisonPillHandler, QuarantinedMessage
from app.db.graph import get_graph_db
from app.db.mysql_config import mysql_db
from app.models.user_models import Session as ChatSession, Message
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


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

async def get_observability_repository(
        monitor: HealthMonitor = Depends(get_health_monitor),
        pp_handler: PoisonPillHandler = Depends(get_poison_pill_handler)
) -> ObservabilityRepository:
    return ObservabilityRepository(monitor, pp_handler)
