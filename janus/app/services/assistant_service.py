import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from app.services.llm_service import LLMService
from app.core.autonomy.goal_manager import Goal
from app.core.autonomy.policy_engine import PolicyEngine, PolicyConfig, RiskProfile, PolicyDecision
from app.core.autonomy.planner import build_plan_for_goal
from app.core.tools.action_module import action_registry

logger = structlog.get_logger(__name__)


@dataclass
class AssistantExecutionStep:
    tool: str
    args: Dict[str, Any]
    started_at: float
    ended_at: float
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


class AssistantService:
    """
    Serviço de orquestração automática de ferramentas a partir de uma solicitação do usuário.

    Fluxo: analisar pedido → planejar passos (ferramentas/args) → validar política → executar → consolidar resultados.
    """

    def __init__(self, llm_service: LLMService):
        self._llm = llm_service

    async def execute_request(
        self,
        user_request: str,
        risk_profile: str = RiskProfile.BALANCED,
        allowlist: Optional[List[str]] = None,
        blocklist: Optional[List[str]] = None,
        max_steps: int = 8,
        timeout_seconds: int = 30,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executa uma solicitação do usuário de ponta a ponta, sem exigir escolha manual de ferramentas.
        """
        # 1) Criar Goal a partir do pedido do usuário
        goal = Goal(id="ad-hoc", title=user_request.strip()[:80], description=user_request.strip())

        # 2) Configurar política
        policy = PolicyEngine(
            PolicyConfig(
                risk_profile=risk_profile or RiskProfile.BALANCED,
                allowlist=set(allowlist or []),
                blocklist=set(blocklist or []),
                max_actions_per_cycle=max_steps,
                max_seconds_per_cycle=max(20, timeout_seconds),
            )
        )

        # 3) Planejar passos com ORCHESTRATOR
        plan = await build_plan_for_goal(
            goal=goal,
            metrics=metrics or {},
            llm_service=self._llm,
            policy=policy,
            max_steps=max_steps,
            timeout_seconds=timeout_seconds,
        )

        # 4) Executar passos conforme política
        results: List[AssistantExecutionStep] = []
        transparent_steps: List[Dict[str, Any]] = []

        for step in plan:
            if not policy.can_continue_cycle():
                break
            tool_name = step.get("tool")
            args = step.get("args") or {}

            # Validação de política
            decision: PolicyDecision = policy.validate_tool_call(tool_name, args)
            transparent_steps.append({
                "tool": tool_name,
                "args": args,
                "allowed": decision.allowed,
                "require_confirmation": decision.require_confirmation,
                "reason": decision.reason,
            })

            if not decision.allowed:
                continue

            tool = action_registry.get_tool(tool_name)
            if not tool:
                continue

            # Execução e telemetria
            started = time.time()
            success = True
            out: Optional[str] = None
            err: Optional[str] = None
            try:
                # BaseTool pode suportar .invoke ou .run; preferimos .invoke no estilo LangChain
                # Alguns wrappers esperam dict: {"input": ...}. Usamos kwargs diretos.
                out = tool.run(**args) if hasattr(tool, "run") else tool.invoke(args)
            except Exception as e:
                success = False
                err = str(e)
                logger.error("Falha ao executar ferramenta", tool=tool_name, exc_info=True)
            ended = time.time()

            # Registra métricas e rate limit
            try:
                action_registry.record_call(
                    tool_name=tool_name,
                    duration=ended - started,
                    success=success,
                    error=err,
                    input_args=args,
                )
            except Exception:
                pass

            results.append(
                AssistantExecutionStep(
                    tool=tool_name,
                    args=args,
                    started_at=started,
                    ended_at=ended,
                    success=success,
                    output=str(out) if out is not None else None,
                    error=err,
                )
            )

        # 5) Resposta consolidada e transparente
        consolidated_output = self._consolidate_results(results)
        stats = action_registry.get_statistics()

        return {
            "request": user_request,
            "planned_steps": plan,
            "transparent": transparent_steps,
            "executions": [
                {
                    "tool": r.tool,
                    "args": r.args,
                    "success": r.success,
                    "duration_seconds": round(r.ended_at - r.started_at, 3),
                    "output": r.output,
                    "error": r.error,
                }
                for r in results
            ],
            "consolidated_output": consolidated_output,
            "telemetry": stats,
        }

    def _consolidate_results(self, steps: List[AssistantExecutionStep]) -> str:
        """Cria uma saída human-readable consolidada a partir dos resultados das ferramentas."""
        if not steps:
            return "Nenhuma ação executada."
        lines: List[str] = []
        for s in steps:
            status = "ok" if s.success else f"erro: {s.error}"
            snippet = (s.output or "").strip()
            if len(snippet) > 500:
                snippet = snippet[:500] + "..."
            lines.append(f"[{s.tool}] → {status}\n{snippet}")
        return "\n\n".join(lines)


# Padrão de Injeção de Dependência: Getter
from fastapi import Request

def get_assistant_service(request: Request) -> AssistantService:
    return request.app.state.assistant_service