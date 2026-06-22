---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/reflexion.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# reflexion

## Arquivos-fonte
- `backend/app/api/v1/endpoints/reflexion.py`

## Rotas
- `GET /config`
- `GET /health`
- `GET /summary/post_sprint`
- `POST /execute`
- `POST /reset-circuit-breaker`

## Dependências de código
- Serviços
  - `memory_service`
  - `meta_agent_service`
  - `reflexion_service`

## Símbolos
- class: `ReflexionRequest`
- class: `ReflexionResponse`
- class: `LessonItem`
- class: `PostSprintSummaryResponse`
- function: `execute_with_reflexion(request: ReflexionRequest, service: ReflexionService = Depends(get_reflexion_service))`
  - Delega a execução de uma tarefa com o ciclo de auto-otimização para o ReflexionService.
O tratamento de erros (Validação, Timeout, etc.) é feito pelo exception handler central.
- function: `get_reflexion_config(service: ReflexionService = Depends(get_reflexion_service))`
  - Retorna a configuração padrão do sistema Reflexion, via serviço.
- function: `reset_circuit_breaker(service: ReflexionService = Depends(get_reflexion_service))`
  - Delega o reset dos circuit breakers para o ReflexionService.
- function: `reflexion_health(service: ReflexionService = Depends(get_reflexion_service))`
  - Delega a verificação de saúde do módulo para o ReflexionService.
- function: `get_post_sprint_summary(limit: int = Query(10, ge=1, le=100, description='Limite de lições recentes'), timeframe_seconds: int = Query(3600, ge=60, le=86400, description='Janela de tempo em segundos para lições (padrão: 1 hora)'), min_score: float | None = Query(None, ge=0.0, description='Score mínimo das lições'), memory: MemoryService = Depends(get_memory_service), meta: MetaAgentService = Depends(get_meta_agent_service))`
  - Retorna um resumo pós-sprint com lições aprendidas recentes e o último relatório do Meta-Agente.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
