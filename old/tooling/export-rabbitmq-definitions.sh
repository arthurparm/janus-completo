#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/backend/app/.env"
OUTPUT_FILE=""
BEST_EFFORT="false"
RABBITMQ_API_URL="http://localhost:15672"

usage() {
  cat <<'EOF'
Usage: tooling/export-rabbitmq-definitions.sh --output <file> [--api-url <url>] [--best-effort]

Exports RabbitMQ definitions using the local management API.
Requires RABBITMQ_USER and RABBITMQ_PASSWORD in backend/app/.env.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FILE="${2:-}"
      shift 2
      ;;
    --api-url)
      RABBITMQ_API_URL="${2:-}"
      shift 2
      ;;
    --best-effort)
      BEST_EFFORT="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${OUTPUT_FILE}" ]]; then
  echo "--output is required" >&2
  exit 2
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Env file not found: ${ENV_FILE}" >&2
  [[ "${BEST_EFFORT}" == "true" ]] && exit 0
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "${ENV_FILE}"
set +a

if [[ -z "${RABBITMQ_USER:-}" || -z "${RABBITMQ_PASSWORD:-}" ]]; then
  echo "RABBITMQ_USER/RABBITMQ_PASSWORD missing in ${ENV_FILE}" >&2
  [[ "${BEST_EFFORT}" == "true" ]] && exit 0
  exit 1
fi

mkdir -p "$(dirname "${OUTPUT_FILE}")"

if ! curl -sfS \
  --user "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
  "${RABBITMQ_API_URL%/}/api/definitions" \
  -o "${OUTPUT_FILE}"; then
  echo "RabbitMQ definitions export failed" >&2
  [[ "${BEST_EFFORT}" == "true" ]] && exit 0
  exit 1
fi

echo "Exported RabbitMQ definitions to ${OUTPUT_FILE}"
