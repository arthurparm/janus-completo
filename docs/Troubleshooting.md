# Troubleshooting

Guia de diagnóstico e resolução de problemas comuns.

## Infra e Conexões

- RabbitMQ indisponível
  - Verifique `RABBITMQ_HOST/PORT/USER/PASSWORD/VHOST` no `.env`.
  - UI em `http://localhost:15672`; confira se a fila `janus.neural.training` existe.
  - Veja `app/core/infrastructure/message_broker.py` para política de filas.

- Neo4j/Qdrant
  - Neo4j Browser: `http://localhost:7474` (credenciais do `.env`).
  - Qdrant health: `http://localhost:6333/healthz`.
  - Ajuste recursos Docker Desktop (memória/CPU) se reinícios ocorrerem.

## LLMs e Orçamentos

- Chaves ausentes (OpenAI/Gemini) — defina `OPENAI_API_KEY`/`GEMINI_API_KEY`.
- Fallback: Ollama local (`OLLAMA_HOST`) com modelos configurados.
- Rate limit/budgets: aumente `RATE_LIMIT_*` e ajuste `LLM_BUDGETS_JSON`.

## Treinamento e Dataset

- `training/status` não avança
  - Cheque logs do worker: `docker compose logs -f janus-api` e do serviço de treino.
  - Confirme publicação na fila `janus.neural.training`.
  - Revise `neural_training_worker.py` e `neural_training_system.py`.

- Dataset vazio
  - Execute `POST /api/v1/learning/harvest`.
  - Use `GET /api/v1/learning/dataset/preview?limit=5` para ver amostras.

## Portas e Ambiente

- Conflito de portas — ajuste mapeamentos no `docker-compose.yml`.
- Windows: certifique-se de que Docker Desktop tem WSL2 habilitado.

## Observabilidade

- Métricas: `GET /metrics`.
- Health: `GET /healthz`, `GET /readyz`.
- Dashboard Grafana: importe `dashboards/janus_component_resilience_dashboard.json`.

## Comandos Úteis

- `docker compose ps`
- `docker compose logs -f janus-api`
- `docker compose logs -f neo4j`
- `docker compose logs -f qdrant`
- `docker compose logs -f ollama`

## Quando Abrir Issue

- Erros repetidos em provedores LLM mesmo com chaves válidas.
- Falhas de conexão persistentes a bancos ou filas após verificar credenciais.
- Circuit Breakers abertos por longos períodos (veja métricas e logs).

## Problemas Específicos da 1.0.0

- SyntaxError em f-strings (Code Agent)
  - Erro: `SyntaxError: f-string expression part cannot include a backslash`.
  - Causa: uso de `\n` dentro da expressão do f-string.
  - Fix: pré-calcular `lines_count = code.count("\n") + 1` e usar `f"lines={lines_count}"`.
  - Após ajustar, reinicie a API: `docker compose restart janus-api`.

- Fila de consolidação com `consumers=0`
  - Verifique a fila: `GET /api/v1/tasks/queue/janus.knowledge.consolidation`.
  - Inicie os workers: `POST /api/v1/workers/start-all`.
  - Confirme que há consumo: `consumers > 0` e `messages` reduzindo.

- Qdrant: `400 Bad Request` em JSON body (IDs inválidos)
  - Causa: IDs de pontos devem ser `UUID` ou `unsigned integer`.
  - Ajuste o payload para usar IDs válidos.
  - Cheque saúde: `http://localhost:6333/healthz`.