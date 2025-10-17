from fastapi import APIRouter

from .endpoints import system_status, knowledge, agent, memory, learning, tasks, context, sandbox, reflexion, tools, \
    optimization, llm, collaboration, observability, meta_agent, chat

api_router = APIRouter()
from app.api.v1.endpoints.workspace import router as workspace_router  # noqa: E402

api_router.include_router(workspace_router)

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
api_router.include_router(llm.router, prefix="/llm")  # Sprint 10: Hybrid Brain & LLM resilience
api_router.include_router(collaboration.router, prefix="/collaboration")  # Sprint 11: Multi-agent collaboration
api_router.include_router(observability.router, prefix="/observability")  # Sprint 12: Resilience & observability
api_router.include_router(meta_agent.router, prefix="/meta-agent")  # Sprint 13: Meta-Agent proactive consciousness
api_router.include_router(chat.router, prefix="/chat")  # Chat conversations
