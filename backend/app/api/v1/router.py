from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.workspace import router as workspace_router

from .endpoints import (
    admin_actions,
    admin_config,
    agent,
    assistant,
    auth_oidc,
    auto_analysis,
    autonomy,
    autonomy_admin,
    autonomy_history,
    chat,
    collaboration,
    context,
    deployment,
    documents,
    evaluation,
    feedback,
    governance,
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
    system_overview,
    system_status,
    tasks,
    tools,
    users,
    workers,
)

api_router = APIRouter()

# Route composition is intentionally policy-free. The canonical, operation-level
# manifest is applied only after every route has its final full path in app.main.
api_router.include_router(auth_oidc.router)

for source, prefix in (
    (agent.router, "/agent"),
    (assistant.router, ""),
    (documents.router, "/documents"),
    (pending_actions.router, ""),
    (productivity.router, ""),
    (profiles.router, ""),
    (rag.router, "/rag"),
    (memory.router, "/memory"),
    (evaluation.router, ""),
    (users.user_router, ""),
    (admin_actions.router, ""),
    (chat.router, "/chat"),
    (context.router, "/context"),
    (feedback.router, ""),
    (knowledge.router, "/knowledge"),
    (llm.router, "/llm"),
    (observability.router, "/observability"),
    (system_status.router, "/system"),
    (evaluation.control_router, ""),
    (workspace_router, ""),
    (admin_config.router, ""),
    (auto_analysis.router, "/auto-analysis"),
    (autonomy.router, "/autonomy"),
    (autonomy_admin.router, "/autonomy/admin"),
    (autonomy_history.router, "/autonomy/history"),
    (collaboration.router, "/collaboration"),
    (deployment.router, ""),
    (governance.router, "/governance"),
    (learning.router, "/learning"),
    (meta_agent.router, "/meta-agent"),
    (optimization.router, "/optimization"),
    (system_overview.router, "/system"),
    (tasks.router, "/tasks"),
    (tools.router, "/tools"),
    (users.router, ""),
    (workers.router, "/workers"),
    (reflexion.router, "/reflexion"),
):
    api_router.include_router(source, prefix=prefix)
