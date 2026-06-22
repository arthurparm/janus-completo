---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/optimization_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# optimization_service

## Arquivos-fonte
- `backend/app/services/optimization_service.py`

## Dependências de código
- Repositórios
  - `optimization_repository`
  - `prompt_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/optimization.py`
- `backend/app/api/v1/endpoints/system_overview.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/core/kernel.py`
- `backend/app/services/autonomy_service.py`

## Símbolos
- class: `OptimizationServiceError`
  - Base exception for optimization service errors.
- class: `OptimizationService`
  - Camada de serviço para o ciclo de auto-otimização proativa.
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `OptimizationService.__init__(self, repo: OptimizationRepository)`
- method: `OptimizationService.run_optimization_cycle(self, enable_auto_execution: bool, max_improvements: int | None)` -> `dict[str, Any]`
- method: `OptimizationService.get_system_health(self)` -> `dict[str, Any]`
- method: `OptimizationService.get_detected_issues(self, severity: str | None, category: str | None)` -> `list[DetectedIssue]`
- method: `OptimizationService.get_metrics_history(self, limit: int)` -> `list[SystemMetrics]`
- method: `OptimizationService.get_status(self)` -> `dict[str, Any]`
- method: `OptimizationService.analyze_system(self, analysis_type: str, detailed: bool)` -> `dict[str, Any]`
  - Gera análise agregada do sistema a partir de métricas e issues.
- method: `OptimizationService.update_agent_prompt(self, role: AgentRole, content: str, *, name: str | None = None, language: str | None = None, tags: list[str] | None = None, metadata: dict[str, Any] | None = None, activate: bool = True)` -> `dict[str, Any]`
  - Cria nova versão de prompt para um agente e ativa opcionalmente.
Deriva `name` de `role` quando ausente e usa o repositório de prompts.
- function: `get_optimization_service(request: Request)` -> `OptimizationService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
