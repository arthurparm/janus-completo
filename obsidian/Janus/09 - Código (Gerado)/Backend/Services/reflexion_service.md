---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/reflexion_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# reflexion_service

## Arquivos-fonte
- `backend/app/services/reflexion_service.py`

## Dependências de código
- Repositórios
  - `reflexion_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/reflexion.py`
- `backend/app/core/kernel.py`
- `backend/app/core/workers/reflexion_worker.py`

## Símbolos
- class: `ReflexionServiceError`
  - Base exception for reflexion service errors.
- class: `ReflexionValidationError`
  - Raised for validation errors.
- class: `ReflexionTimeoutError`
  - Raised on execution timeout.
- class: `ReflexionService`
  - Camada de servico para o ciclo de auto-otimizacao Reflexion.
- method: `ReflexionService.__init__(self, repo: ReflexionRepository)`
- method: `ReflexionService._normalize_step(step: Any, position: int)` -> `dict[str, Any]`
  - Normaliza formatos heterogeneos de step para contrato de API estavel.
- method: `ReflexionService._compute_dynamic_success_threshold(self, base: float)` -> `float`
  - Ajusta dinamicamente o success_threshold com base em metricas historicas.
- method: `ReflexionService.run_reflexion_cycle(self, task: str, config_overrides: dict[str, Any])` -> `dict[str, Any]`
  - Orquestra a execucao de uma tarefa com o ciclo completo de Reflexion.
- method: `ReflexionService.get_config(self)` -> `ReflexionConfig`
- method: `ReflexionService.reset_agent_breakers(self)`
- method: `ReflexionService.get_health_status(self)` -> `dict[str, Any]`
- function: `get_reflexion_service(request: Request)` -> `ReflexionService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
