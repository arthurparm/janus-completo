# Janus 1.0.0 — Release Notes

Data: 2025-10-21

Este documento resume as mudanças, melhorias, correções e instruções de atualização para a versão 1.0.0 do Janus AI Architect.

## Destaques
- Orquestração de workers unificada com endpoint: `POST /api/v1/workers/start-all`.
- Consolidação de conhecimento mais robusta (fila `janus.knowledge.consolidation`), com endpoints para publicação e observabilidade:
  - `POST /api/v1/knowledge/consolidate` (single ou batch)
  - `GET /api/v1/tasks/queue/janus.knowledge.consolidation` (profundidade/consumers)
  - `GET /api/v1/knowledge/stats` (nós/relacionamentos)
- Meta-Agente e Reflexion Worker integrados ao orquestrador de workers.
- Configuration-as-Data para prompts e agentes dinâmicos, com persistência MySQL.
- Observabilidade aprimorada (Prometheus/Grafana), incluindo métricas por workers e componentes.

## Melhorias
- Logs estruturados e health checks consistentes para API e serviços subjacentes.
- Tuning de memória do Neo4j e melhorias de resiliência em `docker-compose.yml`.
- Padronização de endpoints e contratos para tasks e conhecimento.

## Correções Importantes
- Ajuste de `SyntaxError` em `code_agent_worker.py` causado por f-string com `\n` dentro da expressão. Agora a contagem de linhas é pré-calculada e usada sem backslashes:
  - `lines_count = code.count("\n") + 1`
  - `"notes": f"lines={lines_count}"`
- Tratamento de erro `400 Bad Request` no Qdrant por IDs inválidos em pontos: os IDs devem ser `UUID` ou `unsigned integer`.

## Mudanças Potencialmente Quebradoras (Breaking Changes)
- O fluxo de inicialização dos workers agora pode recusar iniciar se houver erros sintáticos em módulos carregados (ex.: f-string inválida). Garanta que a API esteja livre de erros antes de usar `start-all`.
- IDs para pontos em Qdrant: reforçada a validação para `UUID`/inteiro sem sinal.

## Guia de Atualização
1. Atualize a configuração (`.env`) para refletir a versão:
   - `APP_VERSION=1.0.0`
2. Suba os serviços com Docker Compose:
   - `docker compose up -d`
3. Verifique readiness:
   - API: `http://localhost:8000/readyz`
4. Inicie os workers:
   - `POST /api/v1/workers/start-all`
5. Publique experiências para consolidar:
   - `POST /api/v1/knowledge/consolidate` com `mode=single` ou `mode=batch`
6. Observe a fila de consolidação:
   - `GET /api/v1/tasks/queue/janus.knowledge.consolidation` → verifique `messages` e `consumers`
7. Confirme a evolução do grafo:
   - `GET /api/v1/knowledge/stats`

## Solução de Problemas (1.0.0)
- `SyntaxError: f-string expression part cannot include a backslash`
  - Corrija a expressão do f-string; evite `\n` dentro da expressão.
  - Reinicie a API após o ajuste.
- `Qdrant 400 Format error in JSON body`
  - Use IDs válidos (`UUID` ou `unsigned integer`) ao publicar/consultar pontos.
- Fila com `consumers=0`
  - Inicie os workers com `start-all` e confirme consumo pela fila.

## Endpoints Referência
- Workers:
  - `POST /api/v1/workers/start-all`
  - `POST /api/v1/workers/stop-all`
  - `GET /api/v1/workers/status-all`
- Conhecimento:
  - `POST /api/v1/knowledge/consolidate`
  - `GET /api/v1/knowledge/stats`
- Tasks/Filas:
  - `GET /api/v1/tasks/queue/{queue_name}`

## Links Úteis
- Changelog completo: `CHANGELOG.md`
- Guia de Uso: `doc/Usage.md`
- Configuração: `doc/Configuration.md`
- Troubleshooting: `doc/Troubleshooting.md`
- Arquitetura: `doc/Architecture.md`

## Créditos
A todos os contribuidores que ajudaram a consolidar a primeira versão estável do Janus.