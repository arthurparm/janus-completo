#!/usr/bin/env bash
# Manage Janus Docker Compose services for PC1 and PC2

set -e

COMPOSE_PC1="docker-compose.pc1.yml"
COMPOSE_PC2="docker-compose.pc2.yml"

usage() {
    cat << EOF
Usage: $0 <command> <environment>

Commands:
  up       - Start services
  down     - Stop and remove containers
  logs     - Show service logs
  status   - Show service status
  rebuild  - Rebuild images
  clean    - Remove stopped containers and unused images

Environments:
  pc1      - API, Frontend, Database services
  pc2      - GPU services (Neo4j, Qdrant, Ollama)
  all      - Both environments

Examples:
  $0 up pc1          # Start PC1 services
  $0 logs pc2        # Show PC2 logs
  $0 down all        # Stop both PC1 and PC2
  $0 rebuild pc1     # Rebuild PC1 images

EOF
    exit 1
}

if [ $# -lt 2 ]; then
    usage
fi

COMMAND=$1
ENV=$2

# Validate environment
case $ENV in
    pc1|pc2|all) ;;
    *) echo "❌ Invalid environment: $ENV"; usage ;;
esac

# Build compose files list
if [ "$ENV" = "all" ]; then
    COMPOSES=("$COMPOSE_PC1" "$COMPOSE_PC2")
elif [ "$ENV" = "pc1" ]; then
    COMPOSES=("$COMPOSE_PC1")
else
    COMPOSES=("$COMPOSE_PC2")
fi

case $COMMAND in
    up)
        for compose in "${COMPOSES[@]}"; do
            echo "🚀 Starting $compose..."
            docker compose -f "$compose" up -d
            echo "✅ $compose running"
        done
        echo ""
        docker compose -f "${COMPOSES[0]}" ps
        ;;
    
    down)
        for compose in "${COMPOSES[@]}"; do
            echo "🛑 Stopping $compose..."
            docker compose -f "$compose" down
        done
        ;;
    
    logs)
        if [ ${#COMPOSES[@]} -eq 1 ]; then
            docker compose -f "${COMPOSES[0]}" logs -f --tail 100
        else
            echo "Showing logs from multiple environments. Use: $0 logs pc1  or  $0 logs pc2"
            docker compose -f "$COMPOSE_PC1" logs -f --tail 50 &
            docker compose -f "$COMPOSE_PC2" logs -f --tail 50 &
            wait
        fi
        ;;
    
    status)
        for compose in "${COMPOSES[@]}"; do
            echo "Status for $compose:"
            docker compose -f "$compose" ps
            echo ""
        done
        ;;
    
    rebuild)
        for compose in "${COMPOSES[@]}"; do
            echo "🔨 Rebuilding images for $compose..."
            docker compose -f "$compose" build --no-cache
        done
        echo "✅ Rebuild complete"
        ;;
    
    clean)
        echo "🧹 Cleaning up Docker resources..."
        docker container prune -f --filter "label!=keep"
        docker image prune -f --filter "dangling=true"
        echo "✅ Cleanup complete"
        ;;
    
    *)
        echo "❌ Unknown command: $COMMAND"
        usage
        ;;
esac
