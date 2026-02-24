#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR=""
FORCE="false"
SKIP_RABBIT_IMPORT="false"

usage() {
  cat <<'EOF'
Usage: tooling/restore-stack.sh --backup-dir <dir> [--force] [--skip-rabbitmq-definitions-import]

Restores cold backup archives created by tooling/backup-stack.sh.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir)
      BACKUP_DIR="${2:-}"
      shift 2
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --skip-rabbitmq-definitions-import)
      SKIP_RABBIT_IMPORT="true"
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

if [[ -z "${BACKUP_DIR}" ]]; then
  echo "--backup-dir is required" >&2
  exit 2
fi

cd "${ROOT_DIR}"
if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "Backup dir not found: ${BACKUP_DIR}" >&2
  exit 1
fi
if [[ ! -f "${BACKUP_DIR}/manifest.json" ]]; then
  echo "manifest.json not found in ${BACKUP_DIR}" >&2
  exit 1
fi

if [[ "${FORCE}" != "true" ]]; then
  printf "This will overwrite local backend/data directories from %s. Continue? [y/N] " "${BACKUP_DIR}"
  read -r answer
  case "${answer}" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
data_root="${ROOT_DIR}/backend/data"
mkdir -p "${data_root}"

echo "Stopping compose stack..."
docker compose down >/dev/null

restore_archive() {
  local name="$1"
  local tar_path="${BACKUP_DIR}/data/${name}.tar.gz"
  local target_dir="${data_root}/${name}"
  local backup_old="${data_root}/${name}.pre-restore.${timestamp}"

  if [[ ! -f "${tar_path}" ]]; then
    return 0
  fi

  if [[ -e "${target_dir}" ]]; then
    mv "${target_dir}" "${backup_old}"
  fi
  mkdir -p "${data_root}"
  tar -C "${data_root}" -xzf "${tar_path}"
}

restore_archive "postgres"
restore_archive "neo4j"
restore_archive "qdrant"
restore_archive "redis"
restore_archive "rabbitmq"
restore_archive "ollama"

echo "Starting compose stack..."
docker compose up -d >/dev/null

echo "Waiting for RabbitMQ before definitions import..."
for _ in $(seq 1 60); do
  if curl -s "http://localhost:15672" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if [[ "${SKIP_RABBIT_IMPORT}" == "false" && -f "${BACKUP_DIR}/rabbitmq-definitions.json" ]]; then
  "${ROOT_DIR}/tooling/import-rabbitmq-definitions.sh" --input "${BACKUP_DIR}/rabbitmq-definitions.json" || {
    echo "RabbitMQ definitions import failed (continuing)." >&2
  }
fi

echo "Running health checks..."
curl -sf http://localhost:8000/health >/dev/null
curl -sf http://localhost:8000/healthz >/dev/null
curl -sf http://localhost:8000/api/v1/system/status >/dev/null
curl -sf http://localhost:8000/api/v1/workers/status >/dev/null

echo "Restore completed from ${BACKUP_DIR}"
