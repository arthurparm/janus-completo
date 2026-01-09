from typing import Any

import structlog
from starlette.requests import Request

from app.core.agents.multi_agent_system import (
    AgentRole,
    MultiAgentSystem,
    Task,
    TaskPriority,
)
from app.core.infrastructure import AgentType

logger = structlog.get_logger(__name__)

# Global dictionary to hold circuit breaker instances for different agent types
# This needs to be initialized with actual CircuitBreaker instances as agents are created or registered.
agent_circuit_breakers: dict[AgentType, Any] = {}


class AgentManager:
    """
    Gerencia a criação e execução de diferentes tipos de agentes.
    """

    def __init__(self):
        logger.info("AgentManager inicializado.")
        self._system = MultiAgentSystem()

    def _map_type_to_role(self, agent_type: AgentType) -> AgentRole:
        """Mapeia AgentType (infra) para AgentRole (sistema multi-agente)."""
        mapping = {
            AgentType.ORCHESTRATOR: AgentRole.PROJECT_MANAGER,
            AgentType.TOOL_USER: AgentRole.RESEARCHER,  # Default to Researcher for tools
            AgentType.META_AGENT: AgentRole.OPTIMIZER,
            AgentType.REFLEXION_AGENT: AgentRole.TESTER,  # Or Tester/Optimizer
        }
        # Fallback inteligente
        if agent_type == AgentType.REFLEXION_AGENT:
            return AgentRole.OPTIMIZER
        return mapping.get(agent_type, AgentRole.PROJECT_MANAGER)

    async def arun_agent(
        self, question: str, agent_type: AgentType, request: Request
    ) -> dict[str, Any]:
        """
        Executa um agente especializado para responder a uma questão.
        """
        logger.info("Executando agente através do AgentManager", agent_type=agent_type.name)

        role = self._map_type_to_role(agent_type)

        # Cria ou recupera um agente para este papel
        # Nota: MultiAgentSystem.create_agent cria uma nova instância.
        # Para eficiência, poderíamos cachear, mas por enquanto vamos criar sob demanda
        # para garantir isolamento de contexto por request se necessário.
        agent = self._system.create_agent(role)

        task = Task(
            description=question,
            priority=TaskPriority.HIGH,
            metadata={"source": "api_request", "agent_type": agent_type.name},
        )

        # Registra a tarefa no workspace
        self._system.workspace.add_task(task)

        try:
            result = await agent.execute_task(task)

            return {
                "answer": result.get("result", ""),
                "intermediate_steps": [],  # Poderíamos extrair do result se disponível
                "task_id": task.id,
                "status": result.get("status"),
            }
        except Exception as e:
            logger.error(f"Erro na execução do agente: {e}", exc_info=True)
            return {
                "answer": f"Desculpe, ocorreu um erro ao processar sua solicitação: {e!s}",
                "intermediate_steps": [],
                "error": str(e),
            }

    def create_specialized_agent(self, role: AgentRole) -> dict[str, Any]:
        """Cria um agente especializado delegando ao MultiAgentSystem (config dinâmicas)."""
        agent = self._system.create_agent(role)
        return {"agent_id": agent.agent_id, "role": agent.role.value}

    def update_agent_config(self, agent_id: str, config: dict[str, Any]) -> bool:
        """Atualiza a configuração de um agente existente (via banco)."""
        return self._system.update_agent_config(agent_id, config)

    def list_agents(self) -> dict[str, Any]:
        """Lista agentes ativos e seus metadados."""
        return {"agents": self._system.list_agents()}

    def get_workspace_status(self) -> dict[str, Any]:
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
