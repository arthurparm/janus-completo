from fastapi import APIRouter

# Adiciona o novo endpoint de learning
from .endpoints import system_status, knowledge, agent, memory, learning

api_router = APIRouter()

api_router.include_router(system_status.router, prefix="/system")

api_router.include_router(knowledge.router, prefix="/knowledge")

api_router.include_router(agent.router, prefix="/agent")

api_router.include_router(memory.router, prefix="/memory")

# Inclui as novas rotas de aprendizagem
api_router.include_router(learning.router, prefix="/learning")