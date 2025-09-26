from fastapi import APIRouter

from .endpoints import system_status, knowledge, agent, memory, learning

api_router = APIRouter()

api_router.include_router(system_status.router, prefix="/system")
api_router.include_router(knowledge.router, prefix="/knowledge")
api_router.include_router(agent.router, prefix="/agent")
api_router.include_router(memory.router, prefix="/memory")
api_router.include_router(learning.router, prefix="/learning")
