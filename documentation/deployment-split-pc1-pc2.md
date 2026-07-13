# Deploy Split: PC1 + PC2

## Topologia

- `PC1 (i7, 16GB, 250GB)`:
  - `janus-api`
  - `postgres`
  - `redis`
  - `rabbitmq`
- `PC2 (i9, 64GB, 1TB, RTX 4060 Ti 16GB)`:
  - `neo4j`
  - `qdrant`
  - `ollama`

## Preset de tuning Ollama

- PC2 (servidor Ollama):
  - `OLLAMA_NUM_PARALLEL=1`
  - `OLLAMA_MAX_LOADED_MODELS=1`
  - `OLLAMA_KEEP_ALIVE=120m`
- PC1 (cliente Janus -> Ollama):
  - `OLLAMA_NUM_CTX=4096`
  - sem tuning agressivo de GPU/thread/batch (controlado no PC2)

## Politica de Rede (PC2)

Qdrant usa API key obrigatoria por politica operacional (`QDRANT_API_KEY`).
Protecao obrigatoria: portas expostas apenas na interface Tailscale (`tailscale0`).

Quando TLS estiver habilitado no proprio Qdrant, configure:

- PC2: `QDRANT_ENABLE_TLS=true`, `QDRANT_TLS_CERT=/qdrant/tls/cert.pem`, `QDRANT_TLS_KEY=/qdrant/tls/key.pem` e `QDRANT_TLS_CA_CERT=/qdrant/tls/ca.pem`.
- PC1: `QDRANT_HTTPS=true` e `QDRANT_TLS_CA_CERT=/run/secrets/janus/qdrant/ca.pem`.
- Certificados locais devem ficar em `.secrets/qdrant/`, que e ignorado pelo Git.

Sem TLS, a API key do Qdrant ainda deve trafegar somente em rede privada controlada.

Exemplo `ufw`:

```bash
sudo ufw deny 7687/tcp
sudo ufw deny 6333/tcp
sudo ufw deny 11434/tcp
sudo ufw allow in on tailscale0 to any port 7687 proto tcp
sudo ufw allow in on tailscale0 to any port 6333 proto tcp
sudo ufw allow in on tailscale0 to any port 11434 proto tcp
sudo ufw reload
```

## Arquivos

- PC1: `docker-compose.pc1.yml` + `.env.pc1.example`
- PC2: `docker-compose.pc2.yml` + `.env.pc2.example`

## Ordem de deploy

1. Subir PC2.
2. Validar portas em PC2 (`7687`, `6333`, `11434`).
3. Buildar imagem da API no PC1.
4. Subir PC1 apontando para o IP Tailscale do PC2.

## Reset de credenciais stateful

Quando senha de Neo4j/Postgres mudar, resetar volumes para evitar mismatch com dados antigos:

```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 down -v
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d

docker compose -f docker-compose.pc1.yml --env-file .env.pc1 down -v
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

## Comandos

PC2:

```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
```

PC1:

```bash
docker build -f backend/docker/Dockerfile -t janus-completo-janus-api:latest backend
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

## Checks

PC2:

```bash
curl -sf http://localhost:11434/api/tags
curl -sf -H "api-key: ${QDRANT_API_KEY}" http://localhost:6333/collections
```

Com Qdrant TLS ativo:

```bash
curl --cacert .secrets/qdrant/ca.pem -sf -H "api-key: ${QDRANT_API_KEY}" https://localhost:6333/collections
```

PC1:

```bash
curl -sf http://localhost:8000/health
```

## Backup Qdrant

Antes de upgrade ou manutencao stateful no Qdrant, gere snapshots das colecoes por HTTPS validado:

```bash
python backend/scripts/data_plane_backup_restore.py backup \
  --components qdrant \
  --qdrant-url https://localhost:6333 \
  --qdrant-api-key "${QDRANT_API_KEY}" \
  --qdrant-ca-cert .secrets/qdrant/ca.pem \
  --output-dir outputs/qa/data-plane-backups
```

Verificacao operacional:

```bash
python backend/scripts/data_plane_backup_restore.py verify \
  --components qdrant \
  --qdrant-url https://localhost:6333 \
  --qdrant-api-key "${QDRANT_API_KEY}" \
  --qdrant-ca-cert .secrets/qdrant/ca.pem
```

Validacao offline dos artefatos antes de restore:

```bash
python backend/scripts/data_plane_backup_restore.py restore \
  --dry-run \
  --components qdrant \
  --restore-dir outputs/qa/data-plane-backups/<run-id>
```

Quando `manifest.json` existir no diretorio restaurado, o restore compara o SHA-256
registrado de cada artefato antes de carregar snapshots. Divergencia de checksum
aborta o restore antes de upload/carga.

Retencao auditavel, sem apagar por padrao:

```bash
python backend/scripts/data_plane_backup_restore.py prune \
  --output-dir outputs/qa/data-plane-backups \
  --retention-days 14 \
  --retain-last 5
```

Remocao real exige confirmacao operacional explicita via flag:

```bash
python backend/scripts/data_plane_backup_restore.py prune \
  --output-dir outputs/qa/data-plane-backups \
  --retention-days 14 \
  --retain-last 5 \
  --prune-apply
```
