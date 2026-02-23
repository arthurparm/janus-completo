# Async Operational SLO (Janus)

Data de referência: 2026-02-12  
Ambiente: `docker compose` local (`janus_api` em `http://localhost:8000`)

## Objetivo
Validar robustez do fluxo assíncrono em cenário real:
- carga concorrente de chat/pending/meta-agent
- falha controlada de backend (`postgres`) com degradação esperada
- recuperação automática dentro de janela-alvo

## SLOs adotados
- `load_error_rate_max_percent`: `<= 5.0%`
- `load_p95_latency_ms_max`: `<= 8000ms`
- `chat_p95_latency_ms_max`: `<= 15000ms`
- `pending_p95_latency_ms_max`: `<= 3000ms`
- `chaos_recovery_seconds_max`: `<= 90s`

## Execução padrão
```bash
python tooling/async_ops_validation.py \
  --base-url http://localhost:8000 \
  --users 10 \
  --timeout 45 \
  --chaos-timeout 90
```

Relatório gerado em:
- `outputs/qa/async_ops_validation_report.json`

## Resultado de referência (2026-02-12)
- `load_error_rate_percent`: `0.0%`
- `load_p95_latency_ms`: `6887.86ms`
- `chat_p95_latency_ms`: `7155.51ms`
- `pending_p95_latency_ms`: `58.08ms`
- `chaos_recovery_seconds`: `0.52s`
- Veredito: `PASS`

## Critérios de aceite (Go/No-Go)
- Go:
  - Todos os SLOs acima atendidos
  - Durante queda de `postgres`, `pending_actions` e `chat/health` degradam para `503`
  - Após retorno do `postgres`, endpoints voltam para `200` dentro do limite
- No-Go:
  - qualquer SLO rompido
  - erro `500` em rota que deveria degradar com `503`
  - não recuperação dentro da janela definida
