# Guia de Monitoramento e Observabilidade

## Visão Geral

Este guia descreve como implementar, configurar e utilizar o sistema de monitoramento e observabilidade do Janus para garantir alta disponibilidade, performance e confiabilidade do sistema.

## Arquitetura de Monitoramento

### Componentes Principais

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Aplicação     │───▶│  Prometheus     │───▶│    Grafana      │
│   (Métricas)    │    │   (Storage)     │    │  (Dashboards)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenTelemetry │    │    AlertManager │    │   PagerDuty     │
│   (Tracing)     │    │   (Alerting)    │    │  (Notificações) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Loki         │    │    Webhook      │    │    Slack        │
│   (Logs)        │    │  (Integrações)  │    │  (Notificações) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Stack de Monitoramento

- **Prometheus**: Coleta e armazenamento de métricas
- **Grafana**: Visualização e dashboards
- **Loki**: Agregação de logs
- **OpenTelemetry**: Rastreamento distribuído
- **AlertManager**: Gerenciamento de alertas
- **Jaeger**: Análise de traces (opcional)

## Métricas Principais

### 1. Métricas de Aplicação

#### Backend FastAPI

```python
# Exemplo de métricas customizadas
from prometheus_client import Counter, Histogram, Gauge, Info

# Métricas de requisições HTTP
http_requests_total = Counter(
    'janus_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Métricas de latência
http_request_duration_seconds = Histogram(
    'janus_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Métricas de usuários ativos
active_users = Gauge(
    'janus_active_users',
    'Number of active users'
)

# Métricas de LLM
llm_requests_total = Counter(
    'janus_llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_tokens_used = Counter(
    'janus_llm_tokens_used_total',
    'Total tokens used by LLM',
    ['provider', 'model']
)

llm_request_duration = Histogram(
    'janus_llm_request_duration_seconds',
    'LLM request duration',
    ['provider', 'model']
)
```

#### Frontend Angular

```typescript
// Métricas de performance no navegador
export class MetricsService {
  private metricsEndpoint = '/api/v1/metrics';

  // Métricas de carregamento de página
  recordPageLoadTime(page: string, loadTime: number) {
    this.http.post(`${this.metricsEndpoint}/page-load`, {
      page,
      load_time: loadTime,
      timestamp: Date.now()
    }).subscribe();
  }

  // Métricas de erro JavaScript
  recordJavaScriptError(error: Error, context: string) {
    this.http.post(`${this.metricsEndpoint}/js-error`, {
      message: error.message,
      stack: error.stack,
      context,
      timestamp: Date.now()
    }).subscribe();
  }

  // Métricas de uso de memória
  recordMemoryUsage() {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      this.http.post(`${this.metricsEndpoint}/memory`, {
        used: memory.usedJSHeapSize,
        total: memory.totalJSHeapSize,
        limit: memory.jsHeapSizeLimit,
        timestamp: Date.now()
      }).subscribe();
    }
  }
}
```

### 2. Métricas de Infraestrutura

#### Docker Compose

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./monitoring/loki.yml:/etc/loki/local-config.yaml

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log:ro
      - ./monitoring/promtail.yml:/etc/promtail/config.yml

volumes:
  prometheus_data:
  grafana_data:
```

#### Configuração do Prometheus

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Janus Backend
  - job_name: 'janus-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  # Janus Frontend
  - job_name: 'janus-frontend'
    static_configs:
      - targets: ['localhost:4200']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    metrics_path: '/metrics'

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    metrics_path: '/metrics'

  # RabbitMQ
  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['rabbitmq:15692']
    metrics_path: '/metrics'

  # Qdrant
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'

  # Neo4j
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']
    metrics_path: '/metrics'

  # Ollama
  - job_name: 'ollama'
    static_configs:
      - targets: ['ollama:11434']
    metrics_path: '/metrics'

  # Node Exporter (métricas do sistema)
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

### 3. Regras de Alerta

```yaml
# monitoring/alert_rules.yml
groups:
  - name: janus_alerts
    rules:
      # Alta latência de API
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, janus_http_request_duration_seconds_bucket) > 2
        for: 5m
        labels:
          severity: warning
          team: backend
        annotations:
          summary: "High API latency detected"
          description: "95th percentile latency is above 2 seconds for {{ $labels.endpoint }}"

      # Erros de API elevados
      - alert: HighAPIErrorRate
        expr: rate(janus_http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "High API error rate"
          description: "Error rate is above 10% for {{ $labels.endpoint }}"

      # LLM indisponível
      - alert: LLMServiceDown
        expr: up{job="llm-service"} == 0
        for: 2m
        labels:
          severity: critical
          team: ai
        annotations:
          summary: "LLM service is down"
          description: "LLM service {{ $labels.provider }} has been down for more than 2 minutes"

      # Alto uso de memória
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90%"

      # Disco quase cheio
      - alert: DiskSpaceWarning
        expr: (node_filesystem_size_bytes{fstype!="tmpfs"} - node_filesystem_free_bytes{fstype!="tmpfs"}) / node_filesystem_size_bytes{fstype!="tmpfs"} > 0.8
        for: 5m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "Disk space warning"
          description: "Disk usage is above 80% on {{ $labels.mountpoint }}"

      # PostgreSQL lento
      - alert: SlowPostgresQueries
        expr: pg_stat_activity_max_tx_duration > 300
        for: 5m
        labels:
          severity: warning
          team: database
        annotations:
          summary: "Slow PostgreSQL queries"
          description: "Longest running transaction is taking more than 5 minutes"

      # Redis indisponível
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 2m
        labels:
          severity: critical
          team: cache
        annotations:
          summary: "Redis is down"
          description: "Redis service has been down for more than 2 minutes"

      # Alto uso de tokens LLM
      - alert: HighLLMTokenUsage
        expr: increase(janus_llm_tokens_used_total[1h]) > 100000
        for: 1m
        labels:
          severity: info
          team: ai
        annotations:
          summary: "High LLM token usage"
          description: "Used more than 100k tokens in the last hour"
```

## Dashboards

### 1. Dashboard de Visão Geral

```json
{
  "dashboard": {
    "title": "Janus - Visão Geral",
    "panels": [
      {
        "title": "Taxa de Requisições",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(janus_http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Latência de Requisições",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, janus_http_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, janus_http_request_duration_seconds_bucket)",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Erros por Endpoint",
        "type": "table",
        "targets": [
          {
            "expr": "rate(janus_http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Usuários Ativos",
        "type": "singlestat",
        "targets": [
          {
            "expr": "janus_active_users",
            "legendFormat": "Usuários"
          }
        ]
      }
    ]
  }
}
```

### 2. Dashboard de LLM

```json
{
  "dashboard": {
    "title": "Janus - LLM Performance",
    "panels": [
      {
        "title": "Requisições LLM por Provedor",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(janus_llm_requests_total[5m])",
            "legendFormat": "{{provider}} - {{model}}"
          }
        ]
      },
      {
        "title": "Tokens Usados por Hora",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(janus_llm_tokens_used_total[1h])",
            "legendFormat": "{{provider}} - {{model}}"
          }
        ]
      },
      {
        "title": "Latência LLM",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, janus_llm_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile - {{provider}}"
          }
        ]
      },
      {
        "title": "Taxa de Erro LLM",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(janus_llm_requests_total{status=\"error\"}[5m])",
            "legendFormat": "{{provider}} - {{model}}"
          }
        ]
      }
    ]
  }
}
```

### 3. Dashboard de Infraestrutura

```json
{
  "dashboard": {
    "title": "Janus - Infraestrutura",
    "panels": [
      {
        "title": "Uso de CPU",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "CPU Usage %"
          }
        ]
      },
      {
        "title": "Uso de Memória",
        "type": "graph",
        "targets": [
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "legendFormat": "Memory Usage %"
          }
        ]
      },
      {
        "title": "Uso de Disco",
        "type": "graph",
        "targets": [
          {
            "expr": "(node_filesystem_size_bytes{fstype!=\"tmpfs\"} - node_filesystem_free_bytes{fstype!=\"tmpfs\"}) / node_filesystem_size_bytes{fstype!=\"tmpfs\"} * 100",
            "legendFormat": "{{mountpoint}}"
          }
        ]
      },
      {
        "title": "Tráfego de Rede",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(node_network_receive_bytes_total[5m])",
            "legendFormat": "Receive - {{device}}"
          },
          {
            "expr": "rate(node_network_transmit_bytes_total[5m])",
            "legendFormat": "Transmit - {{device}}"
          }
        ]
      }
    ]
  }
}
```

## Logs e Rastreamento

### 1. Configuração de Logs Estruturados

```python
# backend/app/core/logging.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        
    def log_request(self, request, response, duration):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "info",
            "type": "http_request",
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "duration_ms": duration * 1000,
            "user_agent": request.headers.get("user-agent"),
            "ip": request.client.host,
            "request_id": request.headers.get("x-request-id")
        }
        self.logger.info(json.dumps(log_data))
    
    def log_llm_request(self, provider, model, tokens_used, duration, status):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "info",
            "type": "llm_request",
            "provider": provider,
            "model": model,
            "tokens_used": tokens_used,
            "duration_ms": duration * 1000,
            "status": status
        }
        self.logger.info(json.dumps(log_data))
    
    def log_error(self, error, context=None):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "error",
            "type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "context": context or {}
        }
        self.logger.error(json.dumps(log_data))
```

### 2. Configuração do Loki

```yaml
# monitoring/loki.yml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s
  max_transfer_retries: 0

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb:
    directory: /tmp/loki/index
  filesystem:
    directory: /tmp/loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

### 3. Configuração do Promtail

```yaml
# monitoring/promtail.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: janus-backend
    static_configs:
      - targets:
          - localhost
        labels:
          job: janus-backend
          __path__: /var/log/janus/backend/*.log

  - job_name: janus-frontend
    static_configs:
      - targets:
          - localhost
        labels:
          job: janus-frontend
          __path__: /var/log/janus/frontend/*.log

  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          job: nginx
          __path__: /var/log/nginx/*.log
```

## Rastreamento Distribuído

### 1. Configuração OpenTelemetry

```python
# backend/app/core/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

def configure_tracing(app_name: str = "janus-backend"):
    resource = Resource(attributes={
        SERVICE_NAME: app_name
    })
    
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    
    span_processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(span_processor)
    
    return trace.get_tracer(app_name)

def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
```

### 2. Implementação de Traces Customizados

```python
# backend/app/services/llm_service.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class LLMService:
    def __init__(self):
        self.tracer = tracer
    
    async def chat(self, messages: List[Dict], provider: str):
        with self.tracer.start_as_current_span("llm.chat") as span:
            span.set_attribute("llm.provider", provider)
            span.set_attribute("llm.messages.count", len(messages))
            
            try:
                # Processar requisição
                response = await self._process_chat(messages, provider)
                
                span.set_attribute("llm.response.success", True)
                span.set_attribute("llm.tokens.used", response.get("tokens_used", 0))
                
                return response
                
            except Exception as e:
                span.set_attribute("llm.response.success", False)
                span.set_attribute("llm.error.type", type(e).__name__)
                span.record_exception(e)
                raise
```

## Health Checks e Readiness Probes

### 1. Endpoints de Health Check

```python
# backend/app/api/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from redis import Redis
import httpx

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check básico"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/healthz")
async def healthz_check(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Health check completo com dependências"""
    checks = {}
    
    # Check PostgreSQL
    try:
        db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # Check LLM providers
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                checks["ollama"] = "healthy"
            else:
                checks["ollama"] = f"unhealthy: HTTP {response.status_code}"
        except Exception as e:
            checks["ollama"] = f"unhealthy: {str(e)}"
    
    # Status geral
    overall_status = "healthy" if all("healthy" in v for v in checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow()
    }

@router.get("/ready")
async def readiness_check():
    """Readiness check para Kubernetes"""
    # Verificar se a aplicação está pronta para receber tráfego
    return {"status": "ready", "timestamp": datetime.utcnow()}
```

### 2. Configuração Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: janus-backend
spec:
  template:
    spec:
      containers:
      - name: janus-backend
        image: janus-backend:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30
```

## Alertas e Notificações

### 1. Configuração do AlertManager

```yaml
# monitoring/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@janus.com'
  smtp_auth_username: 'alerts@janus.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: pagerduty
    continue: true
  - match:
      team: backend
    receiver: backend-team
  - match:
      team: database
    receiver: database-team

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://localhost:5001/webhook'
    send_resolved: true

- name: 'pagerduty'
  pagerduty_configs:
  - service_key: 'your-pagerduty-service-key'
    description: '{{ .GroupLabels.alertname }}: {{ .GroupLabels.service }}'

- name: 'backend-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#backend-alerts'
    title: 'Backend Alert'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

- name: 'database-team'
  email_configs:
  - to: 'database-team@janus.com'
    subject: 'Database Alert: {{ .GroupLabels.alertname }}'
    body: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### 2. Webhook Customizado para Alertas

```python
# monitoring/webhook_handler.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json

app = FastAPI()

class Alert(BaseModel):
    status: str
    labels: dict
    annotations: dict
    startsAt: str
    endsAt: str
    generatorURL: str

class AlertWebhook(BaseModel):
    receiver: str
    status: str
    alerts: List[Alert]
    groupLabels: dict
    commonLabels: dict
    commonAnnotations: dict
    externalURL: str
    version: str
    groupKey: str
    truncatedAlerts: int

@app.post("/webhook")
async def handle_alert(webhook: AlertWebhook):
    """Processar alertas do AlertManager"""
    
    for alert in webhook.alerts:
        severity = alert.labels.get('severity', 'info')
        
        # Enviar para Slack
        if severity in ['warning', 'critical']:
            await send_slack_notification(alert)
        
        # Criar ticket no Jira
        if severity == 'critical':
            await create_jira_ticket(alert)
        
        # Enviar notificação para Telegram
        if severity == 'critical':
            await send_telegram_notification(alert)
        
        # Log do alerta
        logger.error(f"Alert received: {alert.labels.get('alertname')} - {alert.annotations.get('description')}")
    
    return {"status": "processed"}

async def send_slack_notification(alert: Alert):
    """Enviar notificação para Slack"""
    webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    
    color = "danger" if alert.labels.get('severity') == 'critical' else "warning"
    
    payload = {
        "attachments": [
            {
                "color": color,
                "title": f"Alert: {alert.labels.get('alertname')}",
                "text": alert.annotations.get('description'),
                "fields": [
                    {
                        "title": "Severity",
                        "value": alert.labels.get('severity'),
                        "short": True
                    },
                    {
                        "title": "Service",
                        "value": alert.labels.get('service', 'unknown'),
                        "short": True
                    }
                ],
                "footer": "Janus Monitoring",
                "ts": int(datetime.fromisoformat(alert.startsAt).timestamp())
            }
        ]
    }
    
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200
```

## Performance Monitoring

### 1. Métricas de Performance

```python
# backend/app/core/performance.py
import time
import functools
from prometheus_client import Histogram, Counter

# Métricas de performance
function_duration = Histogram(
    'janus_function_duration_seconds',
    'Time spent in functions',
    ['function_name', 'module']
)

db_query_duration = Histogram(
    'janus_db_query_duration_seconds',
    'Database query duration',
    ['query_type', 'table']
)

cache_operations = Counter(
    'janus_cache_operations_total',
    'Cache operations',
    ['operation', 'cache_name', 'result']
)

def monitor_performance(func):
    """Decorator para monitorar performance de funções"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            function_duration.labels(
                function_name=func.__name__,
                module=func.__module__
            ).observe(duration)
    
    return wrapper

def monitor_db_query(query_type: str, table: str = "unknown"):
    """Decorator para monitorar queries de banco de dados"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                db_query_duration.labels(
                    query_type=query_type,
                    table=table
                ).observe(duration)
        
        return wrapper
    return decorator
```

### 2. Monitoramento de Queries Lentas

```python
# backend/app/core/slow_query_logger.py
import time
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SLOW_QUERY_THRESHOLD = 1.0  # segundos

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug(f"Starting query: {statement[:100]}...")

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    
    if total_time > SLOW_QUERY_THRESHOLD:
        logger.warning(
            f"Slow query detected: {statement[:200]}... "
            f"({total_time:.2f}s)",
            extra={
                'query_time': total_time,
                'query': statement,
                'parameters': str(parameters)
            }
        )
        
        # Enviar métrica para Prometheus
        from prometheus_client import Histogram
        slow_query_duration = Histogram(
            'janus_slow_query_duration_seconds',
            'Slow query duration',
            ['query_type']
        )
        
        query_type = statement.split()[0].upper() if statement else 'UNKNOWN'
        slow_query_duration.labels(query_type=query_type).observe(total_time)
```

## Testes de Monitoramento

### 1. Testes de Health Check

```python
# tests/test_health.py
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_healthz_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/healthz")
    
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "unhealthy"]
    assert "checks" in response.json()

@pytest.mark.asyncio
async def test_metrics_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/metrics")
    
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "janus_http_requests_total" in response.text
```

### 2. Testes de Alertas

```python
# tests/test_alerts.py
import pytest
import requests
import time

def test_alert_rules():
    """Testar se as regras de alerta estão funcionando"""
    
    # Simular condição de alerta
    # Por exemplo, alta latência
    
    # Verificar se o alerta foi disparado
    alertmanager_url = "http://localhost:9093/api/v1/alerts"
    response = requests.get(alertmanager_url)
    
    assert response.status_code == 200
    alerts = response.json()["data"]
    
    # Verificar se há alertas ativos
    active_alerts = [alert for alert in alerts if alert["status"]["state"] == "active"]
    
    if active_alerts:
        print(f"Found {len(active_alerts)} active alerts")
        for alert in active_alerts:
            print(f"Alert: {alert['labels']['alertname']} - {alert['labels']['severity']}")

def test_slack_webhook():
    """Testar webhook de notificações"""
    
    webhook_url = "http://localhost:5001/webhook"
    
    test_alert = {
        "receiver": "test",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "TestAlert",
                    "severity": "warning"
                },
                "annotations": {
                    "description": "This is a test alert"
                },
                "startsAt": "2024-01-01T00:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z"
            }
        ],
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "externalURL": "",
        "version": "4",
        "groupKey": "test",
        "truncatedAlerts": 0
    }
    
    response = requests.post(webhook_url, json=test_alert)
    assert response.status_code == 200
```

## Manutenção e Troubleshooting

### 1. Verificação de Status dos Serviços

```bash
#!/bin/bash
# scripts/check_monitoring_status.sh

echo "=== Status do Monitoramento ==="

# Verificar Prometheus
echo "Prometheus:"
curl -s http://localhost:9090/-/healthy | jq -r .status

# Verificar Grafana
echo "Grafana:"
curl -s http://admin:admin@localhost:3000/api/health | jq -r .database

# Verificar Loki
echo "Loki:"
curl -s http://localhost:3100/ready | head -n 1

# Verificar AlertManager
echo "AlertManager:"
curl -s http://localhost:9093/-/healthy | jq -r .status

# Listar alertas ativos
echo "=== Alertas Ativos ==="
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | select(.status.state == "active") | .labels.alertname'

# Verificar exporters
echo "=== Exporters ==="
echo "Node Exporter: $(curl -s http://localhost:9100/metrics | grep -c node_) métricas"
echo "Postgres Exporter: $(curl -s http://localhost:9187/metrics | grep -c pg_) métricas"
echo "Redis Exporter: $(curl -s http://localhost:9121/metrics | grep -c redis_) métricas"
```

### 2. Diagnóstico de Problemas Comuns

#### Prometheus Não Está Coletando Métricas

```bash
# Verificar targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Verificar configuração
curl -s http://localhost:9090/api/v1/status/config | jq '.data.yaml' | head -20

# Testar query simples
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result[] | {metric: .metric, value: .value[1]}'
```

#### Alertas Não Estão Sendo Enviados

```bash
# Verificar configuração do AlertManager
curl -s http://localhost:9093/api/v1/status | jq '.data.configJSON' | jq '.route'

# Testar rota de alerta
curl -X POST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning"
  },
  "annotations": {
    "summary": "Test alert"
  }
}]'

# Verificar logs do AlertManager
docker logs monitoring_alertmanager_1 | tail -50
```

#### Grafana Não Está Mostrando Dados

```bash
# Verificar datasources
curl -s http://admin:admin@localhost:3000/api/datasources | jq '.[] | {name: .name, type: .type, url: .url}'

# Testar datasource
curl -s http://admin:admin@localhost:3000/api/datasources/uid/prometheus/health

# Verificar permissões
curl -s http://admin:admin@localhost:3000/api/org
```

### 3. Limpeza e Manutenção

```bash
#!/bin/bash
# scripts/maintenance.sh

echo "=== Manutenção do Monitoramento ==="

# Limpar logs antigos do Loki (manter últimos 7 dias)
curl -X POST http://localhost:3100/loki/api/v1/delete \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{job=\"janus-backend\"}",
    "start": "$(date -d '7 days ago' +%s)",
    "end": "$(date +%s)"
  }'

# Compactar dados antigos do Prometheus
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Backup dos dashboards do Grafana
mkdir -p backups/grafana-dashboards
curl -s http://admin:admin@localhost:3000/api/search | jq -r '.[].uid' | while read uid; do
  curl -s "http://admin:admin@localhost:3000/api/dashboards/uid/$uid" > "backups/grafana-dashboards/$uid.json"
done

echo "Manutenção concluída!"
```

## Conclusão

Este guia cobre os principais aspectos do monitoramento e observabilidade do Janus. Para mais informações:

- Consulte a [documentação de incidentes](incident-response-runbook.md) para procedimentos de resposta
- Veja o [guia de performance](performance-tuning.md) para otimização
- Reporte problemas no [repositório GitHub](https://github.com/janus-completo/janus-completo)

Para suporte técnico, entre em contato com a equipe de operações.