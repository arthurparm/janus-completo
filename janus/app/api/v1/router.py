from fastapi import APIRouter

from app.api.v1.endpoints.workspace import router as workspace_router
from app.config import settings  # Added settings for feature flag

from .endpoints import (
    agent,
    assistant,
    auth,
    auto_analysis,
    autonomy,
    autonomy_history,
    chat,
    collaboration,
    consents,
    context,
    deployment,
    documents,
    evaluation,
    feedback,
    knowledge,
    learning,
    llm,
    memory,
    meta_agent,
    observability,
    optimization,
    pending_actions,
    productivity,
    profiles,
    rag,
    reflexion,
    sandbox,
    system_overview,
    system_status,
    tasks,
    tools,
    users,
    workers,
)

api_router = APIRouter()

if getattr(settings, "PUBLIC_API_MINIMAL", False):
    # Minimal public API: expose only chat and autonomy endpoints
    api_router.include_router(chat.router, prefix="/chat")
    api_router.include_router(users.router)
    api_router.include_router(profiles.router)
    api_router.include_router(autonomy.router, prefix="/autonomy")  # Autonomy Loop & Goals
    api_router.include_router(assistant.router)
    api_router.include_router(autonomy_history.router, prefix="/autonomy/history")
    api_router.include_router(consents.router)
    api_router.include_router(pending_actions.router)
    api_router.include_router(evaluation.router)
    api_router.include_router(deployment.router)
    api_router.include_router(auth.router)
    api_router.include_router(auto_analysis.router, prefix="/auto-analysis")  # Auto-análise simples
    api_router.include_router(feedback.router)  # Quick Win: Feedback loop
else:
    # Full API: expose all internal and public endpoints
    api_router.include_router(workspace_router)

    api_router.include_router(system_status.router, prefix="/system")
    api_router.include_router(system_overview.router, prefix="/system")
    api_router.include_router(knowledge.router, prefix="/knowledge")
    api_router.include_router(rag.router, prefix="/rag")
    api_router.include_router(documents.router, prefix="/documents")
    api_router.include_router(productivity.router)
    api_router.include_router(agent.router, prefix="/agent")
    api_router.include_router(memory.router, prefix="/memory")
    api_router.include_router(learning.router, prefix="/learning")
    api_router.include_router(tasks.router, prefix="/tasks")  # Sprint 1: Task management
    api_router.include_router(context.router, prefix="/context")  # Sprint 3: Environmental context
    api_router.include_router(sandbox.router, prefix="/sandbox")  # Sprint 4: Python sandbox
    api_router.include_router(
        reflexion.router, prefix="/reflexion"
    )  # Sprint 5: Reflexion & self-optimization
    api_router.include_router(tools.router, prefix="/tools")  # Sprint 6: Dynamic tool management
    api_router.include_router(
        optimization.router, prefix="/optimization"
    )  # Sprint 7: Proactive self-optimization
    api_router.include_router(llm.router, prefix="/llm")  # Sprint 10: Hybrid Brain & LLM resilience
    api_router.include_router(
        collaboration.router, prefix="/collaboration"
    )  # Sprint 11: Multi-agent collaboration
    api_router.include_router(
        observability.router, prefix="/observability"
    )  # Sprint 12: Resilience & observability
    api_router.include_router(
        meta_agent.router, prefix="/meta-agent"
    )  # Sprint 13: Meta-Agent proactive consciousness
    api_router.include_router(chat.router, prefix="/chat")
    api_router.include_router(users.router)
    api_router.include_router(profiles.router)
    api_router.include_router(autonomy.router, prefix="/autonomy")  # Autonomy Loop & Goals
    api_router.include_router(workers.router, prefix="/workers")  # Workers orchestration controls
    api_router.include_router(assistant.router)
    api_router.include_router(productivity.router)
    api_router.include_router(autonomy_history.router, prefix="/autonomy/history")
    api_router.include_router(consents.router)
    api_router.include_router(pending_actions.router)
    api_router.include_router(evaluation.router)
    api_router.include_router(deployment.router)
    api_router.include_router(auth.router)
    api_router.include_router(
        auto_analysis.router, prefix="/auto-analysis"
    )  # Auto-análise do sistema
    api_router.include_router(feedback.router)  # Quick Win: Feedback loop
