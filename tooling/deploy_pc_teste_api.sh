#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Repositorio git nao encontrado."
  exit 1
fi

export JANUS_BUILD_REF="${JANUS_BUILD_REF:-$(git rev-parse HEAD)}"

echo "JANUS_BUILD_REF=$JANUS_BUILD_REF"
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 build janus-api
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d janus-api

echo "Aguardando health da API..."
for _ in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/tmp/janus_health.json; then
    cat /tmp/janus_health.json
    exit 0
  fi
  sleep 2
done

echo "Health check nao ficou pronto a tempo."
exit 1
