from fastapi import APIRouter
from .endpoints import system_status

api_router = APIRouter()

# Inclui os endpoints do módulo system_status
api_router.include_router(system_status.router, prefix="/system")
