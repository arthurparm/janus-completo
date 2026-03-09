# Incident Response Playbook (OQ-010)

Data de referencia: 2026-03-08  
Escopo: Frontend (`100.89.17.105:4300`) e Backend (`100.89.17.105:8000`)

## Objetivo

Padronizar resposta a incidentes com um fluxo unico para:
- detectar, classificar e conter impacto rapidamente,
- preservar evidencias tecnicas,
- restaurar servico com risco controlado,
- registrar aprendizado em postmortem sem culpabilizacao.

## Canais e papeis

- Incident Commander (IC): coordena decisao e comunicacao.
- Ops Executor: executa comandos, coleta logs e evidencias.
- Scribe: registra timeline e acoes no incidente.
- Subject Matter Expert (SME): suporte tecnico (API, frontend, banco, infra).

## Classificacao de severidade

- SEV-1: indisponibilidade total do backend `:8000` ou falha critica de autenticacao/pagamento.
- SEV-2: degradacao relevante de funcionalidade principal com workaround parcial.
- SEV-3: falha localizada sem impacto amplo.

Meta inicial:
- Ack: ate 5 minutos.
- Mitigacao inicial: ate 15 minutos para SEV-1/SEV-2.
- Comunicacao de status: a cada 15 minutos enquanto ativo.

## Runbook de resposta rapida

### 1) Confirmar incidente e abrir timeline

```bash
date -u
curl -i --max-time 10 http://100.89.17.105:8000/health
curl -i --max-time 10 http://100.89.17.105:8000/healthz
curl -i --max-time 10 http://100.89.17.105:8000/api/v1/system/status
```

Se qualquer probe acima retornar `5xx` ou timeout, tratar como incidente ativo.

### 2) Coletar evidencia minima (sem alterar estado)

```bash
ssh queliarte-server@100.89.17.105
```

No servidor:

```bash
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs --tail 200 janus-api
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs --tail 200 neo4j
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs --tail 200 qdrant
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs --tail 200 ollama
```

### 3) Isolar dominio impactado

Executar verificacoes por dominio:

```bash
curl -sS "http://100.89.17.105:8000/api/v1/observability/slo/domains?window_minutes=15&min_events=20"
curl -i --max-time 10 http://100.89.17.105:8000/api/v1/workers/status
curl -i --max-time 10 http://100.89.17.105:8000/api/v1/system/status
```

### 4) Mitigar

Acoes permitidas (ordem sugerida):
- Reiniciar servico afetado (`pc1` ou `pc2`) com menor blast radius.
- Desabilitar temporariamente fluxo nao-essencial.
- Escalar para rollback quando houver regressao apos deploy.

Exemplo de restart controlado:

```bash
ssh queliarte-server@100.89.17.105 "cd /opt/janus-completo && docker compose -f docker-compose.pc1.yml --env-file .env.pc1 restart janus-api"
```

### 5) Validar recuperacao

```bash
curl -i --max-time 10 http://100.89.17.105:8000/health
curl -i --max-time 10 http://100.89.17.105:8000/api/v1/system/status
curl -i --max-time 10 http://100.89.17.105:4300
```

Criterio minimo de recuperacao:
- `health` e `system/status` retornando `200`.
- Frontend respondendo na porta `4300`.

### 6) Encerrar incidente

Checklist de encerramento:
- impacto cessou,
- timeline revisada,
- evidencias anexadas,
- postmortem criado em ate 48h usando template oficial.

## Evidencias obrigatorias

- Horario UTC de inicio, mitigacao e encerramento.
- Comandos executados e saidas relevantes.
- Logs (tail) dos servicos impactados.
- Request IDs / trace IDs de falhas representativas.
- Decisao de rollback/hotfix e justificativa.

## Integracoes de apoio

- SSH servidor: `ssh queliarte-server@100.89.17.105`
- Portainer (visao operacional): `https://100.89.17.105:9443/#!/3/docker/stacks/janus-completo?type=2&external=true`
- Neo4j Browser: `http://100.88.71.49:7474/browser/`
- Qdrant endpoint: `https://100.89.17.105:9443`

## DoD (OQ-010)

- Existe playbook versionado para resposta a incidentes.
- Existe template de postmortem padrao para analise sem culpa.
- Fluxo inclui comandos concretos no ambiente de producao/teste (`100.89.17.105`).
