# Knowledge Consolidator Worker - Sprint 8

## Visão Geral

O **Knowledge Consolidator Worker** é o componente responsável por transformar a **memória episódica** (experiências
brutas armazenadas no Qdrant) em **memória semântica** (conhecimento estruturado no Neo4j).

Este worker implementa a funcionalidade-chave da **Sprint 8: Consolidação do Conhecimento – Memória à Sabedoria**.

## Arquitetura

```
┌─────────────────────┐
│  Memória Episódica  │
│     (Qdrant)        │
│  - Experiências     │
│  - Embeddings       │
└──────────┬──────────┘
           │
           │ 1. Recupera
           ▼
┌─────────────────────┐
│  Knowledge          │
│  Consolidator       │
│  Worker             │
│                     │
│  2. Extrai com LLM: │
│  - Entidades        │
│  - Relacionamentos  │
│  - Insights         │
└──────────┬──────────┘
           │
           │ 3. Persiste
           ▼
┌─────────────────────┐
│  Memória Semântica  │
│     (Neo4j)         │
│  - Grafo de         │
│    Conhecimento     │
└─────────────────────┘
```

## Funcionalidades

### 1. Extração de Conhecimento com LLM

O worker utiliza um **LLM especializado** (Knowledge Curator) para analisar cada experiência e extrair:

- **Entidades**: Conceitos, tecnologias, ferramentas, pessoas, erros, soluções
- **Relacionamentos**: Como as entidades se relacionam (USES, CAUSES, SOLVES, etc.)
- **Insights**: Lições aprendidas e conhecimento-chave

### 2. Tipos de Entidades Suportados

- `CONCEPT`: Conceitos abstratos
- `TECHNOLOGY`: Tecnologias específicas (FastAPI, Neo4j, Qdrant)
- `TOOL`: Ferramentas utilizadas
- `PERSON`: Pessoas ou agentes
- `ERROR`: Tipos de erros
- `SOLUTION`: Soluções implementadas
- `PATTERN`: Padrões de design

### 3. Tipos de Relacionamentos

- `USES`: Entidade A utiliza entidade B
- `RELATES_TO`: Relação genérica
- `CAUSES`: Entidade A causa entidade B
- `SOLVES`: Entidade A resolve entidade B
- `DEPENDS_ON`: Dependência
- `IMPLEMENTS`: Implementação de padrão

### 4. Estrutura do Grafo

#### Nós Criados

**Experience**

```cypher
(:Experience {
  id: "uuid",
  timestamp: "2025-10-06T14:30:00Z",
  type: "tool_usage",
  consolidated_at: datetime(),
  insights: "texto com insights extraídos"
})
```

**Entidades (diversos tipos)**

```cypher
(:TECHNOLOGY {
  name: "Neo4j",
  last_seen: datetime(),
  ... propriedades customizadas ...
})
```

#### Relacionamentos Criados

**MENTIONS** (Experiência menciona Entidade)

```cypher
(e:Experience)-[:MENTIONS]->(n:TECHNOLOGY)
```

**Relacionamentos entre Entidades**

```cypher
(a:TECHNOLOGY)-[:USES {
  discovered_at: datetime(),
  source_experience: "uuid"
}]->(b:TOOL)
```

## API

### Endpoint Principal

**POST** `/api/v1/knowledge/consolidate`

Aciona o processo de consolidação em lote.

**Response:**

```json
{
  "message": "Processo de consolidação concluído.",
  "summary": "Consolidação concluída. 10/10 experiências processadas com sucesso. 25 entidades e 15 relacionamentos criados no grafo em 12.5s."
}
```

### Uso Programático

```python
from app.core.knowledge_consolidator_worker import knowledge_consolidator

# Consolidar uma experiência específica
result = await knowledge_consolidator.consolidate_experience(
    experience_id="abc-123",
    experience_content="Conteúdo da experiência...",
    metadata={"type": "tool_usage", "timestamp": "..."}
)

# Consolidar lote de experiências
stats = await knowledge_consolidator.consolidate_batch(
    limit=10,
    min_score=0.0
)
```

## Resiliência

O worker implementa múltiplas camadas de resiliência:

1. **Circuit Breaker**: Protege contra falhas em cascata
2. **Retry com Backoff Exponencial**: 3 tentativas com backoff de 2-10s
3. **Timeouts**: Limites de tempo para operações LLM e Neo4j
4. **Graceful Degradation**: Continua processando mesmo se algumas experiências falharem

## Observabilidade

### Métricas Prometheus

```
# Total de consolidações
knowledge_consolidation_total{outcome="success|error", exception_type=""}

# Latência de consolidação
knowledge_consolidation_latency_seconds{outcome="success|error"}

# Entidades extraídas
knowledge_entities_extracted_total

# Relacionamentos criados
knowledge_relationships_created_total
```

### Logs Estruturados

```python
logger.info(
    f"Consolidação concluída para experiência {experience_id}: "
    f"{num_entities} entidades, {num_rels} relacionamentos em {elapsed:.2f}s"
)
```

## Configuração

O worker utiliza configurações do `app/config.py`:

```python
# LLM para extração (usa Knowledge Curator)
OLLAMA_CURATOR_MODEL = "phi3:mini"

# Circuit Breaker
LLM_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
LLM_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60

# Neo4j
NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Qdrant
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
```

## Fluxo de Consolidação

1. **Inicialização**
    - Conecta ao Qdrant (memória episódica)
    - Conecta ao Neo4j (memória semântica)
    - Inicializa LLM (Knowledge Curator)

2. **Recuperação de Experiências**
    - Busca experiências não consolidadas no Qdrant
    - Verifica se já foram processadas (evita duplicação)

3. **Extração de Conhecimento**
    - Envia experiência ao LLM com prompt especializado
    - Parseia resposta JSON com entidades, relacionamentos e insights

4. **Persistência no Grafo**
    - Cria nó da experiência
    - Cria/atualiza nós de entidades
    - Cria relacionamentos `MENTIONS`
    - Cria relacionamentos entre entidades
    - Armazena insights como propriedades

5. **Estatísticas e Logging**
    - Registra métricas Prometheus
    - Loga resultado da consolidação

## Exemplo de Extração

**Entrada (Experiência):**

```
Conteúdo: "O sistema implementou o padrão Circuit Breaker para proteger
a conexão com Neo4j. O LLM Manager utiliza Ollama como fallback quando
OpenAI falha."

Metadados: {
  "type": "system_architecture",
  "timestamp": "2025-10-06T14:40:00Z"
}
```

**Saída (Conhecimento Extraído):**

```json
{
  "entities": [
    {
      "name": "Circuit Breaker",
      "type": "PATTERN",
      "properties": {}
    },
    {
      "name": "Neo4j",
      "type": "TECHNOLOGY",
      "properties": {}
    },
    {
      "name": "LLM Manager",
      "type": "CONCEPT",
      "properties": {}
    },
    {
      "name": "Ollama",
      "type": "TECHNOLOGY",
      "properties": {
        "role": "local"
      }
    },
    {
      "name": "OpenAI",
      "type": "TECHNOLOGY",
      "properties": {
        "role": "cloud"
      }
    }
  ],
  "relationships": [
    {
      "from": "Circuit Breaker",
      "to": "Neo4j",
      "type": "PROTECTS"
    },
    {
      "from": "LLM Manager",
      "to": "Ollama",
      "type": "USES"
    },
    {
      "from": "Ollama",
      "to": "OpenAI",
      "type": "FALLBACK_FOR"
    }
  ],
  "insights": [
    {
      "text": "Sistema utiliza padrões de resiliência para garantir alta disponibilidade",
      "confidence": 0.9
    }
  ]
}
```

## Queries Úteis

### Ver todas as tecnologias mencionadas

```cypher
MATCH (t:TECHNOLOGY)
RETURN t.name, t.last_seen
ORDER BY t.last_seen DESC
```

### Ver relacionamentos entre componentes

```cypher
MATCH (a)-[r]->(b)
WHERE NOT a:Experience
RETURN type(r) as rel, a.name as from, b.name as to
```

### Encontrar experiências sobre uma tecnologia

```cypher
MATCH (tech:TECHNOLOGY {name: "Neo4j"})<-[:MENTIONS]-(e:Experience)
RETURN e.id, e.type, e.timestamp
ORDER BY e.timestamp DESC
```

### Ver insights descobertos

```cypher
MATCH (e:Experience)
WHERE e.insights IS NOT NULL
RETURN e.id, e.insights
LIMIT 10
```

## Testes

Execute os testes de integração:

```bash
# Via HTTP Client (IntelliJ/VSCode)
# Abrir: http/sprint/test_knowledge_consolidation.http
```

## Roadmap

### Melhorias Futuras

1. **Consolidação Incremental**: Processar apenas experiências novas
2. **Priorização**: Consolidar primeiro experiências mais importantes
3. **Merge Inteligente**: Detectar entidades duplicadas com nomes diferentes
4. **Validação de Qualidade**: Verificar qualidade das extrações do LLM
5. **Consolidação em Background**: Worker autônomo que roda periodicamente
6. **Cache de Extrações**: Evitar reprocessar experiências similares

## Referências

- **Sprint 8**: SPRINTS JANUS.md
- **Memória Episódica**: `app/core/memory_core.py`
- **Grafo Neo4j**: `app/db/graph.py`
- **LLM Manager**: `app/core/llm_manager.py`
