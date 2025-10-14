import structlog
from dataclasses import asdict
from typing import Dict, Any, Optional
from fastapi import Request

from app.repositories.reflexion_repository import ReflexionRepository, ReflexionRepositoryError
from app.core.optimization import ReflexionConfig

logger = structlog.get_logger(__name__)

# --- Custom Service-Layer Exceptions ---

class ReflexionServiceError(Exception):
    """Base exception for reflexion service errors."""
    pass

class ReflexionValidationError(ReflexionServiceError):
    """Raised for validation errors."""
    pass

class ReflexionTimeoutError(ReflexionServiceError):
    """Raised on execution timeout."""
    pass

# --- Reflexion Service ---

class ReflexionService:
    """
    Camada de serviço para o ciclo de auto-otimização Reflexion.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: ReflexionRepository):
        self._repo = repo

    async def run_reflexion_cycle(self, task: str, config_overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orquestra a execução de uma tarefa com o ciclo completo de Reflexion.
        """
        logger.info("Orquestrando ciclo de Reflexion via serviço", task=task)
        try:
            config = ReflexionConfig.from_settings()
            for key, value in config_overrides.items():
                if value is not None:
                    setattr(config, key, value)

            result = await self._repo.run_cycle(task=task, config=config)

            result["steps"] = [asdict(step) for step in result.get("steps", [])]
            result["iterations"] = len(result["steps"])

            logger.info("Ciclo de Reflexion orquestrado com sucesso", success=result["success"],
                        score=result["best_score"])
            return result
        except ValueError as e:
            raise ReflexionValidationError(str(e)) from e
        except TimeoutError as e:
            raise ReflexionTimeoutError(str(e)) from e
        except ReflexionRepositoryError as e:
            logger.error("Erro no repositório de Reflexion", exc_info=e)
            raise ReflexionServiceError("Ocorreu uma falha na camada de execução do ciclo de Reflexion.") from e
        except Exception as e:
            logger.error("Erro inesperado no serviço de Reflexion", exc_info=e)
            raise ReflexionServiceError("Ocorreu uma falha inesperada no serviço de Reflexion.") from e

    def get_config(self) -> ReflexionConfig:
        return ReflexionConfig.from_settings()

    def reset_agent_breakers(self):
        logger.info("Orquestrando reset dos circuit breakers via serviço.")
        self._repo.reset_breakers()

    def get_health_status(self) -> Dict[str, Any]:
        logger.info("Buscando saúde do módulo Reflexion via serviço.")
        return self._repo.get_health()

# Padrão de Injeção de Dependência: Getter para o serviço
def get_reflexion_service(request: Request) -> ReflexionService:
    return request.app.state.reflexion_service
