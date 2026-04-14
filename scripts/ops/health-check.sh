#!/usr/bin/env bash
# Monitor Janus services health and connectivity

set -e

echo "🏥 Janus Health & Connectivity Check"
echo "═══════════════════════════════════════════════════════════════"
echo ""

check_container() {
    local container=$1
    local service=$2
    
    if docker ps -q -f "name=$container" | grep -q .; then
        echo "✅ $service (running)"
        return 0
    elif docker ps -aq -f "name=$container" | grep -q .; then
        echo "❌ $service (stopped)"
        return 1
    else
        echo "⚠️  $service (not found)"
        return 2
    fi
}

check_port() {
    local port=$1
    local service=$2
    
    if timeout 1 bash -c "echo >/dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        echo "  ✅ Port $port open ($service)"
        return 0
    else
        echo "  ❌ Port $port closed ($service)"
        return 1
    fi
}

echo "PC1 Services:"
echo "───────────────────────────────────────────────────────────────"
check_container "janus_api_pc1" "API"
check_container "janus_frontend_pc1" "Frontend"
check_container "janus_postgres_pc1" "PostgreSQL"
check_container "janus_redis_pc1" "Redis"
check_container "janus_rabbitmq_pc1" "RabbitMQ"

echo ""
echo "PC1 Port Connectivity:"
echo "───────────────────────────────────────────────────────────────"
check_port 8000 "API"
check_port 4300 "Frontend"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 5672 "RabbitMQ"

echo ""
echo "PC2 Services:"
echo "───────────────────────────────────────────────────────────────"
check_container "janus_neo4j_pc2" "Neo4j"
check_container "janus_qdrant_pc2" "Qdrant"
check_container "janus_ollama_pc2" "Ollama"

echo ""
echo "PC2 Port Connectivity:"
echo "───────────────────────────────────────────────────────────────"
check_port 7687 "Neo4j Bolt" || true
check_port 6333 "Qdrant" || true
check_port 11434 "Ollama" || true

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Service Logs (last 10 lines per service):"
echo "───────────────────────────────────────────────────────────────"

for compose in docker-compose.pc1.yml docker-compose.pc2.yml; do
    if [ -f "$compose" ]; then
        echo ""
        echo "Logs from $compose:"
        docker compose -f "$compose" logs --tail 5 --no-log-prefix 2>/dev/null | head -20 || echo "  (compose not running)"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Troubleshooting Tips:"
echo "  • Check logs: docker compose -f docker-compose.pc1.yml logs -f"
echo "  • Restart service: docker compose -f docker-compose.pc1.yml restart <service>"
echo "  • Rebuild image: docker compose -f docker-compose.pc1.yml build --no-cache"
echo "  • View config: docker compose -f docker-compose.pc1.yml config"
