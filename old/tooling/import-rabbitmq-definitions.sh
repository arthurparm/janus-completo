#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/backend/app/.env"
INPUT_FILE=""
RABBITMQ_API_URL="http://localhost:15672"

usage() {
  cat <<'EOF'
Usage: tooling/import-rabbitmq-definitions.sh --input <rabbitmq-definitions.json> [--api-url <url>]

Imports RabbitMQ definitions using the local management API.
Requires RABBITMQ_USER and RABBITMQ_PASSWORD in backend/app/.env.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      INPUT_FILE="${2:-}"
      shift 2
      ;;
    --api-url)
      RABBITMQ_API_URL="${2:-}"
      shift 2
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

if [[ -z "${INPUT_FILE}" ]]; then
  echo "--input is required" >&2
  exit 2
fi
if [[ ! -f "${INPUT_FILE}" ]]; then
  echo "Definitions file not found: ${INPUT_FILE}" >&2
  exit 1
fi
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Env file not found: ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "${ENV_FILE}"
set +a

if [[ -z "${RABBITMQ_USER:-}" || -z "${RABBITMQ_PASSWORD:-}" ]]; then
  echo "RABBITMQ_USER/RABBITMQ_PASSWORD missing in ${ENV_FILE}" >&2
  exit 1
fi

curl -sfS \
  --user "${RABBITMQ_USER}:${RABBITMQ_PASSWORD}" \
  -H "content-type: application/json" \
  -X POST "${RABBITMQ_API_URL%/}/api/definitions" \
  --data-binary "@${INPUT_FILE}" >/dev/null

echo "Imported RabbitMQ definitions from ${INPUT_FILE}"
