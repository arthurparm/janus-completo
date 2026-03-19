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

PC1:

```bash
curl -sf http://localhost:8000/health
```
