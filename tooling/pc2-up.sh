#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ENV_FILE=".env.pc2"
RESET_VOLUMES=0
SKIP_PULL=0
TIMEOUT_SECONDS=300

usage() {
  cat <<'EOF'
Usage: tooling/pc2-up.sh [options]

Options:
  --env-file <path>      Env file to use (default: .env.pc2)
  --reset-volumes        Run `down -v --remove-orphans` before `up -d`
  --skip-pull            Skip `docker compose pull`
  --timeout <seconds>    Health wait timeout (default: 300)
  -h, --help             Show this help
EOF
}

while (($#)); do
  case "$1" in
    --env-file)
      ENV_FILE="${2:-}"
      shift 2
      ;;
    --reset-volumes)
      RESET_VOLUMES=1
      shift
      ;;
    --skip-pull)
      SKIP_PULL=1
      shift
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ "${ENV_FILE}" == ".env.pc2" && -f ".env.pc2.example" ]]; then
    cp ".env.pc2.example" ".env.pc2"
    echo "Created .env.pc2 from .env.pc2.example. Review secrets before rerun." >&2
  else
    echo "Env file not found: ${ENV_FILE}" >&2
  fi
  exit 1
fi

# shellcheck disable=SC1090
set -a; source "${ENV_FILE}"; set +a
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-}"
if [[ -z "${NEO4J_PASSWORD}" ]]; then
  echo "NEO4J_PASSWORD is empty in ${ENV_FILE}" >&2
  exit 1
fi

COMPOSE=(docker compose -f docker-compose.pc2.yml --env-file "${ENV_FILE}")

echo "[pc2-up] Validating compose..."
"${COMPOSE[@]}" config >/dev/null

if (( RESET_VOLUMES )); then
  echo "[pc2-up] Resetting PC2 volumes..."
  "${COMPOSE[@]}" down -v --remove-orphans
fi

if (( SKIP_PULL == 0 )); then
  echo "[pc2-up] Pulling images..."
  "${COMPOSE[@]}" pull
fi

echo "[pc2-up] Starting stack..."
"${COMPOSE[@]}" up -d

wait_http() {
  local url="$1"
  local timeout="$2"
  local start now
  start="$(date +%s)"
  while true; do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

wait_healthy() {
  local container="$1"
  local timeout="$2"
  local start now status
  start="$(date +%s)"
  while true; do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${container}" 2>/dev/null || true)"
    if [[ "${status}" == "healthy" || "${status}" == "running" ]]; then
      return 0
    fi
    now="$(date +%s)"
    if (( now - start >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

echo "[pc2-up] Waiting for container health..."
wait_healthy "janus_neo4j" "${TIMEOUT_SECONDS}" || { echo "neo4j health timeout"; exit 1; }
wait_healthy "janus_qdrant" "${TIMEOUT_SECONDS}" || { echo "qdrant health timeout"; exit 1; }
wait_healthy "janus_ollama" "${TIMEOUT_SECONDS}" || { echo "ollama health timeout"; exit 1; }

echo "[pc2-up] Running smoke checks..."
wait_http "http://localhost:6333/collections" "${TIMEOUT_SECONDS}" || {
  echo "qdrant http check failed"
  exit 1
}
wait_http "http://localhost:11434/api/tags" "${TIMEOUT_SECONDS}" || {
  echo "ollama http check failed"
  exit 1
}

docker exec "janus_neo4j" cypher-shell -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" "RETURN 1;" >/dev/null

echo "[pc2-up] OK"
"${COMPOSE[@]}" ps
