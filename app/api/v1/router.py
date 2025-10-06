from fastapi import APIRouter

from .endpoints import system_status, knowledge, agent, memory, learning, tasks, context, sandbox, reflexion, tools, \
    optimization

api_router = APIRouter()

api_router.include_router(system_status.router, prefix="/system")
api_router.include_router(knowledge.router, prefix="/knowledge")
api_router.include_router(agent.router, prefix="/agent")
api_router.include_router(memory.router, prefix="/memory")
api_router.include_router(learning.router, prefix="/learning")
api_router.include_router(tasks.router, prefix="/tasks")  # Sprint 1: Task management
api_router.include_router(context.router, prefix="/context")  # Sprint 3: Environmental context
api_router.include_router(sandbox.router, prefix="/sandbox")  # Sprint 4: Python sandbox
api_router.include_router(reflexion.router, prefix="/reflexion")  # Sprint 5: Reflexion & self-optimization
api_router.include_router(tools.router, prefix="/tools")  # Sprint 6: Dynamic tool management
api_router.include_router(optimization.router, prefix="/optimization")  # Sprint 7: Proactive self-optimization
