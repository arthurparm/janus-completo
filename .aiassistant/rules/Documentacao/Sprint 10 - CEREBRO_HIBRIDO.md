# Sprint 10: Cérebro Híbrido e Resiliência de APIs

## 📋 Visão Geral

A Sprint 10 implementa um **sistema inteligente de gerenciamento de LLMs** que alterna dinamicamente entre diferentes
provedores (OpenAI, Google Gemini, Ollama local), garantindo **alta disponibilidade**, **otimização de custos** e *
*resiliência contra falhas**.

---

## 🎯 Objetivos

1. **LLM Manager Central**: Sistema que seleciona automaticamente o melhor provedor de LLM
2. **Fallback Automático**: Alternância para modelo local (Ollama) em caso de falha de APIs pagas
3. **Monitoramento de Uso**: Rastreamento de chamadas e custos para evitar limites de API
4. **Circuit Breakers**: Isolamento de falhas por provedor para evitar cascata de erros
5. **Observabilidade Completa**: Métricas Prometheus para todos os provedores

---

## 🏗️ Arquitetura

### Componentes Principais

```
┌─────────────────────────────────────────────┐
│           LLM Manager (Cérebro)             │
│  ┌───────────────────────────────────────┐  │
│  │  Roteador Dinâmico de Modelos         │  │
│  │  - Seleção baseada em papel e prioridade │
│  │  - Cache de instâncias LLM            │  │
│  │  - Validação de API keys              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
              ↓           ↓           ↓
    ┌─────────────┐ ┌──────────┐ ┌──────────┐
    │   OpenAI    │ │  Gemini  │ │  Ollama  │
    │  (Pago)     │ │  (Pago)  │ │ (Local)  │
    └─────────────┘ └──────────┘ └──────────┘
         ↓               ↓             ↓
    ┌─────────────────────────────────────────┐
    │      Circuit Breakers por Provedor      │
    │  - Isolamento de falhas                 │
    │  - Recuperação automática               │
    └─────────────────────────────────────────┘
```

---

## 🔧 Implementação

### 1. LLM Manager (`app/core/llm_manager.py`)

#### **ModelRole (Papéis de Modelos)**

```python
class ModelRole(Enum):
    ORCHESTRATOR = "orchestrator"  # Coordenação geral
    CODE_GENERATOR = "code_generator"  # Geração de código
    KNOWLEDGE_CURATOR = "knowledge_curator"  # Curadoria de conhecimento
```

#### **ModelPriority (Estratégias de Seleção)**

```python
class ModelPriority(Enum):
    LOCAL_ONLY = "local_only"  # Sempre usa Ollama local
    FAST_AND_CHEAP = "fast_and_cheap"  # Prioriza velocidade/custo
    HIGH_QUALITY = "high_quality"  # Prioriza qualidade
```

#### **Função Principal: `get_llm()`**

```python
def get_llm(
        role: ModelRole = ModelRole.ORCHESTRATOR,
        priority: ModelPriority = ModelPriority.LOCAL_ONLY,
        cache_key: str = ""
) -> BaseChatModel:
    """
    Obtém um LLM com base no papel e prioridade.

    Estratégias:
    1. LOCAL_ONLY: Sempre Ollama (falha se indisponível)
    2. FAST_AND_CHEAP/HIGH_QUALITY:
       - Tenta Gemini primeiro (mais barato)
       - Fallback para OpenAI
       - Fallback final para Ollama
    """
```

#### **Cliente Unificado: `LLMClient`**

```python
class LLMClient:
    def send(self, prompt: str, timeout_s: Optional[int] = None) -> str:
        """
        Envia prompt com:
        - Validação de prompt
        - Circuit breaker por provedor
        - Retry com backoff exponencial
        - Métricas Prometheus (latência, tokens, sucessos/falhas)
        - Timeout configurável
        """
```

### 2. Sistema de Cache

```python
@dataclass
class CachedLLM:
    instance: BaseChatModel
    created_at: datetime
    provider: str
    consecutive_failures: int = 0  # Evicção após 3 falhas


# Cache global com TTL configurável
_llm_cache: Dict[str, CachedLLM] = {}
```

**Invalidação:**

- Automática após TTL (configurável)
- Após 3 falhas consecutivas
- Manual via API `/llm/cache/invalidate`

### 3. Circuit Breakers

```python
_provider_circuit_breakers: Dict[str, CircuitBreaker] = {
    "ollama": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "openai": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "google_gemini": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
}
```

**Estados:**

- `CLOSED`: Operação normal
- `OPEN`: Provedor bloqueado (falhas acima do threshold)
- `HALF_OPEN`: Tentando recuperação

### 4. Métricas Prometheus

```python
# Contador de seleção de modelos
LLM_ROUTER_COUNTER = Counter(
    "llm_router_model_selected_total",
    ["role", "priority", "model_name", "provider"]
)

# Total de requisições
LLM_REQUESTS = Counter(
    "llm_requests_total",
    ["provider", "model", "role", "outcome", "exception_type"]
)

# Latência
LLM_LATENCY = Histogram(
    "llm_request_latency_seconds",
    ["provider", "model", "role", "outcome"]
)

# Tokens consumidos
LLM_TOKENS = Counter(
    "llm_tokens_total",
    ["provider", "model", "role", "direction"]  # in/out
)
```

---

## 🌐 API Endpoints

### **1. POST `/api/v1/llm/invoke`**

Invoca um LLM com seleção automática de provedor.

**Request:**

```json
{
  "prompt": "Explique o que é um circuit breaker",
  "role": "orchestrator",
  "priority": "fast_and_cheap",
  "timeout_seconds": 30
}
```

**Response:**

```json
{
  "response": "Um circuit breaker é um padrão...",
  "provider": "google_gemini",
  "model": "gemini-1.5-flash",
  "role": "orchestrator"
}
```

### **2. GET `/api/v1/llm/cache/status`**

Status do cache de LLMs.

**Response:**

```json
{
  "total_cached": 3,
  "cache_entries": [
    {
      "cache_key": "orchestrator_local_only",
      "provider": "ollama",
      "consecutive_failures": 0,
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### **3. POST `/api/v1/llm/cache/invalidate`**

Invalida cache (total ou por provedor).

**Query Params:**

- `provider` (opcional): "ollama", "openai", "google_gemini"

### **4. GET `/api/v1/llm/circuit-breakers`**

Status de todos os circuit breakers.

**Response:**

```json
[
  {
    "provider": "openai",
    "state": "CLOSED",
    "failure_count": 0,
    "last_failure_time": null
  },
  {
    "provider": "google_gemini",
    "state": "OPEN",
    "failure_count": 5,
    "last_failure_time": 1705315200.0
  }
]
```

### **5. POST `/api/v1/llm/circuit-breakers/{provider}/reset`**

Reseta circuit breaker de um provedor.

### **6. GET `/api/v1/llm/health`**

Health check completo do sistema.

**Response:**

```json
{
  "status": "healthy",
  "total_providers": 4,
  "circuit_breakers": [
    ...
  ],
  "cache_status": {
    "total_cached": 3,
    "providers_in_cache": 2
  }
}
```

### **7. GET `/api/v1/llm/providers`**

Lista todos os provedores configurados.

---

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# Ollama (Local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_ORCHESTRATOR_MODEL=llama3.2:latest
OLLAMA_CODER_MODEL=codellama:latest
OLLAMA_CURATOR_MODEL=llama3.2:latest

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL_NAME=gpt-4-turbo-preview

# Google Gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL_NAME=gemini-1.5-flash

# LLM Manager
LLM_CACHE_TTL_SECONDS=3600
LLM_DEFAULT_TIMEOUT_SECONDS=60
LLM_MAX_PROMPT_LENGTH=50000
LLM_RETRY_MAX_ATTEMPTS=3
LLM_RETRY_INITIAL_BACKOFF_SECONDS=1
LLM_RETRY_MAX_BACKOFF_SECONDS=10
LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

---

## 🔄 Fluxo de Execução

### Exemplo: Invocação com `priority=FAST_AND_CHEAP`

```
1. Cliente chama get_llm_client(role=ORCHESTRATOR, priority=FAST_AND_CHEAP)
   ↓
2. Verifica cache (cache_key="orchestrator_fast_and_cheap")
   ↓
3. Cache miss → Inicia seleção de provedor
   ↓
4. Tenta Gemini (mais barato)
   - Valida API key ✅
   - Circuit breaker CLOSED ✅
   - Inicializa ChatGoogleGenerativeAI ✅
   ↓
5. Adiciona ao cache
   ↓
6. Cliente invoca LLM.send(prompt)
   - Aplica circuit breaker
   - Retry com backoff
   - Registra métricas
   ↓
7. Retorna resposta
```

### Cenário de Fallback

```
1. Tenta OpenAI → Circuit breaker OPEN ❌
   ↓
2. Tenta Gemini → API key inválida ❌
   ↓
3. Fallback para Ollama local
   - Health check ✅
   - Retorna LLM local
   ↓
4. Métricas registram: provider="ollama", priority="fallback"
```

---

## 📊 Monitoramento

### Dashboards Prometheus/Grafana

#### **1. Taxa de Requisições por Provedor**

```promql
rate(llm_requests_total[5m])
```

#### **2. Latência P95 por Provedor**

```promql
histogram_quantile(0.95, llm_request_latency_seconds)
```

#### **3. Taxa de Erro por Provedor**

```promql
rate(llm_requests_total{outcome="failure"}[5m])
```

#### **4. Tokens Consumidos**

```promql
sum by (provider, model) (llm_tokens_total)
```

#### **5. Circuit Breaker Status**

- Estado atual de cada provedor
- Contagem de falhas

---

## 🧪 Testes

### Teste 1: Seleção Local Only

```bash
curl -X POST http://localhost:8000/api/v1/llm/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, world!",
    "role": "orchestrator",
    "priority": "local_only"
  }'
```

### Teste 2: Fallback Automático

1. Desabilite Gemini/OpenAI (remova API keys)
2. Invoque com `priority=high_quality`
3. Sistema deve fazer fallback para Ollama

### Teste 3: Circuit Breaker

1. Simule 5 falhas consecutivas para um provedor
2. Verifique `/llm/circuit-breakers` → estado "OPEN"
3. Próximas chamadas devem pular esse provedor

---

## 🎓 Conceitos-Chave

### 1. **Híbrido Local + Nuvem**

- Modelo local sempre disponível como fallback
- APIs de nuvem para tarefas que exigem mais capacidade

### 2. **Otimização de Custos**

- Cache de instâncias LLM (evita reinicialização)
- Seleção por prioridade (FAST_AND_CHEAP usa modelos menores)
- Monitoramento de tokens para controle de gastos

### 3. **Resiliência**

- Circuit breakers isolam falhas
- Retry automático com backoff exponencial
- Fallback garantido para modelo local

### 4. **Observabilidade**

- Métricas detalhadas (latência, erros, tokens)
- Health checks
- Cache e circuit breaker status

---

## 🚀 Próximos Passos

1. **Sprint 11**: Colaboração Agêntica (múltiplos agentes)
2. **Sprint 12**: Observabilidade avançada (Grafana dashboards)
3. **Sprint 13**: Meta-Agente de Auto-Otimização

---

## 📚 Referências

- **LangChain**: Framework de integração de LLMs
- **Circuit Breaker Pattern**: Padrão de resiliência
- **Prometheus**: Sistema de métricas
- **Ollama**: Servidor de LLMs locais

---

## ✅ Critérios de Aceitação

- [x] LLM Manager seleciona provedor dinamicamente
- [x] Fallback automático para Ollama funciona
- [x] Circuit breakers isolam falhas por provedor
- [x] Cache de LLMs reduz latência
- [x] Métricas Prometheus registram todas as operações
- [x] API endpoints permitem monitoramento e controle
- [x] Documentação completa
- [x] Testes HTTP funcionais
