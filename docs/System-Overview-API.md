# Endpoint Agregado: System Overview

Proposta de contrato para otimizar o carregamento inicial do painel, consolidando múltiplas chamadas em um único endpoint.

- Path: `/api/v1/system/overview`
- Method: `GET`
- Auth: opcional (se presente, usar `Authorization: Bearer <token>`)
- Cache: curto (ex.: `Cache-Control: max-age=60` via API; SW configurado com freshness)

## Objetivo
Retornar, em uma única resposta:
- Health geral da API
- Status do sistema (app, versão, ambiente, uptime)
- Saúde dos serviços (LLM, observabilidade, etc.)
- Estado dos workers (running/done/cancelled/exception)

## Response 200 (OK)
```json
{
  "health": { "status": "ok", "timestamp": "2025-10-24T16:00:00Z" },
  "system": {
    "app_name": "Janus",
    "version": "1.0.0",
    "environment": "development",
    "status": "ok",
    "uptime_seconds": 12345
  },
  "services": {
    "services": [
      { "name": "llm", "status": "ok", "metric_text": "latência 120ms" },
      { "name": "observability", "status": "ok" }
    ]
  },
  "workers": {
    "workers": [
      { "name": "ingestor", "running": true, "done": false, "cancelled": false },
      { "name": "indexer", "running": false, "done": true, "cancelled": false }
    ]
  }
}
```

### Tipos (esquema conceitual)
- `health.status`: enum `ok | unknown | degraded`
- `system`: segue `SystemStatus` atual (campos Pydantic existentes)
- `services.services[]`: lista de `ServiceHealthItem`
- `workers.workers[]`: lista de `WorkersStatusItem`

## Response 503 (Service Unavailable)
Quando algum subsistema crítico falhar:
```json
{
  "status": 503,
  "title": "Subsystem unavailable",
  "detail": "LLM provider timed out",
  "type": "about:blank"
}
```

## Considerações de Implementação (FastAPI)
- Rota: `@router.get("/api/v1/system/overview", response_model=SystemOverviewResponse)`
- Internamente, usar `asyncio.gather` para paralelizar chamadas a serviços existentes:
  - `/api/v1/health`
  - `/api/v1/system/status`
  - `/api/v1/observability/health/system`
  - `/api/v1/workers/status`
- Propagar `Authorization` se presente; não exigir autenticação para leitura básica
- Retornar `Cache-Control` curto no cabeçalho

## Benefícios
- Reduz 3–4 roundtrips na renderização do Dashboard
- Padroniza contrato agregado e simplifica o frontend (possível uso na GlobalStateStore)
- Facilita monitoramento e retries em um único ponto

## Próximos Passos
- Aprovar contrato no backend e implementar `SystemOverviewResponse`
- Integrar no frontend (GlobalStateStore: `loadOverview()` pode usar endpoint agregado quando disponível)