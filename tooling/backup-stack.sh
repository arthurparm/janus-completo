#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_OUTPUT_ROOT="${ROOT_DIR}/outputs/backups"
OUTPUT_ROOT="${DEFAULT_OUTPUT_ROOT}"
SKIP_OLLAMA="true"
NO_RESTART="false"
RABBITMQ_API_URL="http://localhost:15672"

usage() {
  cat <<'EOF'
Usage: tooling/backup-stack.sh [--output-dir <dir>] [--skip-ollama] [--include-ollama] [--no-restart] [--rabbitmq-api-url <url>]

Cold backup v1 for local Docker Compose stateful services.
Stops running compose services, snapshots backend/data directories, optionally exports RabbitMQ definitions,
and restarts the stack unless --no-restart is provided.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_ROOT="${2:-}"
      shift 2
      ;;
    --skip-ollama)
      SKIP_OLLAMA="true"
      shift
      ;;
    --include-ollama)
      SKIP_OLLAMA="false"
      shift
      ;;
    --no-restart)
      NO_RESTART="true"
      shift
      ;;
    --rabbitmq-api-url)
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

cd "${ROOT_DIR}"
if [[ ! -f "docker-compose.yml" ]]; then
  echo "Run from repository root (docker-compose.yml not found)." >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${OUTPUT_ROOT%/}/${timestamp}"
mkdir -p "${backup_dir}"

restart_stack() {
  if [[ "${NO_RESTART}" == "false" ]]; then
    echo "Restarting docker compose stack..."
    docker compose up -d >/dev/null
  fi
}

trap 'rc=$?; if [[ $rc -ne 0 ]]; then echo "Backup failed (exit ${rc})."; restart_stack; fi' EXIT

echo "Exporting RabbitMQ definitions (best effort)..."
"${ROOT_DIR}/tooling/export-rabbitmq-definitions.sh" \
  --output "${backup_dir}/rabbitmq-definitions.json" \
  --api-url "${RABBITMQ_API_URL}" \
  --best-effort || true

echo "Saving compose status..."
docker compose ps > "${backup_dir}/compose-ps.txt" || true

services="$(docker compose ps --services 2>/dev/null | tr '\n' ' ' | sed 's/  */ /g; s/^ //; s/ $//')"
if [[ -n "${services}" ]]; then
  echo "Stopping services for cold snapshot..."
  # shellcheck disable=SC2086
  docker compose stop ${services}
fi

mkdir -p "${backup_dir}/data"

checksum_file="${backup_dir}/checksums.txt"
: > "${checksum_file}"

hash_file() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${file}" >> "${checksum_file}"
  else
    shasum -a 256 "${file}" >> "${checksum_file}"
  fi
}

snapshot_dir() {
  local name="$1"
  local rel_path="$2"
  local src="${ROOT_DIR}/${rel_path}"
  local tar_path="${backup_dir}/data/${name}.tar.gz"

  if [[ ! -d "${src}" ]]; then
    echo "Skipping missing directory: ${rel_path}"
    return 0
  fi

  echo "Archiving ${rel_path}..."
  tar -C "$(dirname "${src}")" -czf "${tar_path}" "$(basename "${src}")"
  hash_file "${tar_path}"
}

snapshot_dir "postgres" "backend/data/postgres"
snapshot_dir "neo4j" "backend/data/neo4j"
snapshot_dir "qdrant" "backend/data/qdrant"
snapshot_dir "redis" "backend/data/redis"
snapshot_dir "rabbitmq" "backend/data/rabbitmq"
if [[ "${SKIP_OLLAMA}" == "false" ]]; then
  snapshot_dir "ollama" "backend/data/ollama"
fi

git_commit="$(git rev-parse HEAD 2>/dev/null || true)"
hostname_value="$(hostname 2>/dev/null || echo unknown)"

python3 - "$backup_dir" "$timestamp" "$hostname_value" "$git_commit" "$services" "$SKIP_OLLAMA" "$RABBITMQ_API_URL" <<'PY'
import json, sys
from pathlib import Path

backup_dir = Path(sys.argv[1])
timestamp = sys.argv[2]
hostname = sys.argv[3]
git_commit = sys.argv[4]
services = [s for s in sys.argv[5].split(" ") if s]
skip_ollama = sys.argv[6].lower() == "true"
rabbitmq_api_url = sys.argv[7]

data_archives = sorted(
    [p.name for p in (backup_dir / "data").glob("*.tar.gz")]
)
manifest = {
    "backup_version": "v1-cold",
    "timestamp_utc": timestamp,
    "hostname": hostname,
    "git_commit": git_commit or None,
    "services_stopped": services,
    "skip_ollama": skip_ollama,
    "rabbitmq_api_url": rabbitmq_api_url,
    "artifacts": {
        "compose_ps": "compose-ps.txt",
        "rabbitmq_definitions": "rabbitmq-definitions.json" if (backup_dir / "rabbitmq-definitions.json").exists() else None,
        "checksums": "checksums.txt",
        "data_archives": data_archives,
    },
}
(backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY

hash_file "${backup_dir}/manifest.json"

restart_stack
trap - EXIT

echo "Backup completed: ${backup_dir}"
