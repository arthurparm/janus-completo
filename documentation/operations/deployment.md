# Janus Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Janus multi-agent AI system across different environments, from local development to production.

## Deployment Environments

### 1. Local Development

#### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local backend development)
- Node.js 20+ (for local frontend development)
- Git

#### Quick Start (Recommended)
```bash
# Clone repository
git clone <repository-url>
cd janus-completo

# One-command bootstrap
python tooling/dev.py up
```

#### Manual Setup
```bash
# Start infrastructure services (PC2)
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d

# Start application services (PC1)
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d

# Verify deployment
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/api/v1/system/status
```

### 2. Staging Environment

#### Environment Configuration
```bash
# Copy environment templates
cp .env.pc1.example .env.pc1.staging
cp .env.pc2.example .env.pc2.staging

# Configure staging-specific variables
# Update API keys, database connections, and resource limits
```

#### Deployment Steps
```bash
# Build images with staging tags
docker build -f backend/docker/Dockerfile -t janus-api:staging backend/
docker build -f frontend/docker/Dockerfile -t janus-frontend:staging frontend/

# Deploy infrastructure
docker compose -f docker-compose.pc2.yml --env-file .env.pc2.staging up -d

# Deploy application
docker compose -f docker-compose.pc1.yml --env-file .env.pc1.staging up -d
```

### 3. Production Environment

#### Pre-Deployment Checklist
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Security policies applied
- [ ] Resource limits defined
- [ ] Health checks configured

#### Production Deployment
```bash
# Use production environment files
docker compose -f docker-compose.pc2.yml --env-file .env.pc2.prod up -d
docker compose -f docker-compose.pc1.yml --env-file .env.pc1.prod up -d

# Verify all services are healthy
docker compose -f docker-compose.pc1.yml --env-file .env.pc1.prod ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2.prod ps
```

## Service Dependencies

### Startup Order
1. **PC2 Services** (must start first):
   - Neo4j (graph database)
   - Qdrant (vector database)
   - Ollama (LLM service)

2. **PC1 Services** (start after PC2):
   - PostgreSQL (relational database)
   - Redis (cache)
   - RabbitMQ (message queue)
   - Janus API (backend)
   - Janus Frontend (UI)

### Health Check URLs
```bash
# API Health
curl -sf http://localhost:8000/health
curl -sf http://localhost:8000/healthz

# System Status
curl -sf http://localhost:8000/api/v1/system/status
curl -sf http://localhost:8000/api/v1/workers/status

# Database Connections
curl -sf http://localhost:8000/api/v1/system/health/db
curl -sf http://localhost:8000/api/v1/system/health/cache
```

## Configuration Management

### Environment Variables

#### Required Variables (PC1)
```bash
# Authentication
AUTH_JWT_SECRET=<secure-random-string>
AUTH_ADMIN_CPF_ALLOWLIST=<admin-cpf-list>

# Database
POSTGRES_PASSWORD=<secure-password>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=janus
POSTGRES_DB=janus_db

# Redis
REDIS_URL=redis://redis:6379

# RabbitMQ
RABBITMQ_PASSWORD=<secure-password>
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

# External Services (PC2)
NEO4J_URI=bolt://<pc2-ip>:7687
NEO4J_PASSWORD=<secure-password>
QDRANT_HOST=<pc2-ip>
QDRANT_API_KEY=<qdrant-api-key>
OLLAMA_HOST=http://<pc2-ip>:11434
```

#### Required Variables (PC2)
```bash
# Neo4j
NEO4J_AUTH=neo4j/<secure-password>

# Qdrant
QDRANT__SERVICE__API_KEY=<qdrant-api-key>

# Ollama
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
```

### SSL/TLS Configuration

#### Production SSL Setup
```bash
# Generate SSL certificates (using Let's Encrypt)
certbot certonly --standalone -d your-domain.com

# Update nginx configuration or application settings
# Mount certificates in Docker containers
```

#### Self-Signed Certificates (Development)
```bash
# Generate self-signed certificates
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Monitoring and Observability

### Key Metrics to Monitor
- API response times
- Error rates
- Database connection pool usage
- Memory and CPU usage
- Queue depths (RabbitMQ)
- Cache hit rates (Redis)

### Log Aggregation
```bash
# View logs by service
docker compose -f docker-compose.pc1.yml logs -f janus-api
docker compose -f docker-compose.pc2.yml logs -f neo4j

# Filter logs by level
docker compose logs | grep ERROR
docker compose logs | grep WARN
```

### Alerting Configuration
Set up alerts for:
- Service downtime
- High error rates (>5%)
- Database connection failures
- Memory usage >80%
- Disk space <20%

## Rollback Procedures

### Quick Rollback
```bash
# Stop current services
docker compose -f docker-compose.pc1.yml down
docker compose -f docker-compose.pc2.yml down

# Restore previous version
git checkout <previous-stable-commit>

# Rebuild and restart
docker compose -f docker-compose.pc2.yml up -d --build
docker compose -f docker-compose.pc1.yml up -d --build
```

### Database Rollback
```bash
# Restore from backup
./tooling/restore-stack.sh --backup-dir outputs/backups/<timestamp> --force

# Verify restoration
curl -sf http://localhost:8000/health
docker compose -f docker-compose.pc1.yml ps
```

## Troubleshooting Common Issues

### Service Startup Failures
```bash
# Check service logs
docker compose logs <service-name>

# Verify port availability
netstat -tulpn | grep <port>

# Check resource usage
docker stats
```

### Database Connection Issues
```bash
# Test database connectivity
docker exec -it janus_postgres pg_isready -U janus
docker exec -it janus_neo4j cypher-shell -u neo4j -p <password>

# Check network connectivity between services
docker network ls
docker network inspect <network-name>
```

### Performance Issues
```bash
# Monitor resource usage
docker stats --no-stream

# Check slow queries (PostgreSQL)
docker exec -it janus_postgres psql -U janus -d janus_db -c "SELECT * FROM pg_stat_activity;"

# Analyze API performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/health
```

## Security Considerations

### Network Security
- Use Tailscale VPN for PC1/PC2 communication
- Implement firewall rules for exposed ports
- Regular security updates for base images

### Access Control
- Strong passwords for all services
- Regular key rotation
- Principle of least privilege
- Audit logging enabled

### Data Protection
- Encrypted connections (TLS 1.3+)
- Sensitive data encryption at rest
- Regular backup encryption
- Secure secret management

## Backup and Disaster Recovery

### Automated Backups
```bash
# Create backup
./tooling/backup-stack.sh --skip-ollama

# Backup includes:
# - Database dumps
# - Configuration files
# - User data (excluding large models)
```

### Disaster Recovery Plan
1. **Detection**: Monitor service health
2. **Assessment**: Determine scope of failure
3. **Recovery**: Restore from backup or failover
4. **Verification**: Test all services
5. **Documentation**: Record incident and lessons learned

## Performance Optimization

### Resource Allocation
```yaml
# Example resource limits in docker-compose
services:
  janus-api:
    mem_limit: 4g
    cpus: "4.0"
    
  postgres:
    mem_limit: 2g
    cpus: "2.0"
```

### Database Optimization
- Connection pooling configuration
- Query optimization
- Index maintenance
- Regular VACUUM operations

### Cache Optimization
- Redis memory allocation
- Cache key strategies
- TTL configuration
- Cache invalidation patterns

---

*This deployment guide is maintained by the Janus operations team. For updates and changes, please submit PRs with appropriate review.*