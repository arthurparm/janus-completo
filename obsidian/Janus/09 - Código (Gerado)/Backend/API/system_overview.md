---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/system_overview.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# system_overview

## Arquivos-fonte
- `backend/app/api/v1/endpoints/system_overview.py`

## Rotas
- `GET /overview`

## Dependências de código
- Serviços
  - `knowledge_service`
  - `llm_service`
  - `observability_service`
  - `optimization_service`
  - `system_status_service`

## Símbolos
- class: `SystemStatus`
- class: `ServiceHealthItem`
- class: `WorkerStatusResponse`
- class: `SystemOverviewResponse`
- function: `get_system_overview(request: Request, observability: ObservabilityService = Depends(get_observability_service), knowledge: KnowledgeService = Depends(get_knowledge_service), llm: LLMService = Depends(get_llm_service), optimization: OptimizationService = Depends(get_optimization_service))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
