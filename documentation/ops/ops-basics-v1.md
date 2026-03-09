# Ops Basics v1 (Bootstrap, Alerting, Backup/Restore)

## Objetivo

Este runbook define o baseline operacional local para o stack Janus:

- bootstrap reproduzivel via Docker Compose
- health checks basicos
- pipeline de alertas (Prometheus -> Alertmanager)
- backup/restore v1 (cold backup)

Escopo v1: operacao local/dev-ops. Nao e um plano de DR de producao.

## Pre-requisitos

- Docker + Docker Compose
- Repo clonado em `/Users/arthurparaiso/Desktop/janus-completo`

## Bootstrap rapido

1. Criar arquivo de ambiente local:

```bash
cp backend/app/.env.example backend/app/.env
```

2. Ajustar segredos minimos no `backend/app/.env`:

- `AUTH_JWT_SECRET`
- `POSTGRES_PASSWORD`
- `RABBITMQ_PASSWORD`
- `NEO4J_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`

3. Subir stack:

```bash
docker compose up -d
```

4. Verificar saude:

```bash
docker compose ps
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/healthz
curl -sf http://localhost:8000/api/v1/system/status
curl -sf http://localhost:8000/api/v1/workers/status
```

## Observabilidade (v1)

Servicos locais:

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Alertmanager: `http://localhost:9093`

### Alertmanager

O Alertmanager v1 e configurado com receiver padrao `null`:

- o pipeline de alerta fica funcional (Prometheus envia alertas)
- nenhum alerta e enviado para canal externo por padrao

Para integrar webhook/Slack em ambiente local:

- crie um arquivo local (nao versionado) com override de configuracao, por exemplo:
  - `backend/observability/alertmanager/alertmanager.local.yml`
- ajuste o compose localmente conforme sua necessidade

## Backup (cold backup v1)

O backup v1 para o stack para copiar os stores locais com consistencia simples.

### Comando recomendado

```bash
./tooling/backup-stack.sh --skip-ollama
```

Exemplo para ambiente remoto (PC Teste em `100.89.17.105`) via SSH:

```bash
ssh queliarte-server@100.89.17.105 \
  "cd /caminho/do/repo/janus-completo && ./tooling/backup-stack.sh \
    --skip-ollama \
    --rabbitmq-api-url http://100.89.17.105:15672"
```

Saida padrao:

- `outputs/backups/<timestamp>/manifest.json`
- `outputs/backups/<timestamp>/compose-ps.txt`
- `outputs/backups/<timestamp>/checksums.txt`
- `outputs/backups/<timestamp>/rabbitmq-definitions.json` (best effort)
- `outputs/backups/<timestamp>/data/*.tar.gz`

### Flags uteis

- `--output-dir <dir>`: muda destino do backup
- `--include-ollama`: inclui `backend/data/ollama` (pode ser grande)
- `--no-restart`: nao sobe o stack no final (manutencao manual)
- `--rabbitmq-api-url <url>`: endpoint da API de management do RabbitMQ

## Restore (cold backup v1)

Restore sobrescreve `backend/data/*` a partir de um backup gerado pelo script.

### Comando recomendado

```bash
./tooling/restore-stack.sh --backup-dir outputs/backups/<timestamp> --force
```

Exemplo para ambiente remoto (PC Teste em `100.89.17.105`) via SSH:

```bash
ssh queliarte-server@100.89.17.105 \
  "cd /caminho/do/repo/janus-completo && ./tooling/restore-stack.sh \
    --backup-dir outputs/backups/<timestamp> \
    --force \
    --api-base-url http://100.89.17.105:8000 \
    --rabbitmq-api-url http://100.89.17.105:15672"
```

### Comportamento

- faz `docker compose down`
- renomeia dados atuais para `*.pre-restore.<timestamp>`
- restaura arquivos `*.tar.gz`
- sobe o stack novamente
- tenta importar definicoes do RabbitMQ (se presentes)
- roda health checks basicos

### Flags uteis

- `--skip-rabbitmq-definitions-import`
- `--api-base-url <url>`: base da API para health checks pos-restore
- `--rabbitmq-api-url <url>`: endpoint da API de management do RabbitMQ

## Config opcional: Google service account

Se voce usar integracoes Google que exigem service account local:

- crie o arquivo (nao versionado):
  - `backend/app/serviceAccountKey.json`

Se nao usar essas integracoes, o arquivo pode permanecer ausente.

## Validacao pos-restore

```bash
docker compose ps
curl -sf http://100.89.17.105:8000/health
curl -sf http://100.89.17.105:8000/healthz
curl -sf http://100.89.17.105:8000/api/v1/system/status
curl -sf http://100.89.17.105:8000/api/v1/workers/status
docker compose logs --since=2m janus-api
docker compose logs --since=2m rabbitmq
docker compose logs --since=2m prometheus
docker compose logs --since=2m alertmanager
```

## Limitacoes conhecidas (v1)

- Backup e restore sao `cold` (stack parado), nao online/hot backup.
- Receiver de Alertmanager e `null` por padrao (sem entrega externa).
- Nao ha DR automatizado em cloud.
- Loki/Tempo podem existir como configuracao/provisioning, mas nao fazem parte deste baseline v1.
