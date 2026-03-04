# Deployment Guide

## Visao Geral

O deploy oficial do projeto usa dois stacks separados:

- `PC1`: `docker-compose.pc1.yml` (API + Postgres + Redis + RabbitMQ)
- `PC2`: `docker-compose.pc2.yml` (Neo4j + Qdrant + Ollama)

Nao ha suporte operacional para `docker-compose.yml` legado.

## Ordem de Subida

```bash
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

## Validacao Rapida

PC2:

```bash
curl -sf http://localhost:11434/api/tags
curl -sf -H "api-key: ${QDRANT_API_KEY}" http://localhost:6333/collections
```

PC1:

```bash
curl -sf http://localhost:8000/health
```

## Rede: somente Tailscale no PC2

Servicos do PC2 devem ficar acessiveis apenas via `tailscale0`:

- Neo4j `7687`
- Qdrant `6333`
- Ollama `11434`

Exemplo com `ufw` (ajuste conforme seu host):

```bash
sudo ufw deny 7687/tcp
sudo ufw deny 6333/tcp
sudo ufw deny 11434/tcp
sudo ufw allow in on tailscale0 to any port 7687 proto tcp
sudo ufw allow in on tailscale0 to any port 6333 proto tcp
sudo ufw allow in on tailscale0 to any port 11434 proto tcp
sudo ufw reload
```

## Credenciais e Volumes

Se houve troca de senha em Neo4j/Postgres, resetar volumes para alinhar credenciais:

```bash
# PC2 (Neo4j)
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 down -v
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d

# PC1 (Postgres)
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 down -v
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d
```

## Referencia

Fluxo operacional detalhado: `documentation/deployment-split-pc1-pc2.md`.
