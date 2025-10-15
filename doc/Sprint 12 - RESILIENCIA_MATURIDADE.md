# Sprint 12: Resiliência e Maturidade - Operação Contínua

## 📋 Visão Geral

A Sprint 12 consolida o Janus como um **sistema maduro e resiliente**, pronto para **operação autônoma 24/7**.
Implementa observabilidade avançada, gestão robusta de falhas e monitoramento proativo.

---

## 🎯 Objetivos

1. **Observabilidade Completa**: Grafana dashboards + Prometheus metrics
2. **Poison Pill Handling**: Isolamento automático de mensagens problemáticas
3. **Health Checks Avançados**: Monitoramento proativo de todos os componentes
4. **Resiliência Aprimorada**: Circuit breakers + retry com backoff exponencial (já existentes)
5. **Operação Contínua**: Sistema self-healing

---

## 🏗️ Componentes Implementados

### 1. Dashboards Grafana

#### **Janus Overview Dashboard**

- System health status
- Active agents
- Circuit breakers status
- Error rates
- LLM request rates & latency (P50/P95)
- Multi-agent tasks by status
- Task duration by agent role
- Memory operations rate
- Retry operations
- Token usage

#### **LLM Performance & Cost Dashboard**

- Provider selection distribution
- Requests by priority/role
- Success rate by provider
- Failure distribution by exception type
- Latency heatmap
- Token consumption rate
- Estimated cost (tokens/hour)
- Fallback events
- Cache hit rate

### 2. Poison Pill Handler

**Problema**: Mensagens que causam falhas repetidas podem travar filas e degradar o sistema.

**Solução**: Sistema que detecta, isola e gerencia mensagens problemáticas.

**Critérios de Detecção**:

1. Threshold de falhas (padrão: 3 falhas)
2. Mesmo tipo de erro persistente (3x seguidas)
3. Falhas ao longo do tempo (>5 min)

**Funcionalidades**:

- Rastreamento automático de falhas
- Quarentena de poison pills
- Estatísticas por fila
- Limpeza automática de quarentena expirada
- Liberação manual de mensagens

**Uso via Decorador**:

```python
@protect_against_poison_pills(
    queue_name="tasks",
    extract_message_id=lambda task: task.id
)
async def process_task(task: Task):
# processar task
```

### 3. Health Monitor

Sistema centralizado de health checks com:

- Checks assíncronos em paralelo
- Timeout configurável (10s)
- Status: HEALTHY/DEGRADED/UNHEALTHY
- Score de saúde (0-100)
- Monitoramento contínuo opcional

**Componentes Monitorados**:

- `llm_manager`: Circuit breakers, cache
- `multi_agent_system`: Agentes ativos, workspace
- `poison_pill_handler`: Mensagens em quarentena

**Registrar Novos Checks**:

```python
monitor = get_health_monitor()
monitor.register_health_check(
    component="database",
    check_func=check_database_health,
    is_critical=True
)
```

### 4. Resiliência Existente (Verificada)

**Circuit Breakers** (`app/core/resilience.py`):

- Estados: CLOSED/OPEN/HALF_OPEN
- Isolamento de falhas por provedor
- Recuperação automática

**Retry com Backoff Exponencial**:

- Configurável via decorador `@resilient`
- Métricas Prometheus integradas

---

## 🌐 API Endpoints

### Health Checks

**1. GET `/api/v1/observability/health/system`**
Visão agregada da saúde do sistema.

**Response**:

```json
{
  "status": "healthy",
  "score": 95,
  "message": "3/3 componentes saudáveis",
  "components": {
    "llm_manager": {
      "status": "healthy",
      "message": "Todos os provedores operacionais",
      "details": {
        "open_circuits": 0,
        "cached_llms": 3
      }
    }
  }
}
```

**2. GET `/api/v1/observability/health/components/{component}`**
Health check de componente específico.

**3. POST `/api/v1/observability/health/check-all`**
Força execução imediata de todos os checks.

### Poison Pills

**4. GET `/api/v1/observability/poison-pills/quarantined`**
Lista mensagens em quarentena.

**5. POST `/api/v1/observability/poison-pills/release`**
Libera mensagem da quarentena.

**Request**:

```json
{
  "message_id": "uuid-123",
  "allow_retry": false
}
```

**6. POST `/api/v1/observability/poison-pills/cleanup`**
Remove mensagens expiradas.

**7. GET `/api/v1/observability/poison-pills/stats`**
Estatísticas de poison pills.

### Métricas

**8. GET `/api/v1/observability/metrics/summary`**
Resumo de métricas chave (LLM, multi-agent, poison pills).

---

## 📊 Métricas Prometheus

### Circuit Breakers

- `janus_resilience_circuit_state`: Estado do circuit breaker
- `janus_resilience_failure_count`: Contagem de falhas
- `janus_resilience_retries_total`: Total de retries

### LLM Manager

- `llm_router_model_selected_total`: Seleções de modelo
- `llm_requests_total`: Total de requisições
- `llm_request_latency_seconds`: Latência
- `llm_tokens_total`: Tokens consumidos

### Multi-Agent

- `multi_agent_tasks_total`: Total de tarefas
- `multi_agent_task_duration_seconds`: Duração de tarefas
- `multi_agent_collaborations_total`: Colaborações
- `multi_agent_active_agents`: Agentes ativos (gauge)

### Poison Pills

- `poison_pill_detected_total`: Poison pills detectadas
- `poison_pill_quarantined_total`: Total em quarentena
- `poison_pill_in_quarantine`: Atualmente em quarentena (gauge)

### System Health

- `component_health_status`: Saúde do componente (0-1)
- `system_health_score`: Score geral (0-100)
- `health_check_duration_seconds`: Duração dos checks

---

## ⚙️ Configuração

### Prometheus

Já configurado via métricas integradas em todos os módulos.

### Grafana

1. Importar dashboards de `grafana/dashboards/`:
    - `janus-overview.json`
    - `janus-llm-performance.json`

2. Configurar datasource Prometheus

### Poison Pill Handler

```python
handler = PoisonPillHandler(
    failure_threshold=3,
    consecutive_failure_threshold=5,
    quarantine_duration_hours=24,
    enable_auto_retry=False
)
```

### Health Monitor

```python
monitor = get_health_monitor()
await monitor.start_monitoring(interval_seconds=30)
```

---

## 🧪 Padrões de Resiliência Implementados

| Padrão                    | Implementação            | Uso                             |
|---------------------------|--------------------------|---------------------------------|
| **Circuit Breaker**       | `resilience.py`          | Isola falhas por provedor LLM   |
| **Retry com Backoff**     | `resilience.py`          | Decorador `@resilient`          |
| **Poison Pill Detection** | `poison_pill_handler.py` | Detecta mensagens problemáticas |
| **Graceful Degradation**  | `llm_manager.py`         | Fallback para Ollama local      |
| **Health Checks**         | `health_monitor.py`      | Monitoramento proativo          |
| **Bulkhead**              | `multi_agent_system.py`  | Isolamento por agente           |
| **Timeout**               | Todos os módulos         | Prevenção de hangs              |
| **Observability**         | Prometheus + Grafana     | Visibilidade completa           |

---

## 🚀 Operação Contínua

### Monitoramento Proativo

1. **Grafana Dashboards**: Visão em tempo real
2. **Alertas**: Configurar em Grafana (thresholds)
3. **Health Checks**: Automáticos a cada 30s
4. **Métricas**: Expostas em `/metrics`

### Self-Healing

- Circuit breakers recuperam automaticamente
- Poison pills isoladas sem intervenção
- Fallback LLM garante continuidade
- Health monitor detecta degradação

### Troubleshooting

**Circuit Breaker Aberto:**

```bash
# Verificar status
curl http://localhost:8000/api/v1/llm/circuit-breakers

# Resetar manualmente
curl -X POST http://localhost:8000/api/v1/llm/circuit-breakers/openai/reset
```

**Poison Pills:**

```bash
# Listar quarentena
curl http://localhost:8000/api/v1/observability/poison-pills/quarantined

# Liberar mensagem
curl -X POST http://localhost:8000/api/v1/observability/poison-pills/release \
  -d '{"message_id": "uuid", "allow_retry": false}'
```

**Health Degradado:**

```bash
# Check completo
curl http://localhost:8000/api/v1/observability/health/system

# Check específico
curl http://localhost:8000/api/v1/observability/health/components/llm_manager
```

---

## 📚 Próximos Passos

**Sprint 13**: Meta-Agente de Auto-Otimização (consciência proativa)

---

## ✅ Critérios de Aceitação

- [x] Dashboards Grafana criados (2x)
- [x] Poison pill handler funcional
- [x] Health monitor implementado
- [x] Endpoints de observabilidade (8x)
- [x] Métricas Prometheus completas
- [x] Circuit breakers e retry verificados
- [x] Documentação completa
- [x] Testes HTTP funcionais
