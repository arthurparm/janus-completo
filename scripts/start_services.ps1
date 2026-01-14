# Starts only the infrastructure services (databases, queues, etc.)
# skipping the Janus API and Frontend since they will be run locally.

Write-Host "🐳 Starting Infrastructure Services..." -ForegroundColor Cyan

docker compose up -d neo4j postgres redis qdrant rabbitmq ollama

Write-Host "✅ Services started!" -ForegroundColor Green
Write-Host "   Neo4j: http://localhost:7474"
Write-Host "   RabbitMQ: http://localhost:15672"
Write-Host "   Grafana: http://localhost:3000"
