import structlog
import asyncio  # Added asyncio import
from typing import Dict, Any
from starlette.requests import Request

from app.core.infrastructure import AgentType
from app.core.agents.multi_agent_system import MultiAgentSystem, AgentRole

logger = structlog.get_logger(__name__)

# Global dictionary to hold circuit breaker instances for different agent types
# This needs to be initialized with actual CircuitBreaker instances as agents are created or registered.
agent_circuit_breakers: Dict[AgentType, Any] = {}

class AgentManager:
    """
    Gerencia a criação e execução de diferentes tipos de agentes.
    """
    def __init__(self):
        logger.info("AgentManager inicializado.")
        self._system = MultiAgentSystem()

    async def arun_agent(
            self,
            question: str,
            agent_type: AgentType,
            request: Request
    ) -> Dict[str, Any]:
        """
        Ponto de entrada para executar um agente.
        A lógica específica para cada tipo de agente seria chamada aqui.
        """
        logger.info("Executando agente através do AgentManager", agent_type=agent_type.name)
        await asyncio.sleep(0.1)
        return {
            "answer": f"Resposta do agente {agent_type.name} para a pergunta: '{question}'",
            "intermediate_steps": []
        }

    def create_specialized_agent(self, role: AgentRole) -> Dict[str, Any]:
        """Cria um agente especializado delegando ao MultiAgentSystem (config dinâmicas)."""
        agent = self._system.create_agent(role)
        return {
            "agent_id": agent.agent_id,
            "role": agent.role.value
        }

    def update_agent_config(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """Atualiza a configuração de um agente existente (via banco)."""
        return self._system.update_agent_config(agent_id, config)

    def list_agents(self) -> Dict[str, Any]:
        """Lista agentes ativos e seus metadados."""
        return {"agents": self._system.list_agents()}

    def get_workspace_status(self) -> Dict[str, Any]:
        """Retorna status do workspace compartilhado."""
        return self._system.get_workspace_status()

    def reset_circuit_breaker(self):
        """
        Reseta os circuit breakers dos agentes.
        Clears the global agent_circuit_breakers dictionary.
        """
        logger.info("Resetando circuit breakers no AgentManager.")
        global agent_circuit_breakers
        agent_circuit_breakers.clear()


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_agent_manager_instance: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    """Função getter para injeção de dependência."""
    global _agent_manager_instance
    if _agent_manager_instance is None:
        _agent_manager_instance = AgentManager()
    return _agent_manager_instance


# --- Compatibilidade com código legado ---
agent_manager = get_agent_manager()
