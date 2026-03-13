#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Repositorio git nao encontrado."
  exit 1
fi

export JANUS_BUILD_REF="${JANUS_BUILD_REF:-$(git rev-parse HEAD)}"
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"
BUILD_TIMEOUT_SECONDS="${BUILD_TIMEOUT_SECONDS:-420}"
COMPOSE_CMD=(docker compose -f docker-compose.pc1.yml --env-file .env.pc1)

echo "JANUS_BUILD_REF=$JANUS_BUILD_REF"

build_with_compose() {
  echo "Executando build via docker compose..."
  if command -v timeout >/dev/null 2>&1; then
    timeout "$BUILD_TIMEOUT_SECONDS" "${COMPOSE_CMD[@]}" build janus-api
  else
    "${COMPOSE_CMD[@]}" build janus-api
  fi
}

build_with_docker() {
  echo "Executando fallback via docker build..."
  docker build \
    --progress plain \
    --target final \
    --build-arg "JANUS_BUILD_REF=$JANUS_BUILD_REF" \
    -t janus-completo-janus-api:latest \
    -f backend/docker/Dockerfile \
    backend
}

if ! build_with_compose; then
  echo "Build via docker compose falhou ou excedeu timeout. Aplicando fallback."
  build_with_docker
fi

"${COMPOSE_CMD[@]}" up -d janus-api

echo "Aguardando health da API..."
for _ in $(seq 1 60); do
  if curl -sf http://localhost:8000/health >/tmp/janus_health.json; then
    cat /tmp/janus_health.json
    if python3 - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path("/tmp/janus_health.json").read_text())
expected = os.environ["JANUS_BUILD_REF"]
build_ref = payload.get("build_ref")
if build_ref != expected:
    raise SystemExit(1)
PY
    then
      exit 0
    fi
  fi
  sleep 2
done

echo "Health check nao ficou pronto a tempo ou retornou build_ref inesperado."
exit 1
