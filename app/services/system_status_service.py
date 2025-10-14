import structlog
from typing import Dict, Any

from app.config import settings

logger = structlog.get_logger(__name__)


class SystemStatusService:
    """
    Camada de serviço para obter o status e a saúde geral da aplicação.
    """

    def get_system_status(self) -> Dict[str, Any]:
        """
        Coleta e retorna informações de status da aplicação.
        
        No futuro, pode ser expandido para incluir health checks de dependências.
        """
        logger.info("Coletando status do sistema.")
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "OPERATIONAL"  # Status estático por enquanto
        }


# Instância única do serviço
system_status_service = SystemStatusService()
