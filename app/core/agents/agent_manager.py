import structlog
import asyncio  # Added asyncio import
from typing import Dict, Any
from starlette.requests import Request

from app.core.infrastructure import AgentType

# Assuming CircuitBreaker is defined elsewhere or will be defined.
# For now, we'll use a placeholder for its type if it's not directly available.
# from app.core.infrastructure.circuit_breaker import CircuitBreaker # Uncomment if CircuitBreaker is in this path

logger = structlog.get_logger(__name__)

# Global dictionary to hold circuit breaker instances for different agent types
# This needs to be initialized with actual CircuitBreaker instances as agents are created or registered.
agent_circuit_breakers: Dict[AgentType, Any] = {}

class AgentManager:
    """
    Gerencia a criação e execução de diferentes tipos de agentes.
    """
    def __init__(self):
        # A lógica de inicialização dos agentes, caches, etc., viria aqui.
        logger.info("AgentManager inicializado.")

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
        # Simulação de uma execução de agente
        await asyncio.sleep(0.1)
        return {
            "answer": f"Resposta do agente {agent_type.name} para a pergunta: '{question}'",
            "intermediate_steps": []
        }

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
