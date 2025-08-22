from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings

router = APIRouter()

class StatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    status: str

@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Verifica o estado da aplicação",
    tags=["System"]
)
def get_system_status():
    """
    Retorna o status atual da aplicação, incluindo nome, versão e ambiente.
    Este endpoint é usado como um health check para monitoramento.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "OPERATIONAL"
    }
