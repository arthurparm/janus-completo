# Starts only infrastructure services (without API/frontend) using PC1/PC2 split stacks.

Write-Host "Starting infrastructure services (PC2 + PC1 data plane)..." -ForegroundColor Cyan

docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d postgres redis rabbitmq

Write-Host "Services started." -ForegroundColor Green
Write-Host "  Neo4j:    bolt://localhost:7687"
Write-Host "  Qdrant:   http://localhost:6333"
Write-Host "  Ollama:   http://localhost:11434"
Write-Host "  RabbitMQ: http://localhost:15672"
