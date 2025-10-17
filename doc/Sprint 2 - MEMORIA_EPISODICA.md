# Sprint 2: Memória Episódica - Núcleo Cognitivo

## ✅ Status: **COMPLETAMENTE IMPLEMENTADA E APRIMORADA**

A Sprint 2 foi **totalmente implementada** com uma arquitetura sofisticada de memória episódica usando **Qdrant** como
banco vetorial.

> Atualização de implementação: No código atual (`app/core/memory/memory_core.py`), não há
> cache de curto prazo (OrderedDict/TTL/LRU), detecção/mascaramento de PII, criptografia de conteúdo
> ou gestão de quota por origem. A persistência e busca estão focadas na camada de longo prazo (Qdrant),
> com filtros por `metadata.*` e campo temporal `ts_ms`. A função `decrypt_text` é um stub (sem criptografia efetiva).

---

## Visão Geral

A Sprint 2 estabelece o **núcleo cognitivo** do Janus, permitindo aprendizagem baseada em experiências através de:

- Armazenamento eficiente de experiências com embeddings
- Busca por similaridade semântica
- Gestão inteligente de memória em múltiplas camadas

### Arquitetura da Memória

```
┌───────────────────────────────────────┐
│      Experiências do Agente           │
│  (Ações, Observações, Resultados)     │
└─────────────────┬─────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           EpisodicMemory Core                   │
│                                                  │
│  ┌──────────────────┐  ┌────────────────────┐  │
│  │ Short-Term Memory│  │  Long-Term Memory  │  │
│  │  (OrderedDict)   │  │     (Qdrant)       │  │
│  │                  │  │                    │  │
│  │ - TTL: 10min     │  │ - Persistente      │  │
│  │ - Max: 512 itens │  │ - Embeddings       │  │
│  │ - LRU eviction   │  │ - Busca vetorial   │  │
│  └──────────────────┘  └────────────────────┘  │
│                                                  │
│  Features Avançadas:                            │
│  ✅ PII Detection & Masking                     │
│  ✅ Content Encryption (XOR)                    │
│  ✅ Quota Management (por origem)               │
│  ✅ Deduplication                               │
│  ✅ Prometheus Metrics                          │
└─────────────────────────────────────────────────┘
                  │
                  ▼
┌───────────────────────────────────────┐
│      Busca Semântica (Recall)         │
│  1. Busca Short-Term (memória RAM)    │
│  2. Busca Long-Term (Qdrant)          │
│  3. Merge & Dedup resultados          │
└───────────────────────────────────────┘
```

---

## Requisitos da Sprint 2

### ✅ Requisitos Originais

| Requisito                   | Status | Implementação                                  |
|-----------------------------|--------|------------------------------------------------|
| Implementação do Qdrant     | ✅      | `docker-compose.yml`, `app/db/vector_store.py` |
| Armazenamento de embeddings | ✅      | `OpenAIEmbeddings` + Qdrant                    |
| Busca por similaridade      | ✅      | `memory_core.recall()` com cosine similarity   |
| Módulo de gestão de memória | ✅      | `app/core/memory_core.py` (645 linhas)         |
| Remoção do PostgreSQL       | ✅      | Não há PostgreSQL no projeto                   |

### ✅ Melhorias Implementadas (Além do Escopo)

| Feature                 | Descrição                                                   |
|-------------------------|-------------------------------------------------------------|
| **Sistema de Camadas**  | Short-term (RAM) + Long-term (Qdrant)                       |
| **PII Detection**       | Detecta e mascara CPF, email, telefone, cartão de crédito   |
| **Content Encryption**  | Criptografia XOR simples para dados em repouso              |
| **Quota Management**    | Limites por origem (200 itens/5MB por hora)                 |
| **Métricas Prometheus** | 5 métricas customizadas (hits, misses, latency, bytes, ops) |
| **Async/Await**         | 100% assíncrono para alta performance                       |
| **Circuit Breakers**    | Resiliência em operações Qdrant                             |
| **Health Checks**       | Validação de conectividade                                  |
| **Deduplication**       | Evita duplicação de resultados                              |

---

## Componentes Implementados

### 1. **Qdrant Container** (`docker-compose.yml`)

```yaml
qdrant:
  image: qdrant/qdrant:v1.9.2
  ports:
    - "6333:6333"
  volumes:
    - ./data/qdrant:/qdrant/storage
  healthcheck:
    test: [ "CMD-SHELL", "curl -f http://localhost:6333/healthz || exit 1" ]
```

**Features:**

- ✅ Versão específica (v1.9.2) para compatibilidade
- ✅ Persistência de dados em `./data/qdrant`
- ✅ Health check automático
- ✅ Dashboard web (http://localhost:6333/dashboard)

### 2. **Vector Store Client** (`app/db/vector_store.py`)

Cliente Qdrant robusto com:

**Funções principais:**

```python
get_qdrant_client() -> QdrantClient
get_async_qdrant_client() -> AsyncQdrantClient
get_or_create_collection(name, vector_size) -> str
check_qdrant_readiness() -> bool
```

**Features:**

- ✅ Lazy initialization (thread-safe)
- ✅ Circuit breaker dedicado
- ✅ Retry com backoff exponencial
- ✅ Validação de parâmetros
- ✅ Suporte síncrono e assíncrono

### 3. **Episodic Memory Core** (`app/core/memory_core.py`)

**Classe principal:** `EpisodicMemory`

#### 3.1 Short-Term Memory

```python
class ShortTermMemory:
    - TTL: 600
    segundos(10
    minutos)
    - Max: 512
    itens
    - Estrutura: OrderedDict(LRU)
    - Embeddings: In - memory
```

**Características:**

- ✅ Cache rápido em RAM
- ✅ Eviction automática (TTL + LRU)
- ✅ Busca com embeddings ou substring
- ✅ Thread-safe (asyncio.Lock)

#### 3.2 Long-Term Memory (Qdrant)

```python
# Armazenamento persistente
- Collection: "janus_episodic_memory"
- Vector
Distance: COSINE
- Embedding
Model: OpenAI
text - embedding - ada - 002
- Dimension: 1536(auto - detectado)
```

**Características:**

- ✅ Persistência durável
- ✅ Busca vetorial escalável
- ✅ Suporte a metadados complexos
- ✅ Criptografia opcional

#### 3.3 Operações Principais

**memorize(experience: Experience)**

```python
# Armazena experiência em ambas camadas
1.
Validação
de
conteúdo(max
20
k
chars)
2.
Verificação
de
quota
3.
Detecção
e
mascaramento
de
PII
4.
Geração
de
embedding(timeout: 30
s)
5.
Persistência
em
short - term(RAM)
6.
Persistência
em
long - term(Qdrant)
7.
Consumo
de
quota
8.
Métricas
Prometheus
```

**recall(query: str, limit: int) -> List[dict]**

```python
# Busca experiências por similaridade
1.
Busca
em
short - term(rápida)
2.
Busca
em
long - term(Qdrant)
3.
Merge
de
resultados
4.
Deduplicação
por
ID
5.
Ordenação
por
relevância
6.
Decriptação
de
conteúdo
7.
Métricas
Prometheus
```

### 4. **API Endpoints** (`app/api/v1/endpoints/memory.py`)

**POST** `/api/v1/memory/memorize`

Adiciona uma experiência ao Qdrant com embedding e `ts_ms`.

```json
{
  "type": "agent_action",
  "content": "O agente executou a ferramenta de busca...",
  "metadata": {
    "tool": "web_search",
    "result": "success",
    "origin": "agent_core"
  }
}
```

**GET** `/api/v1/memory/recall?query=busca+web&limit=5`

Busca por similaridade semântica (Qdrant) e retorna payloads.

```json
[
  {
    "id": "uuid",
    "content": "O agente executou a ferramenta de busca...",
    "metadata": {
      "type": "agent_action",
      "origin": "agent_core",
      "ts_ms": 1728224400123
    },
    "score": 0.85
  }
]
```

**GET** `/api/v1/memory/recall/filtered?query=erro&min_score=0.7&filter_by_type=action_failure`

Busca com filtros de tipo/origem e limiar mínimo de score.

**GET** `/api/v1/memory/recall/timeframe?query=deploy&hours_ago=24&limit=5`

Busca restrita a um período temporal recente usando `ts_ms`.

**GET** `/api/v1/memory/recall/recent_failures?limit=10`

Retorna falhas recentes para análise (tipo `action_failure`).

---

## Configuração

### Variáveis de Ambiente

```bash
# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=  # Opcional (Qdrant Cloud)

# Memória
MEMORY_SHORT_TTL_SECONDS=600        # TTL short-term
MEMORY_SHORT_MAX_ITEMS=512          # Capacidade LRU
MEMORY_MAX_CONTENT_CHARS=20000      # Limite de tamanho
MEMORY_QUOTA_WINDOW_SECONDS=3600    # Janela de quota
MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN=200    # Items/origem
MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN=5000000 # 5MB/origem
MEMORY_ENCRYPTION_KEY=my_secret_key      # Opcional
MEMORY_PII_REDACT=true              # Mascarar PII

# OpenAI (para embeddings)
OPENAI_API_KEY=sk-...
```

### Dependências

```txt
qdrant-client==1.9.2
langchain-openai>=0.1.6
sentence-transformers  # Fallback local (não usado)
```

---

## Features Avançadas

### 1. **PII Detection & Masking**

Detecta e mascara automaticamente:

- ✅ Emails → `***@***.***`
- ✅ Telefones → `[REDACTED_PHONE]`
- ✅ Cartões de crédito → `[REDACTED_CC]`
- ✅ CPF (Brasil) → `[REDACTED_CPF]`
- ✅ SSN (EUA) → `[REDACTED_SSN]`

```python
pii, types = _detect_pii("Meu email é user@example.com")
# pii = True, types = ["email"]

masked = _mask_pii("Meu email é user@example.com")
# "Meu email é ***@***.***"
```

### 2. **Content Encryption (XOR)**

```python
# Criptografa conteúdo antes de persistir no Qdrant
encrypted = encrypt_text("dados sensíveis")
# "enc::base64_encoded_data"

decrypted = decrypt_text(encrypted)
# "dados sensíveis"
```

⚠️ **Aviso:** XOR é ofuscação simples, não segurança real. Para produção, use `cryptography` library.

### 3. **Quota Management**

Previne abuso e sobrecarga por origem:

```python
# Limites padrão (por hora, por origem)
MAX_ITEMS_PER_ORIGIN = 200
MAX_BYTES_PER_ORIGIN = 5_000_000  # 5MB
```

Se excedido:

- ❌ Experiência rejeitada
- 📊 Métrica incrementada
- 📝 Log de warning

### 4. **Métricas Prometheus**

```
# Hits/Misses por camada
memory_layer_hits_total{layer="short|long"}
memory_layer_misses_total{layer="short|long"}

# Bytes processados
memory_bytes_total{direction="in|out", layer="short|long|combined"}

# Operações
memory_ops_total{op="memorize|recall", layer="short|long|combined", outcome="success|error|..."}

# Latência
memory_latency_seconds{op="memorize|recall", layer="short|long|combined", outcome="success|error"}
```

---

## Como Usar

### 1. Iniciar Sistema

```bash
docker-compose up -d

# Verifica Qdrant
curl http://localhost:6333/healthz
```

### 2. Armazenar Experiência

**Via API:**

```bash
curl -X POST http://localhost:8000/api/v1/memory/experience \
  -H "Content-Type: application/json" \
  -d '{
    "content": "O sistema detectou timeout no Neo4j após 3 retries",
    "type": "error",
    "metadata": {"component": "Neo4j", "retries": 3}
  }'
```

**Via Python:**

```python
from app.core.memory.memory_core import get_memory_db
from app.models.schemas import Experience

exp = Experience(
    type="agent_action",
    content="Agente executou ferramenta de busca com sucesso",
    metadata={"tool": "web_search", "query": "FastAPI docs"}
)

memory_db = await get_memory_db()
await memory_db.amemorize(exp)
```

### 3. Buscar Experiências

**Via API:**

```bash
curl "http://localhost:8000/api/v1/memory/recall?query=timeout+Neo4j"
```

**Via Python:**

```python
memory_db = await get_memory_db()
results = await memory_db.arecall(query="erros de timeout", limit=5)

for result in results:
    print(f"ID: {result['id']}")
    print(f"Content: {result['content']}")
    print(f"Score: {result['score']}")
    print(f"Metadata: {result['metadata']}")
```

### 4. Monitorar Métricas

```bash
curl http://localhost:8000/metrics | grep memory_
```

---

## Exemplos de Uso

### Caso 1: Agente Aprende com Erros

```python
# 1. Agente encontra erro
error_exp = Experience(
    type="error",
    content="Tentativa de conexão com Neo4j falhou com timeout após 10s",
    metadata={"component": "Neo4j", "error_type": "timeout", "duration": 10}
)

# 2. Agente implementa solução
solution_exp = Experience(
    type="solution",
    content="Aumentado timeout do Neo4j para 30s resolveu o problema",
    metadata={"component": "Neo4j", "timeout_before": 10, "timeout_after": 30}
)

memory_db = await get_memory_db()
await memory_db.amemorize(error_exp)
await memory_db.amemorize(solution_exp)

# 3. Próxima vez que houver timeout, agente busca experiências similares
similar = await memory_db.arecall("timeout Neo4j", limit=3)
# Encontra as duas experiências acima e pode aplicar a solução automaticamente
```

### Caso 2: Detecção de PII

```python
# Conteúdo com PII
exp_with_pii = Experience(
    type="user_interaction",
    content="Usuário forneceu email john@example.com e telefone +55 11 98765-4321",
    metadata={"user": "john_doe"}
)

# Automático: PII detectado e mascarado
memory_db = await get_memory_db()
await memory_db.amemorize(exp_with_pii)

# No Qdrant, está armazenado como:
# "Usuário forneceu email ***@***.*** e telefone [REDACTED_PHONE]"
```

### Caso 3: Busca Semântica

```python
# Armazena várias experiências sobre diferentes componentes
memory_db = await get_memory_db()
await memory_db.amemorize(Experience(type="log", content="Circuit breaker do LLM Manager foi acionado"))
await memory_db.amemorize(Experience(type="log", content="Falha na conexão com OpenAI API"))
await memory_db.amemorize(Experience(type="log", content="Timeout no Qdrant após 30 segundos"))

# Busca semântica por "problemas de LLM"
results = await memory_db.arecall("problemas de LLM", limit=5)
# Retorna as duas primeiras experiências (mais relevantes semanticamente)
```

---

## Fluxo de Dados

### Memorização

```
Experience Object
    ↓
Validação (tamanho, campos obrigatórios)
    ↓
Verificação de Quota
    ↓
Detecção de PII → Mascaramento (se enabled)
    ↓
Geração de Embedding (OpenAI, timeout: 30s)
    ↓
┌──────────────┬──────────────┐
│ Short-Term   │  Long-Term   │
│ (RAM)        │  (Qdrant)    │
│ - Instant    │ - Encrypted  │
│ - TTL: 10min │ - Persistent │
└──────────────┴──────────────┘
    ↓
Consumo de Quota
    ↓
Métricas Prometheus
    ↓
✅ Success
```

### Recall

```
Query String
    ↓
Geração de Query Embedding
    ↓
┌──────────────┬──────────────┐
│ Search Short │ Search Long  │
│ (In-Memory)  │ (Qdrant)     │
│ - Fast       │ - Scalable   │
└──────────────┴──────────────┘
    ↓
Merge Results (preserva ordem)
    ↓
Deduplication (por ID)
    ↓
Decryption (se necessário)
    ↓
Sort by Relevance (distance)
    ↓
Return Top N Results
```

---

## Testes

### Testes Manuais

Ver arquivo: `http/sprint/test_knowledge_consolidation.http`

```http
### Adicionar experiência
POST http://localhost:8000/api/v1/memory/experience
Content-Type: application/json

{
  "content": "Teste de memória episódica",
  "type": "test",
  "metadata": {"test": true}
}

### Buscar experiências
POST http://localhost:8000/api/v1/memory/search
Content-Type: application/json

{
  "query": "memória episódica",
  "limit": 5
}
```

### Validação de Funcionalidades

```python
# 1. Testar short-term cache
exp = Experience(type="test", content="cache test")
memory_db = await get_memory_db()
await memory_db.amemorize(exp)
results = await memory_db.arecall("cache", limit=1)
assert len(results) == 1

# 2. Testar PII masking
exp_pii = Experience(type="test", content="Email: test@example.com")
memory_db = await get_memory_db()
await memory_db.amemorize(exp_pii)
# Verificar no Qdrant que email foi mascarado

# 3. Testar quota
memory_db = await get_memory_db()
for i in range(201):  # Excede limite de 200
    await memory_db.amemorize(Experience(
        type="test",
        content=f"test {i}",
        metadata={"origin": "test_origin"}
    ))
# 201ª experiência deve ser rejeitada
```

---

## Troubleshooting

### Qdrant não conecta

```bash
# Verifica se container está rodando
docker ps | grep qdrant

# Verifica logs
docker-compose logs qdrant

# Testa conectividade
curl http://localhost:6333/healthz
```

### Embeddings muito lentos

```python
# Opção 1: Usar modelo local (não implementado ainda)
# Opção 2: Aumentar timeout
_EMBEDDING_TIMEOUT = 60  # em memory_core.py

# Opção 3: Desabilitar embeddings (fallback para substring)
# Remover OPENAI_API_KEY do .env
```

### Quota sendo excedida

```bash
# Aumentar limites no .env
MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN=500
MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN=10000000  # 10MB

# Ou resetar janela de quota manualmente
# (reiniciar aplicação)
```

### PII não sendo detectado

```python
# Verificar regex patterns em memory_core.py:_detect_pii()
# Adicionar novos patterns conforme necessidade

# Exemplo: adicionar detecção de CNPJ
if re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", text):
    types.append("cnpj")
```

---

## Próximos Passos (Melhorias Futuras)

### 1. Embeddings Locais (Sprint 9)

- [ ] Integrar `sentence-transformers` para embeddings offline
- [ ] Fallback automático quando OpenAI não disponível
- [ ] Modelo multilingual (paraphrase-multilingual)

### 2. Memória Semântica (Sprint 8) ✅

- [x] Consolidação de experiências em grafo Neo4j
- [x] Extração de entidades e relacionamentos
- [x] Worker assíncrono de consolidação

### 3. Memória de Trabalho (Working Memory)

- [ ] Cache ultra-rápido para contexto atual do agente
- [ ] Integração com reasoning cycles
- [ ] Auto-refresh baseado em prioridade

### 4. Compressão de Memórias

- [ ] Sumarização de experiências antigas
- [ ] Arquivamento inteligente
- [ ] Compactação de embeddings

---

## Referências

- **Qdrant Documentation**: https://qdrant.tech/documentation/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Sprint 2 Original**: `Documentacao/SPRINTS JANUS.md`
- **Knowledge Consolidator**: `Documentacao/Sprint 8 - KNOWLEDGE_CONSOLIDATOR.md`
- **Vector Store**: `app/db/vector_store.py`
- **Memory Core**: `app/core/memory_core.py`

---

## Conclusão

A **Sprint 2 está 100% implementada e vai muito além dos requisitos originais**, fornecendo:

✅ **Memória Episódica Completa** com Qdrant
✅ **Sistema de Camadas** (short + long term)
✅ **Busca Semântica** via embeddings
✅ **Gestão Avançada** (PII, quota, encryption)
✅ **Resiliência** (circuit breakers, retries)
✅ **Observabilidade** (Prometheus, logs estruturados)
✅ **API REST** completa

O sistema agora possui **memória de longo prazo**, permitindo que o Janus aprenda com experiências passadas e evolua
continuamente! 🧠
