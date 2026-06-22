---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/llm.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# llm

## Arquivos-fonte
- `backend/app/api/v1/endpoints/llm.py`

## Rotas
- `GET /budget/summary`
- `GET /cache/status`
- `GET /circuit-breakers`
- `GET /health`
- `GET /pricing/providers`
- `GET /providers`
- `GET /response-cache/status`
- `POST /ab/set-experiment`
- `POST /cache/invalidate`
- `POST /circuit-breakers/{provider}/reset`
- `POST /invoke`
- `POST /response-cache/invalidate`

## Dependências de código
- Serviços
  - `llm_service`

## Símbolos
- class: `LLMInvokeRequest`
- class: `LLMInvokeResponse`
- class: `LLMCacheStatusResponse`
- class: `CircuitBreakerStatus`
- class: `InvalidateResponseCacheRequest`
- function: `invoke_llm(request: LLMInvokeRequest, http_request: Request)`
  - Delega a invocação de um LLM para o LLMService.
- function: `get_cache_status(service: LLMService = Depends(get_llm_service))`
  - Delega a busca do status do cache para o LLMService.
- function: `invalidate_llm_cache(provider: str | None = None, service: LLMService = Depends(get_llm_service))`
  - Delega a invalidação do cache para o LLMService.
- function: `get_response_cache_status(service: LLMService = Depends(get_llm_service))`
  - Retorna apenas entradas do cache de respostas.
- function: `invalidate_response_cache(request: InvalidateResponseCacheRequest, service: LLMService = Depends(get_llm_service))`
  - Invalida entradas do cache de respostas conforme filtros fornecidos.
- function: `get_circuit_breaker_status(service: LLMService = Depends(get_llm_service))`
  - Delega a busca do status dos circuit breakers para o LLMService.
- function: `reset_circuit_breaker(provider: str, service: LLMService = Depends(get_llm_service))`
  - Delega o reset do circuit breaker para o LLMService.
- function: `list_llm_providers(service: LLMService = Depends(get_llm_service))`
  - Retorna os provedores configurados com seus modelos e estado de habilitação.
- function: `llm_health(service: LLMService = Depends(get_llm_service))`
  - Delega a verificação de saúde para o LLMService.
- class: `ABExperimentSetRequest`
- function: `set_ab_experiment(req: ABExperimentSetRequest)`
- function: `get_budget_summary()`
  - Retorna resumo de budget e gastos por provedor.
- function: `get_provider_pricing()`
  - Retorna tabela de preços por provedor (USD por 1K tokens).

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
