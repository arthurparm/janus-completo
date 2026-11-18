#!/usr/bin/env bash
# Backup script for the stateful services hosted on the current machine.
# For janus-completo this script is scoped to the local Docker host:
# - PC1: PostgreSQL + Redis
# - Config snapshots: compose files, monitoring, docker assets
# Run as cron job: 0 2 * * * /path/to/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-.backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-7}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-janus_postgres_pc1}"
POSTGRES_USER="${POSTGRES_USER:-janus}"
POSTGRES_DB="${POSTGRES_DB:-janus_db}"
REDIS_CONTAINER="${REDIS_CONTAINER:-janus_redis_pc1}"

find_container() {
  local candidate
  for candidate in "$@"; do
    if docker ps -a --format '{{.Names}}' | grep -qx "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

echo "🔄 Starting JANUS backup at $(date)"
echo "📍 Scope: local Docker host only (PC1 services when executed on PC1)"

mkdir -p "$BACKUP_DIR"

echo "📦 Backing up PostgreSQL..."

PGBACKUP="$BACKUP_DIR/postgresql_$TIMESTAMP.sql.gz"

if POSTGRES_CONTAINER_RESOLVED="$(find_container "$POSTGRES_CONTAINER" janus_postgres)"; then
  docker exec "$POSTGRES_CONTAINER_RESOLVED" pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-privileges \
    --no-owner \
    | gzip > "$PGBACKUP"
else
  echo "⚠️  PostgreSQL container not found. Skipping PostgreSQL backup."
fi

if [ -f "$PGBACKUP" ]; then
  SIZE=$(du -h "$PGBACKUP" | cut -f1)
  echo "✅ PostgreSQL backup: $PGBACKUP ($SIZE)"
fi

echo "📦 Backing up Redis..."

REDISBACKUP="$BACKUP_DIR/redis_$TIMESTAMP.rdb"

if REDIS_CONTAINER_RESOLVED="$(find_container "$REDIS_CONTAINER" janus_redis)"; then
  docker exec "$REDIS_CONTAINER_RESOLVED" redis-cli BGSAVE > /dev/null
  sleep 2
  docker cp "$REDIS_CONTAINER_RESOLVED:/data/dump.rdb" "$REDISBACKUP"
  gzip -f "$REDISBACKUP"
else
  echo "⚠️  Redis container not found. Skipping Redis backup."
fi

if [ -f "$REDISBACKUP.gz" ]; then
  SIZE=$(du -h "$REDISBACKUP.gz" | cut -f1)
  echo "✅ Redis backup: $REDISBACKUP.gz ($SIZE)"
fi

echo "📦 Backing up configurations..."

CONFIGBACKUP="$BACKUP_DIR/config_$TIMESTAMP.tar.gz"

CONFIG_ITEMS=(
  docker-compose.pc1.yml
  docker-compose.pc2.yml
  monitoring
  backend/docker
  frontend/docker
  .github/workflows
)

OPTIONAL_ITEMS=(
  .env.pc1
  .env.pc2
  .env.pc1.example
  .env.pc2.example
)

for item in "${OPTIONAL_ITEMS[@]}"; do
  if [ -e "$item" ]; then
    CONFIG_ITEMS+=("$item")
  fi
done

tar -czf "$CONFIGBACKUP" "${CONFIG_ITEMS[@]}"

if [ -f "$CONFIGBACKUP" ]; then
  SIZE=$(du -h "$CONFIGBACKUP" | cut -f1)
  echo "✅ Configuration backup: $CONFIGBACKUP ($SIZE)"
fi

echo "🧹 Cleaning old backups (older than $RETENTION_DAYS days)..."

find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete

BACKUP_COUNT=$(find "$BACKUP_DIR" -type f | wc -l)
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo "✅ Backup complete!"
echo "📊 Status:"
echo "   Files: $BACKUP_COUNT"
echo "   Size: $BACKUP_SIZE"
echo "   Location: $BACKUP_DIR"
