---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/optimization.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# optimization

## Arquivos-fonte
- `backend/app/api/v1/endpoints/optimization.py`

## Rotas
- `GET /health`
- `GET /issues`
- `GET /metrics/history`
- `GET /status`
- `POST /analyze`
- `POST /run-cycle`

## Dependências de código
- Serviços
  - `optimization_service`

## Símbolos
- class: `OptimizationCycleRequest`
- class: `OptimizationCycleResponse`
- class: `SystemHealthResponse`
- class: `DetectedIssueResponse`
- class: `SystemAnalysisResponse`
- function: `run_optimization_cycle(request: OptimizationCycleRequest, service: OptimizationService = Depends(get_optimization_service))`
  - Delega a execução do ciclo de auto-otimização para o OptimizationService.
- function: `get_system_health(service: OptimizationService = Depends(get_optimization_service))`
  - Delega a coleta de métricas de saúde para o OptimizationService.
- function: `get_detected_issues(service: OptimizationService = Depends(get_optimization_service), severity: str | None = None, category: str | None = None)`
  - Delega a detecção e filtragem de problemas para o OptimizationService.
- function: `get_metrics_history(limit: int = 20, service: OptimizationService = Depends(get_optimization_service))`
  - Delega a busca do histórico de métricas para o OptimizationService.
- function: `get_optimization_status(service: OptimizationService = Depends(get_optimization_service))`
  - Delega a busca de status do módulo para o OptimizationService.
- function: `analyze_system(analysis_type: str = 'performance', detailed: bool = True, service: OptimizationService = Depends(get_optimization_service))`
  - Delega a análise agregada do sistema para o OptimizationService.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
