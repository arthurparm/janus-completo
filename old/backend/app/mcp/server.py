"""Servidor MCP local de manutencao do Janus.

Expoe, via Model Context Protocol (stdio), introspecao sobre metas, autoestudo
e maturidade de autonomia para clientes MCP de confianca (ex.: Claude Code
rodando localmente). Nao e montado na API HTTP e nao passa pelo
SecurityContainmentMiddleware nem pelo endpoint_policy_manifest: roda como
processo local com o mesmo nivel de confianca dos scripts em tooling/, que ja
acessam o banco diretamente sem autenticacao HTTP.

A unica ferramenta de escrita e `propose_goal`, que cria uma meta com
source="mcp". Como em qualquer outra origem, criar uma meta nao autoriza
executa-la (ver invariante 3 em documentation/janus-project-philosophy.md).

Execucao local (a partir da raiz do repo):
    uv run --python 3.12 --with-requirements backend/requirements.txt \
        --with mcp python -m app.mcp.server
(rodar com PYTHONPATH=backend ou cwd=backend para resolver o pacote `app`)

Limitacao conhecida: o estado do agendador (SchedulerService) vive apenas em
memoria dentro do processo da API; este servidor, rodando em processo
separado, nao consegue le-lo. Use o endpoint HTTP
GET /api/v1/autonomy/admin/scheduler/jobs para isso.
"""

from __future__ import annotations

from typing import Any

import structlog
from mcp.server.fastmcp import FastMCP

from app.core.autonomy.goal_manager import GoalManager
from app.repositories.autonomy_admin_repository import AutonomyAdminRepository

logger = structlog.get_logger(__name__)

mcp = FastMCP(
    "janus-maintenance",
    instructions=(
        "Ferramentas de introspeccao e manutencao do Janus: metas ativas, "
        "estado de autoestudo e pontuacao de maturidade de autonomia. Leitura "
        "direta do banco local; nao substitui a API HTTP autenticada e nao "
        "executa acoes fora do que as ferramentas descrevem explicitamente."
    ),
)


def _goal_manager() -> GoalManager:
    return GoalManager(memory_service=None)


def _admin_repo() -> AutonomyAdminRepository:
    return AutonomyAdminRepository()


@mcp.tool()
def list_active_goals(status: str | None = None) -> list[dict[str, Any]]:
    """Lista metas ativas (pending/in_progress) do Janus. Filtra por status se informado."""
    goals = _goal_manager().list_goals(status=status)
    return [g.to_dict() for g in goals]


@mcp.tool()
def get_goal(goal_id: str) -> dict[str, Any] | None:
    """Retorna uma meta pelo id, incluindo metas ja terminais (completed/failed)."""
    goal = _goal_manager().get_goal(goal_id)
    return goal.to_dict() if goal else None


@mcp.tool()
def propose_goal(
    title: str,
    description: str,
    priority: int = 5,
    success_criteria: str | None = None,
) -> dict[str, Any]:
    """Propoe uma nova meta para o Janus (fonte "mcp"). Nao autoriza execucao da meta."""
    goal = _goal_manager().create_goal(
        title=title,
        description=description,
        priority=priority,
        success_criteria=success_criteria,
        source="mcp",
    )
    logger.info("mcp_goal_proposed", goal_id=goal.id, title=goal.title)
    return goal.to_dict()


@mcp.tool()
def get_self_study_status() -> dict[str, Any]:
    """Estado atual do autoestudo: ultimo commit estudado, run em andamento e runs recentes."""
    repo = _admin_repo()
    state = repo.get_self_study_state()
    running = repo.get_latest_running_self_study()
    runs = repo.list_self_study_runs(limit=5)
    return {
        "last_studied_commit": state.last_studied_commit,
        "last_success_at": state.last_success_at.isoformat() if state.last_success_at else None,
        "running": (
            {"id": running.id, "status": running.status, "mode": running.mode}
            if running
            else None
        ),
        "recent_runs": [
            {
                "id": r.id,
                "status": r.status,
                "mode": r.mode,
                "files_processed": r.files_processed,
                "files_total": r.files_total,
            }
            for r in runs
        ],
    }


@mcp.tool()
def list_self_study_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Lista runs de autoestudo, do mais recente ao mais antigo (sem o detalhe por arquivo)."""
    limit = max(1, min(limit, 200))
    runs = _admin_repo().list_self_study_runs(limit=limit)
    return [
        {
            "id": r.id,
            "trigger_type": r.trigger_type,
            "mode": r.mode,
            "status": r.status,
            "files_total": r.files_total,
            "files_processed": r.files_processed,
            "error": r.error,
            "base_commit": r.base_commit,
            "target_commit": r.target_commit,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ]


@mcp.tool()
async def get_autonomy_maturity() -> dict[str, Any]:
    """Pontuacao de maturidade de autonomia com base nos modulos e documentos implementados."""
    from app.api.v1.endpoints.autonomy import get_autonomy_maturity as compute_maturity

    return await compute_maturity(request=None)  # type: ignore[arg-type]


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
