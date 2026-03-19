# Guia de Deployment e DevOps - Janus

## Visão Geral

Este guia descreve as práticas de deployment, pipelines CI/CD, infraestrutura como código (IaC) e operações de DevOps para o projeto Janus, cobrindo desde o desenvolvimento local até produção.

## Arquitetura de Deployment

### Pipeline CI/CD Completo

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Developer     │───▶│   Build & Test  │───▶│   Deploy Staging│───▶│   Deploy Prod   │
│   Commit        │    │   (CI)          │    │   (CD)          │    │   (CD)          │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Code Review   │    │   Security Scan │    │   Integration   │    │   Monitoring    │
│   (PR)          │    │   (SAST/DAST)   │    │   Tests         │    │   & Alerts      │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Ambientes de Deployment

| Ambiente | Branch | URL | Propósito |
|----------|--------|-----|-----------|
| **Development** | `develop` | `https://dev.janus.com` | Desenvolvimento diário |
| **Staging** | `staging` | `https://staging.janus.com` | Testes de integração |
| **Production** | `main` | `https://janus.com` | Produção |
| **Feature** | `feature/*` | `https://feature-{name}.janus.com` | Features em desenvolvimento |

## Configuração de CI/CD

### 1. GitHub Actions Workflows

#### Workflow Principal (CI/CD)

```yaml
# .github/workflows/main.yml
name: Janus CI/CD Pipeline

on:
  push:
    branches: [main, develop, staging]
  pull_request:
    branches: [main, develop]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Análise de código e segurança
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Backend Lint & Type Check
        run: |
          cd backend
          pip install ruff mypy
          ruff check --config pyproject.toml .
          mypy --config-file pyproject.toml --follow-imports=skip app/
      
      - name: Frontend Lint & Build
        run: |
          cd frontend
          npm ci
          npm run lint
          npm run build -- --configuration development
      
      - name: Security Scan
        uses: securecodewarrior/github-action-add-sarif@v1
        with:
          sarif-file: 'security-scan.sarif'

  # Testes automatizados
  tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: janus_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest -v --cov=app --cov-report=xml
      
      - name: Frontend Tests
        run: |
          cd frontend
          npm ci
          npm run test -- --watch=false --browsers=ChromeHeadless
      
      - name: Integration Tests
        run: |
          docker compose -f docker-compose.test.yml up -d
          sleep 30
          python -m pytest qa/ -v
          docker compose -f docker-compose.test.yml down

  # Build e push de containers
  build:
    needs: [code-quality, tests]
    runs-on: ubuntu-latest
    outputs:
      backend-image: ${{ steps.backend.outputs.image }}
      frontend-image: ${{ steps.frontend.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build Backend
        id: backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build Frontend
        id: frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Deploy para staging
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to Staging
        run: |
          # Atualizar imagens no docker-compose
          sed -i "s|janus-backend:latest|${{ needs.build.outputs.backend-image }}|g" docker-compose.staging.yml
          sed -i "s|janus-frontend:latest|${{ needs.build.outputs.frontend-image }}|g" docker-compose.staging.yml
          
          # Deploy via SSH
          ssh -o StrictHostKeyChecking=no ${{ secrets.STAGING_SSH_USER }}@${{ secrets.STAGING_HOST }} << 'EOF'
            cd /opt/janus
            docker compose -f docker-compose.staging.yml pull
            docker compose -f docker-compose.staging.yml up -d
            
            # Health check
            for i in {1..30}; do
              if curl -sf http://localhost:8000/health >/dev/null; then
                echo "Health check passed"
                break
              fi
              sleep 2
            done
            
            if [ $i -eq 30 ]; then
              echo "Health check failed"
              exit 1
            fi
          EOF

  # Deploy para produção
  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to Production
        run: |
          # Blue-green deployment
          ssh -o StrictHostKeyChecking=no ${{ secrets.PROD_SSH_USER }}@${{ secrets.PROD_HOST }} << 'EOF'
            cd /opt/janus
            
            # Deploy para ambiente blue
            echo "Deploying to blue environment..."
            docker compose -f docker-compose.prod.blue.yml pull
            docker compose -f docker-compose.prod.blue.yml up -d
            
            # Health check no blue
            for i in {1..60}; do
              if curl -sf http://localhost:8001/health >/dev/null; then
                echo "Blue health check passed"
                break
              fi
              sleep 2
            done
            
            if [ $i -eq 60 ]; then
              echo "Blue health check failed - rollback"
              docker compose -f docker-compose.prod.blue.yml down
              exit 1
            fi
            
            # Switch traffic para blue
            echo "Switching traffic to blue..."
            sudo nginx -s reload
            
            # Esperar estabilização
            sleep 30
            
            # Atualizar green (para próximo deploy)
            echo "Updating green environment..."
            docker compose -f docker-compose.prod.green.yml pull
            docker compose -f docker-compose.prod.green.yml up -d
            
            echo "Production deployment completed"
          EOF
```

#### Workflow de Feature Branch

```yaml
# .github/workflows/feature-deploy.yml
name: Feature Branch Deploy

on:
  push:
    branches: ['feature/**']

jobs:
  deploy-feature:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Extract branch name
        shell: bash
        run: echo "branch=${GITHUB_REF#refs/heads/}" >> $GITHUB_OUTPUT
        id: extract_branch
      
      - name: Deploy Feature Environment
        run: |
          BRANCH_NAME=$(echo "${{ steps.extract_branch.outputs.branch }}" | sed 's/feature\///')
          
          ssh -o StrictHostKeyChecking=no ${{ secrets.FEATURE_SSH_USER }}@${{ secrets.FEATURE_HOST }} << EOF
            cd /opt/janus-features
            
            # Criar ambiente para feature
            mkdir -p $BRANCH_NAME
            cd $BRANCH_NAME
            
            # Copiar configurações
            cp ../docker-compose.feature.yml ./docker-compose.yml
            
            # Atualizar para branch específica
            git clone -b ${{ steps.extract_branch.outputs.branch }} ${{ secrets.REPO_URL }} .
            
            # Deploy
            docker compose up -d --build
            
            echo "Feature environment deployed at: https://$BRANCH_NAME.janus-dev.com"
          EOF
```

### 2. Configuração de Secrets

Configure os seguintes secrets no GitHub:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# SSH Access
STAGING_SSH_USER=ubuntu
STAGING_HOST=staging.janus.com
PROD_SSH_USER=ubuntu
PROD_HOST=janus.com
FEATURE_SSH_USER=ubuntu
FEATURE_HOST=features.janus-dev.com

# Registry Credentials
REGISTRY_USERNAME=github-username
REGISTRY_PASSWORD=github-token

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPEN_ROUTER_API_KEY=sk-or-...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/janus
REDIS_URL=redis://host:6379/0

# Monitoring
PAGERDUTY_API_KEY=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

## Infraestrutura como Código (IaC)

### 1. Terraform para AWS

```hcl
# infrastructure/terraform/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "janus_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "janus-vpc"
    Environment = var.environment
    Project     = "janus"
  }
}

# Subnets Públicas
resource "aws_subnet" "public_subnets" {
  count             = 2
  vpc_id            = aws_vpc.janus_vpc.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name        = "janus-public-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "public"
  }
}

# Subnets Privadas
resource "aws_subnet" "private_subnets" {
  count             = 2
  vpc_id            = aws_vpc.janus_vpc.id
  cidr_block        = "10.0.${count.index + 3}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "janus-private-subnet-${count.index + 1}"
    Environment = var.environment
    Type        = "private"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "janus_igw" {
  vpc_id = aws_vpc.janus_vpc.id

  tags = {
    Name        = "janus-igw"
    Environment = var.environment
  }
}

# NAT Gateway
resource "aws_eip" "nat_eip" {
  count  = 2
  domain = "vpc"

  tags = {
    Name        = "janus-nat-eip-${count.index + 1}"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "janus_nat" {
  count         = 2
  allocation_id = aws_eip.nat_eip[count.index].id
  subnet_id     = aws_subnet.public_subnets[count.index].id

  tags = {
    Name        = "janus-nat-${count.index + 1}"
    Environment = var.environment
  }
}

# Route Tables
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.janus_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.janus_igw.id
  }

  tags = {
    Name        = "janus-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table" "private_rt" {
  count  = 2
  vpc_id = aws_vpc.janus_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.janus_nat[count.index].id
  }

  tags = {
    Name        = "janus-private-rt-${count.index + 1}"
    Environment = var.environment
  }
}

# Security Groups
resource "aws_security_group" "janus_backend_sg" {
  name        = "janus-backend-sg"
  description = "Security group for Janus backend"
  vpc_id      = aws_vpc.janus_vpc.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "janus-backend-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "janus_frontend_sg" {
  name        = "janus-frontend-sg"
  description = "Security group for Janus frontend"
  vpc_id      = aws_vpc.janus_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "janus-frontend-sg"
    Environment = var.environment
  }
}

# RDS - PostgreSQL
resource "aws_db_subnet_group" "janus_db_subnet_group" {
  name       = "janus-db-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id

  tags = {
    Name        = "janus-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_db_instance" "janus_postgres" {
  identifier             = "janus-postgres-${var.environment}"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = var.db_instance_class
  allocated_storage      = 100
  max_allocated_storage  = 1000
  storage_type           = "gp3"
  storage_encrypted      = true

  db_name  = "janus"
  username = "janus_admin"
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.janus_db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.janus_db_subnet_group.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  deletion_protection = var.environment == "production"
  skip_final_snapshot = var.environment != "production"

  tags = {
    Name        = "janus-postgres"
    Environment = var.environment
  }
}

# ElastiCache - Redis
resource "aws_elasticache_subnet_group" "janus_redis_subnet_group" {
  name       = "janus-redis-subnet-group"
  subnet_ids = aws_subnet.private_subnets[*].id
}

resource "aws_elasticache_replication_group" "janus_redis" {
  replication_group_id       = "janus-redis-${var.environment}"
  description                = "Redis cluster for Janus"
  
  node_type                  = var.redis_node_type
  port                      = 6379
  parameter_group_name      = "default.redis7"
  
  num_cache_clusters        = 2
  automatic_failover_enabled = true
  
  subnet_group_name         = aws_elasticache_subnet_group.janus_redis_subnet_group.name
  security_group_ids       = [aws_security_group.janus_redis_sg.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled  = true
  
  tags = {
    Name        = "janus-redis"
    Environment = var.environment
  }
}

# Application Load Balancer
resource "aws_lb" "janus_alb" {
  name               = "janus-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.janus_alb_sg.id]
  subnets           = aws_subnet.public_subnets[*].id

  enable_deletion_protection = var.environment == "production"

  tags = {
    Name        = "janus-alb"
    Environment = var.environment
  }
}

# Auto Scaling Groups
resource "aws_launch_template" "janus_backend_lt" {
  name_prefix   = "janus-backend-${var.environment}-"
  image_id      = data.aws_ami.ubuntu.id
  instance_type = var.backend_instance_type

  vpc_security_group_ids = [aws_security_group.janus_backend_sg.id]

  user_data = base64encode(templatefile("${path.module}/templates/backend_user_data.sh", {
    environment = var.environment
    db_host     = aws_db_instance.janus_postgres.endpoint
    redis_host  = aws_elasticache_replication_group.janus_redis.primary_endpoint_address
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "janus-backend"
      Environment = var.environment
      Project     = "janus"
    }
  }
}

resource "aws_autoscaling_group" "janus_backend_asg" {
  name                = "janus-backend-asg-${var.environment}"
  vpc_zone_identifier = aws_subnet.private_subnets[*].id
  target_group_arns   = [aws_lb_target_group.janus_backend_tg.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.backend_min_size
  max_size         = var.backend_max_size
  desired_capacity = var.backend_desired_capacity

  launch_template {
    id      = aws_launch_template.janus_backend_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "janus-backend-asg"
    propagate_at_launch = false
  }
}
```

### 2. Kubernetes Manifests

```yaml
# infrastructure/k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: janus
  labels:
    name: janus
    environment: production
```

```yaml
# infrastructure/k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: janus-backend
  namespace: janus
  labels:
    app: janus-backend
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: janus-backend
  template:
    metadata:
      labels:
        app: janus-backend
        version: v1
    spec:
      containers:
      - name: janus-backend
        image: ghcr.io/janus-completo/janus-backend:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: janus-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: janus-secrets
              key: redis-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: janus-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: janus-backend-config
```

```yaml
# infrastructure/k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: janus-frontend
  namespace: janus
  labels:
    app: janus-frontend
    version: v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: janus-frontend
  template:
    metadata:
      labels:
        app: janus-frontend
        version: v1
    spec:
      containers:
      - name: janus-frontend
        image: ghcr.io/janus-completo/janus-frontend:latest
        ports:
        - containerPort: 80
          name: http
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
```

```yaml
# infrastructure/k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: janus-backend-hpa
  namespace: janus
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: janus-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Docker Compose para Diferentes Ambientes

### 1. Desenvolvimento Local

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  janus-api:
    build:
      context: ./backend
      dockerfile: docker/Dockerfile
      target: development
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://janus:janus@postgres:5432/janus_dev
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPEN_ROUTER_API_KEY=${OPEN_ROUTER_API_KEY}
    volumes:
      - ./backend:/app
      - /app/.venv
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  janus-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: development
    ports:
      - "4200:4200"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - CHOKIDAR_USEPOLLING=true
    command: npm start

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: janus_dev
      POSTGRES_USER: janus
      POSTGRES_PASSWORD: janus
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U janus -d janus_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.dev.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - janus-api
      - janus-frontend

volumes:
  postgres_data:
  redis_data:
  neo4j_data:
  qdrant_data:
  ollama_data:

networks:
  default:
    driver: bridge
```

### 2. Produção com Alta Disponibilidade

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  janus-api-blue:
    image: ghcr.io/janus-completo/janus-backend:${VERSION:-latest}
    ports:
      - "8001:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPEN_ROUTER_API_KEY=${OPEN_ROUTER_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        monitor: 60s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  janus-api-green:
    image: ghcr.io/janus-completo/janus-backend:${VERSION:-latest}
    ports:
      - "8002:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPEN_ROUTER_API_KEY=${OPEN_ROUTER_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        monitor: 60s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  janus-frontend:
    image: ghcr.io/janus-completo/janus-frontend:${VERSION:-latest}
    ports:
      - "3000:80"
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - ./nginx/conf.d:/etc/nginx/conf.d
    depends_on:
      - janus-api-blue
      - janus-api-green
      - janus-frontend
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.prod.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.prod.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=https://alerts.janus.com'
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.25'
          memory: 512M
        reservations:
          cpus: '0.1'
          memory: 256M

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  default:
    driver: overlay
    attachable: true
```

## Scripts de Deployment

### 1. Script de Deploy Automatizado

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
DRY_RUN=${3:-false}

echo "🚀 Iniciando deployment para $ENVIRONMENT"

# Validar ambiente
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    echo "❌ Ambiente inválido. Use: development, staging ou production"
    exit 1
fi

# Configurações baseadas no ambiente
case $ENVIRONMENT in
    development)
        COMPOSE_FILE="docker-compose.dev.yml"
        HOST="localhost"
        ;;
    staging)
        COMPOSE_FILE="docker-compose.staging.yml"
        HOST="staging.janus.com"
        ;;
    production)
        COMPOSE_FILE="docker-compose.prod.yml"
        HOST="janus.com"
        ;;
esac

# Dry run - apenas simular
if [ "$DRY_RUN" = true ]; then
    echo "🔍 Dry run ativado - simulando deployment..."
    echo "Arquivo compose: $COMPOSE_FILE"
    echo "Host: $HOST"
    echo "Versão: $VERSION"
    exit 0
fi

# Backup do banco de dados (produção)
if [ "$ENVIRONMENT" = "production" ]; then
    echo "💾 Criando backup do banco de dados..."
    ssh $HOST "cd /opt/janus && ./scripts/backup-database.sh"
fi

# Deploy
if [ "$ENVIRONMENT" = "development" ]; then
    echo "🏗️  Deploy local..."
    docker compose -f $COMPOSE_FILE down
    docker compose -f $COMPOSE_FILE pull
    docker compose -f $COMPOSE_FILE up -d
else
    echo "🏗️  Deploy remoto..."
    
    # Copiar arquivos
    rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
        . $HOST:/opt/janus/
    
    # Executar deployment no servidor
    ssh $HOST << EOF
        cd /opt/janus
        
        # Atualizar variáveis de ambiente
        export VERSION=$VERSION
        
        # Parar serviços antigos
        docker compose -f $COMPOSE_FILE down --remove-orphans
        
        # Limpar imagens antigas
        docker system prune -af --volumes
        
        # Pull das novas imagens
        docker compose -f $COMPOSE_FILE pull
        
        # Iniciar novos serviços
        docker compose -f $COMPOSE_FILE up -d
        
        # Aguardar health check
        echo "⏳ Aguardando health check..."
        for i in {1..60}; do
            if curl -sf http://localhost:8000/health >/dev/null; then
                echo "✅ Health check passou!"
                break
            fi
            echo "⏳ Aguardando... (i/60)"
            sleep 2
        done
        
        if [ \$i -eq 60 ]; then
            echo "❌ Health check falhou!"
            exit 1
        fi
        
        echo "✅ Deployment concluído com sucesso!"
EOF
fi

# Verificação pós-deploy
echo "🔍 Verificando deployment..."
sleep 10

# Testar endpoints principais
endpoints=(
    "/health"
    "/api/v1/system/status"
    "/api/v1/observability/slo/domains"
)

for endpoint in "\${endpoints[@]}"; do
    if curl -sf "http://$HOST$endpoint" >/dev/null; then
        echo "✅ $endpoint - OK"
    else
        echo "❌ $endpoint - FALHOU"
        exit 1
    fi
done

# Notificar equipe
echo "📢 Enviando notificação..."
curl -X POST "${SLACK_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d @- << EOF
{
    "text": "🚀 Deployment concluído!",
    "attachments": [
        {
            "color": "good",
            "fields": [
                {
                    "title": "Ambiente",
                    "value": "$ENVIRONMENT",
                    "short": true
                },
                {
                    "title": "Versão",
                    "value": "$VERSION",
                    "short": true
                },
                {
                    "title": "Status",
                    "value": "✅ Sucesso",
                    "short": true
                },
                {
                    "title": "URL",
                    "value": "https://$HOST",
                    "short": true
                }
            ],
            "footer": "Janus Deployment",
            "ts": $(date +%s)
        }
    ]
}
EOF

echo "🎉 Deployment finalizado com sucesso!"
```

### 2. Script de Rollback

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

ENVIRONMENT=${1:-staging}
BACKUP_VERSION=${2:-previous}

echo "🔄 Iniciando rollback para $ENVIRONMENT"

# Validar ambiente
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo "❌ Ambiente inválido. Use: staging ou production"
    exit 1
fi

# Configurações baseadas no ambiente
case $ENVIRONMENT in
    staging)
        HOST="staging.janus.com"
        COMPOSE_FILE="docker-compose.staging.yml"
        ;;
    production)
        HOST="janus.com"
        COMPOSE_FILE="docker-compose.prod.yml"
        ;;
esac

# Obter versão anterior
if [ "$BACKUP_VERSION" = "previous" ]; then
    echo "📋 Buscando versão anterior..."
    PREVIOUS_VERSION=$(ssh $HOST "cd /opt/janus && cat .last-successful-version 2>/dev/null || echo 'latest'")
    echo "📦 Versão anterior: $PREVIOUS_VERSION"
else
    PREVIOUS_VERSION=$BACKUP_VERSION
fi

# Confirmar rollback
read -p "⚠️  Deseja realmente fazer rollback para $PREVIOUS_VERSION? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Rollback cancelado"
    exit 0
fi

# Executar rollback
ssh $HOST << EOF
    cd /opt/janus
    
    echo "🔄 Iniciando rollback..."
    
    # Parar serviços atuais
    docker compose -f $COMPOSE_FILE down --remove-orphans
    
    # Restaurar versão anterior
    export VERSION=$PREVIOUS_VERSION
    
    # Pull da versão anterior
    docker compose -f $COMPOSE_FILE pull
    
    # Iniciar serviços anteriores
    docker compose -f $COMPOSE_FILE up -d
    
    # Aguardar health check
    echo "⏳ Verificando health check..."
    for i in {1..60}; do
        if curl -sf http://localhost:8000/health >/dev/null; then
            echo "✅ Health check passou!"
            break
        fi
        echo "⏳ Aguardando... (\$i/60)"
        sleep 2
    done
    
    if [ \$i -eq 60 ]; then
        echo "❌ Health check falhou!"
        exit 1
    fi
    
    echo "✅ Rollback concluído!"
EOF

# Notificar equipe
curl -X POST "${SLACK_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d @- << EOF
{
    "text": "🔄 Rollback concluído!",
    "attachments": [
        {
            "color": "warning",
            "fields": [
                {
                    "title": "Ambiente",
                    "value": "$ENVIRONMENT",
                    "short": true
                },
                {
                    "title": "Versão Anterior",
                    "value": "$PREVIOUS_VERSION",
                    "short": true
                },
                {
                    "title": "Status",
                    "value": "✅ Sucesso",
                    "short": true
                },
                {
                    "title": "Horário",
                    "value": "$(date)",
                    "short": true
                }
            ],
            "footer": "Janus Rollback",
            "ts": $(date +%s)
        }
    ]
}
EOF

echo "🎉 Rollback finalizado com sucesso!"
```

## Monitoramento e Observabilidade

### 1. Configuração de Logs Centralizados

```yaml
# infrastructure/logging/fluentd-config.yaml
<source>
  @type tail
  path /var/log/janus/*.log
  pos_file /var/log/fluentd/janus.log.pos
  tag janus.logs
  format json
  time_format %Y-%m-%d %H:%M:%S
</source>

<filter janus.logs>
  @type record_transformer
  <record>
    hostname ${hostname}
    environment ${ENVIRONMENT}
    service janus
  </record>
</filter>

<match janus.logs>
  @type elasticsearch
  host elasticsearch.janus.com
  port 9200
  index_name janus-logs
  type_name _doc
  logstash_format true
  logstash_prefix janus
  logstash_dateformat %Y%m%d
  include_tag_key true
  tag_key @log_name
  <buffer>
    @type file
    path /var/log/fluentd/buffer/elasticsearch
    flush_interval 10s
  </buffer>
</match>
```

### 2. Dashboard de Deployment

```json
{
  "dashboard": {
    "title": "Janus - Deployment Metrics",
    "panels": [
      {
        "title": "Deployment Frequency",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(deployment_total[1d])",
            "legendFormat": "Deployments per day"
          }
        ]
      },
      {
        "title": "Lead Time for Changes",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, lead_time_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Change Failure Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(deployment_failures_total[1w]) / rate(deployment_total[1w])",
            "legendFormat": "Failure rate"
          }
        ]
      },
      {
        "title": "Time to Restore Service",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, mttr_seconds_bucket)",
            "legendFormat": "95th percentile MTTR"
          }
        ]
      }
    ]
  }
}
```

## Boas Práticas e Padrões

### 1. Versionamento Semântico

```bash
# scripts/version.sh
#!/bin/bash

# Obter próxima versão baseada em conventional commits
get_next_version() {
    CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    
    # Analisar commits desde última tag
    COMMITS=$(git log ${CURRENT_VERSION}..HEAD --pretty=format:"%s")
    
    # Detectar tipo de mudança
    MAJOR=false
    MINOR=false
    PATCH=false
    
    while IFS= read -r commit; do
        if [[ $commit =~ ^(BREAKING CHANGE|major): ]]; then
            MAJOR=true
        elif [[ $commit =~ ^(feat|feature|minor): ]]; then
            MINOR=true
        elif [[ $commit =~ ^(fix|patch): ]]; then
            PATCH=true
        fi
    done <<< "$COMMITS"
    
    # Calcular próxima versão
    IFS='.' read -ra VERSION_PARTS <<< "${CURRENT_VERSION#v}"
    MAJOR_VERSION=${VERSION_PARTS[0]}
    MINOR_VERSION=${VERSION_PARTS[1]}
    PATCH_VERSION=${VERSION_PARTS[2]}
    
    if [ "$MAJOR" = true ]; then
        MAJOR_VERSION=$((MAJOR_VERSION + 1))
        MINOR_VERSION=0
        PATCH_VERSION=0
    elif [ "$MINOR" = true ]; then
        MINOR_VERSION=$((MINOR_VERSION + 1))
        PATCH_VERSION=0
    elif [ "$PATCH" = true ]; then
        PATCH_VERSION=$((PATCH_VERSION + 1))
    fi
    
    echo "v${MAJOR_VERSION}.${MINOR_VERSION}.${PATCH_VERSION}"
}

# Criar nova versão
NEW_VERSION=$(get_next_version)
echo "🆕 Nova versão: $NEW_VERSION"

# Criar tag
git tag -a $NEW_VERSION -m "Release $NEW_VERSION"
git push origin $NEW_VERSION
```

### 2. Feature Flags

```python
# backend/app/core/feature_flags.py
import redis
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class FeatureFlags:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "feature_flags"
    
    def get_flag(self, flag_name: str, default: bool = False) -> bool:
        """Obter estado de uma feature flag"""
        key = f"{self.prefix}:{flag_name}"
        value = self.redis.get(key)
        
        if value is None:
            return default
        
        try:
            data = json.loads(value)
            return data.get('enabled', default)
        except json.JSONDecodeError:
            return default
    
    def set_flag(self, flag_name: str, enabled: bool, 
                 user_percentage: Optional[int] = None,
                 user_ids: Optional[list] = None,
                 expires_at: Optional[datetime] = None) -> None:
        """Definir estado de uma feature flag"""
        key = f"{self.prefix}:{flag_name}"
        
        data = {
            'enabled': enabled,
            'user_percentage': user_percentage,
            'user_ids': user_ids or [],
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if expires_at:
            data['expires_at'] = expires_at.isoformat()
        
        self.redis.setex(key, timedelta(days=30), json.dumps(data))
    
    def is_enabled_for_user(self, flag_name: str, user_id: str) -> bool:
        """Verificar se flag está habilitada para usuário específico"""
        key = f"{self.prefix}:{flag_name}"
        value = self.redis.get(key)
        
        if value is None:
            return False
        
        try:
            data = json.loads(value)
            
            # Flag desabilitada globalmente
            if not data.get('enabled', False):
                return False
            
            # Flag habilitada para usuários específicos
            user_ids = data.get('user_ids', [])
            if user_id in user_ids:
                return True
            
            # Flag habilitada por percentual
            user_percentage = data.get('user_percentage')
            if user_percentage is not None:
                # Hash user ID para determinar percentual
                user_hash = hash(user_id) % 100
                return user_hash < user_percentage
            
            # Flag expirou
            expires_at = data.get('expires_at')
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.utcnow() > expires_dt:
                    return False
            
            return data.get('enabled', False)
            
        except (json.JSONDecodeError, KeyError):
            return False
    
    def get_all_flags(self) -> Dict[str, Any]:
        """Obter todas as feature flags"""
        flags = {}
        pattern = f"{self.prefix}:*"
        
        for key in self.redis.scan_iter(match=pattern):
            flag_name = key.decode().replace(f"{self.prefix}:", "")
            value = self.redis.get(key)
            
            if value:
                try:
                    flags[flag_name] = json.loads(value)
                except json.JSONDecodeError:
                    continue
        
        return flags

# Uso
feature_flags = FeatureFlags(redis_client)

# Verificar se feature está habilitada
if feature_flags.is_enabled_for_user("new_chat_ui", user_id):
    # Usar nova interface
    pass
else:
    # Usar interface antiga
    pass

# Habilitar feature para 50% dos usuários
feature_flags.set_flag(
    "new_chat_ui",
    enabled=True,
    user_percentage=50,
    expires_at=datetime.utcnow() + timedelta(days=7)
)
```

### 3. Canary Deployment

```yaml
# infrastructure/k8s/canary-deployment.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: janus-backend
  namespace: janus
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: janus-backend
  progressDeadlineSeconds: 60
  service:
    port: 8000
    targetPort: 8000
    gateways:
    - janus-gateway
    hosts:
    - api.janus.com
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
    webhooks:
    - name: load-test
      url: http://flagger-loadtester.test/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://janus-backend-canary.janus:8000/api/v1/health"
```

## Monitoramento de Deployment

### 1. Métricas de DORA

```python
# backend/app/core/dora_metrics.py
from prometheus_client import Counter, Histogram, Gauge
from datetime import datetime
import pytz

# Deployment frequency
deployment_total = Counter(
    'janus_deployment_total',
    'Total number of deployments',
    ['environment', 'status', 'version']
)

# Lead time for changes
lead_time_seconds = Histogram(
    'janus_lead_time_seconds',
    'Time from commit to deployment',
    ['environment', 'change_type']
)

# Change failure rate
deployment_failures_total = Counter(
    'janus_deployment_failures_total',
    'Total number of failed deployments',
    ['environment', 'failure_reason']
)

# Time to restore service (MTTR)
mttr_seconds = Histogram(
    'janus_mttr_seconds',
    'Mean time to recovery',
    ['environment', 'incident_type']
)

# Change volume
change_volume_total = Counter(
    'janus_change_volume_total',
    'Total number of changes',
    ['environment', 'change_type']
)

class DORAMetrics:
    def __init__(self):
        self.tz = pytz.UTC
    
    def record_deployment(self, environment: str, version: str, status: str = "success"):
        """Registrar deployment"""
        deployment_total.labels(
            environment=environment,
            status=status,
            version=version
        ).inc()
    
    def record_lead_time(self, environment: str, commit_time: datetime, 
                          deployment_time: datetime, change_type: str = "feature"):
        """Registrar lead time"""
        lead_time = (deployment_time - commit_time).total_seconds()
        lead_time_seconds.labels(
            environment=environment,
            change_type=change_type
        ).observe(lead_time)
    
    def record_deployment_failure(self, environment: str, failure_reason: str):
        """Registrar falha de deployment"""
        deployment_failures_total.labels(
            environment=environment,
            failure_reason=failure_reason
        ).inc()
    
    def record_mttr(self, environment: str, incident_start: datetime,
                    incident_end: datetime, incident_type: str = "deployment_failure"):
        """Registrar MTTR"""
        recovery_time = (incident_end - incident_start).total_seconds()
        mttr_seconds.labels(
            environment=environment,
            incident_type=incident_type
        ).observe(recovery_time)

# Uso
dora_metrics = DORAMetrics()

# Registrar deployment bem-sucedido
dora_metrics.record_deployment("production", "v1.2.3", "success")

# Registrar lead time
commit_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=pytz.UTC)
deployment_time = datetime(2024, 1, 1, 14, 30, 0, tzinfo=pytz.UTC)
dora_metrics.record_lead_time("production", commit_time, deployment_time, "feature")
```

### 2. Dashboard de Deployment

```json
{
  "dashboard": {
    "title": "Janus - DORA Metrics",
    "panels": [
      {
        "title": "Deployment Frequency",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(janus_deployment_total[1d])",
            "legendFormat": "Deployments/day"
          }
        ]
      },
      {
        "title": "Lead Time for Changes",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, janus_lead_time_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Change Failure Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(janus_deployment_failures_total[1w]) / rate(janus_deployment_total[1w])",
            "legendFormat": "Failure rate"
          }
        ]
      },
      {
        "title": "Mean Time to Recovery",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, janus_mttr_seconds_bucket)",
            "legendFormat": "95th percentile MTTR"
          }
        ]
      }
    ]
  }
}
```

## Conclusão

Este guia cobre as práticas essenciais de deployment e DevOps para o Janus, incluindo:

- **CI/CD Pipeline** automatizado com GitHub Actions
- **Infraestrutura como Código** com Terraform e Kubernetes
- **Deployment Strategies** (blue-green, canary, rolling)
- **Monitoramento** com DORA metrics e observabilidade
- **Segurança** e gestão de secrets
- **Rollback** automatizado
- **Feature Flags** para deployments seguros

Para suporte técnico ou dúvidas sobre deployment, entre em contato com a equipe de DevOps.