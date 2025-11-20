import structlog
from typing import Dict, Any, Optional

try:
    from app.core.agents import get_meta_agent, MetaAgent
except Exception:
    def get_meta_agent():  # type: ignore
        class _Stub:
            async def run_analysis_cycle(self):
                return None
            def __init__(self):
                self.last_report = None
                self._heartbeat_task = None
                self.cycle_count = 0
                self.agent_id = "stub"
                self.executor = None
                self.tools = []
            async def start_heartbeat(self, interval_minutes: int):
                return None
            def stop_heartbeat(self):
                return None
        return _Stub()
    class MetaAgent:  # type: ignore
        pass
try:
    from app.core.agents.meta_agent import StateReport
except Exception:
    class StateReport:  # type: ignore
        def __init__(self):
            from datetime import datetime
            self.timestamp = datetime.now()

logger = structlog.get_logger(__name__)


# --- Custom Service-Layer Exceptions ---

class MetaAgentServiceError(Exception):
    """Base exception for meta-agent service errors."""
    pass


# --- Meta-Agent Service ---

class MetaAgentService:
    """
    Camada de serviço para o Meta-Agente de Auto-Otimização.
    Abstrai a lógica de controle do ciclo de vida do meta-agente da camada de API.
    """

    def _get_agent(self) -> MetaAgent:
        # Helper para obter a instância do meta-agente
        return get_meta_agent()

    async def run_analysis_cycle(self) -> StateReport:
        logger.info("Disparando ciclo de análise do meta-agente via serviço.")
        try:
            agent = self._get_agent()
            return await agent.run_analysis_cycle()
        except Exception as e:
            logger.error("Erro no serviço ao executar ciclo de análise do meta-agente", exc_info=e)
            raise MetaAgentServiceError("Falha ao executar o ciclo de análise.") from e

    def get_latest_report(self) -> Optional[StateReport]:
        logger.info("Buscando último relatório do meta-agente via serviço.")
        return self._get_agent().last_report

    async def start_heartbeat(self, interval_minutes: int) -> bool:
        logger.info("Iniciando heartbeat do meta-agente via serviço", interval_minutes=interval_minutes)
        agent = self._get_agent()
        if agent._heartbeat_task and not agent._heartbeat_task.done():
            logger.warning("Tentativa de iniciar um heartbeat já ativo.")
            return False  # Indica que já estava ativo

        await agent.start_heartbeat(interval_minutes=interval_minutes)
        return True

    def stop_heartbeat(self):
        logger.info("Parando heartbeat do meta-agente via serviço.")
        self._get_agent().stop_heartbeat()

    def get_heartbeat_status(self) -> Dict[str, Any]:
        logger.info("Buscando status do heartbeat do meta-agente.")
        agent = self._get_agent()
        is_active = agent._heartbeat_task is not None and not agent._heartbeat_task.done()
        return {
            "heartbeat_active": is_active,
            "total_cycles_executed": agent.cycle_count,
            "last_analysis": agent.last_report.timestamp.isoformat() if agent.last_report else None
        }

    def get_health_status(self) -> Dict[str, Any]:
        logger.info("Buscando status de saúde do meta-agente.")
        agent = self._get_agent()
        return {
            "status": "healthy",
            "agent_id": agent.agent_id,
            "executor_initialized": agent.executor is not None,
            "tools_count": len(agent.tools),
            "cycles_executed": agent.cycle_count
        }


# Instância única do serviço
meta_agent_service = MetaAgentService()


# Padrão de Injeção de Dependência: Getter para o serviço
def get_meta_agent_service() -> MetaAgentService:
    return meta_agent_service
