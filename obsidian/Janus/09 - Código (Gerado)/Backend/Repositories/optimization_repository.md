---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/optimization_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# optimization_repository

## Arquivos-fonte
- `backend/app/repositories/optimization_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/optimization_service.py`

## Símbolos
- class: `OptimizationRepositoryError`
  - Base exception for optimization repository errors.
- class: `OptimizationRepository`
  - Camada de Repositório para o ciclo de auto-otimização proativa.
Abstrai todas as interações diretas com a infraestrutura de otimização.
- method: `OptimizationRepository.run_cycle(self, enable_auto_execution: bool = True, max_improvements: int | None = None)` -> `dict[str, Any]`
  - Executa o ciclo de otimização através da infraestrutura core.
- method: `OptimizationRepository.get_metrics(self)` -> `SystemMetrics`
  - Coleta as métricas de saúde atuais do sistema.
- method: `OptimizationRepository.get_health_score(self, metrics: SystemMetrics)` -> `float`
  - Calcula o score de saúde a partir das métricas.
- method: `OptimizationRepository.find_issues(self)` -> `list[DetectedIssue]`
  - Detecta problemas no sistema a partir das métricas.
- method: `OptimizationRepository.get_metrics_history(self)` -> `list[SystemMetrics]`
  - Retorna o histórico de métricas.
- method: `OptimizationRepository.get_status(self)` -> `dict[str, Any]`
  - Retorna o status de execução do ciclo contínuo.
- function: `get_optimization_repository()` -> `OptimizationRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
