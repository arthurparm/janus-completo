# Uso (Janus 1.0.0)

Este guia cobre o fluxo de Autonomia do Janus (batimento contínuo), metas (objetivos) e o Planejador Proativo (ORCHESTRATOR).

## Autonomia (Heartbeat)
- Endpoint para iniciar: `POST /api/v1/autonomy/start`
- Endpoint para parar: `POST /api/v1/autonomy/stop`
- Status do loop: `GET /api/v1/autonomy/status`

Ao iniciar sem um plano explícito, o loop usa um Planejador Proativo que consulta o ORCHESTRATOR para gerar um plano de passos com base nas metas ativas e no estado do sistema.

Exemplo (JSON do corpo):
```
{
  "interval_seconds": 30,
  "risk_profile": "balanced",
  "auto_confirm": true,
  "allowlist": [],
  "blocklist": [],
  "max_actions_per_cycle": 10,
  "max_seconds_per_cycle": 60
}
```

- `interval_seconds`: período entre ciclos do heartbeat.
- `risk_profile`: `conservative|balanced|aggressive` (controla permissões das ferramentas).
- `auto_confirm`: se true, ações que exigem confirmação são aprovadas automaticamente.
- `allowlist`/`blocklist`: nomes de ferramentas permitidas/bloqueadas.
- `max_actions_per_cycle`/`max_seconds_per_cycle`: limites de cada ciclo.

## Metas (Goals)
- Criar meta: `POST /api/v1/autonomy/goals`
- Listar metas: `GET /api/v1/autonomy/goals`
- Obter meta: `GET /api/v1/autonomy/goals/{goal_id}`
- Atualizar status: `PATCH /api/v1/autonomy/goals/{goal_id}/status`
- Excluir meta: `DELETE /api/v1/autonomy/goals/{goal_id}`

Exemplo de criação:
```
POST /api/v1/autonomy/goals
{
  "title": "Monitorar saúde do sistema",
  "description": "Garantir que serviços estão operacionais e registrar insights",
  "priority": 5,
  "success_criteria": "Todos os checks OK por 3 ciclos"
}
```
O Janus seleciona automaticamente a próxima meta pendente (`pending`) e a marca como `in_progress` ao iniciar um ciclo.

## Planejador Proativo (ORCHESTRATOR)
Quando não há um plano explícito em `start`, o planner gera um plano usando o ORCHESTRATOR:
- Prompt inclui: objetivo (title/description), critérios de sucesso, estado do sistema e a lista de ferramentas disponíveis do `ActionRegistry`.
- Saída esperada: JSON puro em formato `[{"tool": string, "args": object}]`.
- Políticas de risco/segurança são refletidas (ex.: em modo `conservative`, prioriza ferramentas `READ_ONLY`/`SAFE`).
- Limite de passos respeita `max_actions_per_cycle`.
- Fallback seguro: se o planejamento falhar, executa `get_current_datetime` e `get_system_info`.

Ferramentas típicas no plano:
- `get_current_datetime`, `get_system_info`
- `search_web`, `get_enriched_context`
- Ferramentas de memória/knowledge (consulta e análise)
- Sandbox Python (avaliação segura de expressões) conforme políticas

## Execução de Ações
- Cada passo passa por validação de políticas (`PolicyEngine`): permissões vs. perfil de risco, allow/blocklist e rate limits.
- Telemetria: cada execução registra latência e sucesso/erro via `ActionRegistry`.

## Cache de Respostas de LLMs
- O repositório de LLM usa um cache de respostas por `prompt+role+priority` com TTL configurável.
- Status/invalidação:
  - `GET /api/v1/llm/response-cache/status`
  - `POST /api/v1/llm/response-cache/invalidate` (filtros por `prompt`, `role`, `priority`)

Configuração (variáveis de ambiente):
- `LLM_RESPONSE_CACHE_ENABLED` (default: true)
- `LLM_RESPONSE_CACHE_TTL_SECONDS` (default: 900)

## Métricas Prometheus
- `autonomy_loop_cycles_total{outcome}`: ciclos executados.
- `autonomy_loop_cycle_duration_seconds`: duração de cada ciclo.
- `autonomy_loop_actions_total{outcome}`: ações executadas/bloqueadas/erro.
- Métricas de ferramentas (Action Module) e LLMs também estão disponíveis.

## Boas Práticas
- Defina metas claras com critérios de sucesso e prioridade.
- Em produção, comece com `risk_profile: conservative` e ajuste allowlist.
- Use `blocklist` para prevenir ferramentas indesejadas.
- Ajuste `interval_seconds` e quotas para evitar sobrecarga.
- Monitore as métricas e ajuste o planejamento conforme necessário.

## Exemplos Rápidos
- Iniciar autonomia sem plano explícito (planner ativo):
```
POST /api/v1/autonomy/start
{
  "interval_seconds": 20,
  "risk_profile": "balanced",
  "auto_confirm": true,
  "max_actions_per_cycle": 5,
  "max_seconds_per_cycle": 30
}
```
- Criar uma meta e deixar o planner agir:
```
POST /api/v1/autonomy/goals
{
  "title": "Coletar contexto ambiental",
  "description": "Capturar data/hora, sistema e contexto web relevante",
  "priority": 4
}
```
- Ver status do loop:
```
GET /api/v1/autonomy/status
```
- Invalidar cache de respostas (se necessário):
```
POST /api/v1/llm/response-cache/invalidate
{
  "role": "orchestrator"
}
```