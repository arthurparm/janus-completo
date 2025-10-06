# Sprint 1: Message Broker - Comunicação Distribuída

## ✅ Status: **IMPLEMENTADA E APRIMORADA**

A Sprint 1 foi **completamente implementada** com arquitetura moderna usando **RabbitMQ** como message broker central para comunicação assíncrona e distribuída entre componentes do sistema Janus.

---

## Visão Geral

A Sprint 1 estabelece a **espinha dorsal de comunicação assíncrona** do sistema, permitindo que diferentes componentes trabalhem de forma desacoplada e escalável.

### Arquitetura

```
┌─────────────────┐
│   FastAPI API   │
│   (Produtor)    │
└────────┬────────┘
         │ publish
         ▼
┌─────────────────────────────────────┐
│         RabbitMQ Broker             │
│   ┌───────────────────────────┐    │
│   │ Filas:                     │    │
│   │ - knowledge.consolidation │    │
│   │ - data.harvesting         │    │
│   │ - agent.tasks             │    │
│   │ - meta_agent.cycle        │    │
│   │ - neural.training         │    │
│   └───────────────────────────┘    │
└────────┬────────────────────────────┘
         │ consume
         ▼
┌─────────────────┐
│  Async Workers  │
│  (Consumidores) │
│                 │
│ - Consolidation │
│ - Harvesting    │
│ - Meta-Agent    │
│ - Neural Train  │
└─────────────────┘
```

---

## Componentes Implementados

### 1. **RabbitMQ Container** (`docker-compose.yml`)

```yaml
rabbitmq:
  image: rabbitmq:3.13-management-alpine
  ports:
    - "5672:5672"   # AMQP protocol
    - "15672:15672" # Management UI
  environment:
    - RABBITMQ_DEFAULT_USER=janus
    - RABBITMQ_DEFAULT_PASS=janus_pass
```

**Features:**
- ✅ Management UI (http://localhost:15672)
- ✅ Health checks integrados
- ✅ Persistência de dados
- ✅ Auto-restart em caso de falha

### 2. **Message Broker Core** (`app/core/message_broker.py`)

Cliente RabbitMQ assíncrono robusto com:

**Features principais:**
- ✅ **Conexão resiliente** com retry e circuit breaker
- ✅ **Publicação de mensagens** com prioridades
- ✅ **Consumo assíncrono** com prefetch configurável
- ✅ **Health checks** automáticos
- ✅ **Métricas Prometheus** integradas
- ✅ **Filas pré-configuradas** com TTL e limites

**Métricas exportadas:**
```
message_broker_published_total{queue, outcome}
message_broker_consumed_total{queue, outcome}
message_broker_latency_seconds{queue, operation}
message_broker_queue_depth{queue}
message_broker_active_consumers{queue}
```

### 3. **Async Consolidation Worker** (`app/core/async_consolidation_worker.py`)

Worker que **integra o Message Broker (Sprint 1) com o Knowledge Consolidator (Sprint 8)**.

**Modos de operação:**
- **Batch**: Processa múltiplas experiências da memória episódica
- **Single**: Processa uma experiência específica

**Recursos:**
- ✅ Processamento assíncrono em background
- ✅ Logging detalhado de cada tarefa
- ✅ Tratamento robusto de erros
- ✅ Integração com Prometheus

### 4. **API Endpoints** (`app/api/v1/endpoints/tasks.py`)

Endpoints REST para interagir com o message broker:

**POST** `/api/v1/tasks/consolidation`
```json
{
  "mode": "batch",
  "limit": 10
}
```

**GET** `/api/v1/tasks/queue/{queue_name}`
```json
{
  "name": "janus.knowledge.consolidation",
  "messages": 5,
  "consumers": 1
}
```

**GET** `/api/v1/tasks/health/rabbitmq`
```json
{
  "status": "healthy",
  "message": "Conexão com RabbitMQ está operacional"
}
```

---

## Filas Disponíveis

| Fila | Propósito | Worker |
|------|-----------|--------|
| `janus.knowledge.consolidation` | Consolidação de conhecimento | ✅ Implementado |
| `janus.data.harvesting` | Coleta de dados de treinamento | ⏳ Futuro |
| `janus.agent.tasks` | Tarefas de agentes | ⏳ Futuro |
| `janus.meta_agent.cycle` | Ciclo do meta-agente | ⏳ Futuro |
| `janus.neural.training` | Treinamento de redes neurais | ⏳ Futuro |

---

## Configuração

### Variáveis de Ambiente (`.env`)

```bash
# Sprint 1: RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=janus
RABBITMQ_PASSWORD=janus_pass
RABBITMQ_MANAGEMENT_PORT=15672
```

### Dependências Adicionadas

```
aio-pika>=9.0.0    # Cliente RabbitMQ assíncrono
pika>=1.3.0        # Cliente RabbitMQ síncrono (fallback)
```

---

## Como Usar

### 1. Iniciar o Sistema

```bash
# Inicia todos os serviços (incluindo RabbitMQ)
docker-compose up -d

# Verifica se RabbitMQ está saudável
curl http://localhost:8000/api/v1/tasks/health/rabbitmq
```

### 2. Publicar Tarefa de Consolidação

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/tasks/consolidation \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "limit": 10}'
```

```python
# Via código Python
from app.core.async_consolidation_worker import publish_consolidation_task

task_id = await publish_consolidation_task(mode="batch", limit=10)
print(f"Tarefa criada: {task_id}")
```

### 3. Monitorar Filas

```bash
# Via API
curl http://localhost:8000/api/v1/tasks/queue/janus.knowledge.consolidation

# Via Management UI
open http://localhost:15672
# User: janus, Password: janus_pass
```

### 4. Iniciar Workers

```python
# Em app/main.py ou script separado
from app.core.async_consolidation_worker import start_all_workers

@app.on_event("startup")
async def startup_workers():
    await start_all_workers()
```

---

## Resiliência

O sistema implementa múltiplas camadas de resiliência:

### 1. **Conexão Robusta**
- Retry com backoff exponencial (5 tentativas)
- Circuit breaker para evitar sobrecarga
- Auto-reconexão em caso de falha

### 2. **Processamento Seguro**
- Mensagens persistentes (survive restart)
- Dead Letter Queue (DLQ) para mensagens com erro
- Prefetch limit para controlar carga

### 3. **Observabilidade**
- Logs estruturados em cada etapa
- Métricas Prometheus detalhadas
- Health checks proativos

---

## Exemplos de Uso

### Consolidação em Lote

```python
# Consolida até 20 experiências da memória episódica
task_id = await publish_consolidation_task(
    mode="batch",
    limit=20
)
```

### Consolidação Individual

```python
# Consolida uma experiência específica
task_id = await publish_consolidation_task(
    mode="single",
    experience_id="exp-123",
    experience_content="Sistema detectou anomalia...",
    metadata={"severity": "high"}
)
```

### Monitoramento em Tempo Real

```python
# Obtém estatísticas da fila
info = await message_broker.get_queue_info("janus.knowledge.consolidation")
print(f"Mensagens pendentes: {info['messages']}")
print(f"Consumidores ativos: {info['consumers']}")
```

---

## Testes

Execute os testes de integração:

```bash
# Via HTTP Client (IntelliJ/VSCode)
# Abrir: http/sprint/test_message_broker.http
```

Os testes cobrem:
1. ✅ Health check do RabbitMQ
2. ✅ Publicação de tarefas
3. ✅ Monitoramento de filas
4. ✅ Consolidação batch e single
5. ✅ Resiliência a erros
6. ✅ Métricas Prometheus

---

## Melhorias Implementadas

A implementação vai **além dos requisitos originais da Sprint 1**:

### Requisitos Originais ✅
- [x] Integração com RabbitMQ
- [x] Módulos de publicação e consumo
- [x] Comunicação assíncrona entre componentes

### Aprimoramentos Adicionais ✅
- [x] **Circuit Breakers** em conexão e operações
- [x] **Retry com backoff exponencial**
- [x] **Métricas Prometheus** completas
- [x] **Health checks** automatizados
- [x] **Priorização de mensagens** (0-9)
- [x] **Dead Letter Queue** (DLQ) configurável
- [x] **TTL de mensagens** (24h)
- [x] **Limite de tamanho de fila** (10k mensagens)
- [x] **Prefetch configurável** por consumidor
- [x] **Management UI** para debug
- [x] **Testes de integração** completos
- [x] **Documentação detalhada**

---

## Management UI

Acesse o painel de administração do RabbitMQ:

**URL**: http://localhost:15672

**Credenciais:**
- User: `janus`
- Password: `janus_pass`

**Funcionalidades:**
- Visualizar filas e exchanges
- Monitorar taxa de mensagens
- Ver consumidores ativos
- Inspecionar mensagens
- Configurar alertas

---

## Próximos Passos

### Workers Adicionais a Implementar:

1. **Data Harvesting Worker** (Sprint 9)
   - Coleta dados de interações
   - Prepara dataset para treinamento

2. **Meta-Agent Worker** (Sprint 13)
   - Executa ciclo de auto-otimização
   - Analisa falhas e propõe melhorias

3. **Neural Training Worker** (Sprint 9)
   - Treina modelos de IA
   - Atualiza pesos automaticamente

4. **Agent Task Worker**
   - Executa tarefas de agentes em background
   - Desacopla execução da API

---

## Troubleshooting

### RabbitMQ não inicia

```bash
# Verifica logs
docker-compose logs rabbitmq

# Reseta dados (CUIDADO: apaga filas)
rm -rf ./data/rabbitmq
docker-compose restart rabbitmq
```

### Consumidor não processa mensagens

```bash
# Verifica se worker está rodando
curl http://localhost:8000/api/v1/tasks/queue/janus.knowledge.consolidation

# Verifica logs da aplicação
docker-compose logs janus-api
```

### Mensagens acumulando na fila

```bash
# Verifica se há erros no worker
docker-compose logs janus-api | grep ERROR

# Aumenta número de consumidores
# Em async_consolidation_worker.py:
# prefetch_count=10  # Aumentar para 20
```

---

## Referências

- **RabbitMQ Documentation**: https://www.rabbitmq.com/documentation.html
- **aio-pika Documentation**: https://aio-pika.readthedocs.io/
- **Sprint 1 Original**: `SPRINTS JANUS.md`
- **Knowledge Consolidator**: `KNOWLEDGE_CONSOLIDATOR.md`
- **Testes**: `http/sprint/test_message_broker.http`

---

## Conclusão

A Sprint 1 está **100% implementada e aprimorada**, fornecendo uma base sólida para comunicação assíncrona e distribuída no sistema Janus. O RabbitMQ atua como o **sistema nervoso central**, permitindo que componentes trabalhem de forma desacoplada, escalável e resiliente.

**Próximo passo recomendado**: Implementar workers adicionais para Data Harvesting (Sprint 9) e Meta-Agent Cycle (Sprint 13) usando a mesma arquitetura de message broker.
