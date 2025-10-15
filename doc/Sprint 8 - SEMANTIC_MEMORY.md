# Sprint 8: Consolidação do Conhecimento - Memória à Sabedoria

## 📋 Visão Geral

A Sprint 8 implementa a **Memória Semântica**, transformando experiências brutas (memória episódica) em conhecimento
estruturado e interconectado através de um grafo de conhecimento no Neo4j. O sistema automaticamente extrai entidades,
relacionamentos e insights das experiências passadas, organizando-os em uma rede de conhecimento consultável.

## 🎯 Objetivos Alcançados

### 1. **Memória Semântica com Neo4j** (`app/db/graph.py`)

Banco de dados de grafos que armazena conhecimento estruturado:

```python
class GraphDatabase:
    def query(self, cypher_query: str, params: dict = None) -> list:
        """Executa queries Cypher com resiliência e métricas"""

    def health_check(self) -> bool:
        """Verifica conectividade com Neo4j"""
```

**Características:**

- Conexão singleton thread-safe
- Circuit breaker para resiliência
- Retry automático com backoff
- Métricas Prometheus
- Timeout configurável

### 2. **Knowledge Graph Manager** (`app/core/knowledge_graph_manager.py`)

Gerencia operações no grafo de conhecimento:

```python
class KnowledgeGraphManager:
    def create_entity(self, entity_type, properties) -> str:
        """Cria entidade no grafo"""

    def create_relationship(self, from_id, to_id, rel_type) -> bool:
        """Cria relacionamento entre entidades"""

    def semantic_search(self, query, limit=5) -> list:
        """Busca semântica no grafo"""

    def get_entity_neighbors(self, entity_id, depth=1) -> list:
        """Obtém entidades relacionadas"""
```

### 3. **Knowledge Consolidator Worker** (`app/core/knowledge_consolidator_worker.py`)

Worker assíncrono que transforma memória episódica em semântica:

```python
class KnowledgeConsolidator:
    async def consolidate_batch(self, batch_size=10) -> dict:
        """
        1. Recupera experiências da memória episódica (Qdrant)
        2. Extrai entidades e relacionamentos com LLM
        3. Persiste no grafo de conhecimento (Neo4j)
        4. Marca experiências como consolidadas
        """
```

**Fluxo de Consolidação:**

```
Memória Episódica (Qdrant)
         ↓
   Recupera experiências não consolidadas
         ↓
   LLM extrai conhecimento estruturado
         ↓
   Cria entidades e relacionamentos no Neo4j
         ↓
   Marca como consolidado
```

### 4. **Ferramentas para Agentes** (`app/core/agent_tools.py`)

Três novas ferramentas que permitem aos agentes consultar o conhecimento consolidado:

#### `query_knowledge_graph(query: str)`

Consulta semântica no grafo de conhecimento.

**Exemplo:**

```python
query_knowledge_graph("Quais ferramentas estão relacionadas a erros de timeout?")

# Resposta:
# Conhecimento encontrado (3 resultados):
# - Tool 'search_web' relacionada a TimeoutError via CAUSES
# - Concept 'timeout' conectado a 'network issues'
# - Solution 'increase_timeout' resolve TimeoutError
```

#### `find_related_concepts(concept: str, max_depth: int)`

Explora relacionamentos no grafo a partir de um conceito.

**Exemplo:**

```python
find_related_concepts("Python", max_depth=2)

# Resposta:
# Conceitos relacionados a 'Python':
# - execute_python_code (relação: USES, distância: 1)
# - RestrictedPython (relação: IMPLEMENTS, distância: 1)
# - Sandbox (relação: PROVIDES, distância: 2)
# - Security (relação: ENSURES, distância: 2)
```

#### `get_entity_details(entity_name: str)`

Obtém propriedades e relacionamentos completos de uma entidade.

**Exemplo:**

```python
get_entity_details("execute_python_code")

# Resposta:
# Detalhes da entidade 'execute_python_code':
#
# Propriedades:
#   - name: execute_python_code
#   - type: Tool
#   - category: computation
#   - created_at: 2024-01-15
#
# Relacionamentos:
#   - USES → RestrictedPython
#   - PROVIDES → Sandbox
#   - HANDLES → PythonCode
#   - CAN_FAIL_WITH → SyntaxError
```

### 5. **Tipos de Entidades no Grafo**

```cypher
// Conceitos abstratos
(:Concept {name, description})

// Entidades concretas
(:Tool {name, category, permission_level})
(:Error {name, severity, frequency})
(:Solution {name, effectiveness})
(:Technology {name, version})

// Eventos
(:Experience {timestamp, type, content})
(:Action {name, outcome})
```

### 6. **Tipos de Relacionamentos**

```cypher
// Uso e dependência
(Tool)-[:USES]->(Technology)
(Agent)-[:UTILIZES]->(Tool)

// Causação
(Action)-[:CAUSES]->(Error)
(Error)-[:TRIGGERS]->(Solution)

// Resolução
(Solution)-[:SOLVES]->(Error)
(Tool)-[:FIXES]->(Problem)

// Hierarquia
(Concept)-[:IS_A]->(Category)
(Tool)-[:BELONGS_TO]->(Category)

// Temporal
(Experience)-[:HAPPENED_BEFORE]->(Experience)
(Action)-[:LEADS_TO]->(Outcome)

// Semântica
(Concept)-[:RELATED_TO]->(Concept)
(Entity)-[:SIMILAR_TO]->(Entity)
```

### 7. **Extração de Conhecimento com LLM**

O consolidator usa LLM (Knowledge Curator) para extrair conhecimento estruturado:

**Prompt para LLM:**

```
Analise a seguinte experiência e extraia conhecimento estruturado:

EXPERIÊNCIA:
{experience_content}

TAREFA:
Extraia:
1. ENTIDADES: Conceitos, ferramentas, erros, soluções mencionados
2. RELACIONAMENTOS: Como as entidades se relacionam
3. INSIGHTS: Conhecimento implícito ou padrões identificados

FORMATO JSON:
{
  "entities": [
    {"type": "Tool", "name": "...", "properties": {...}},
    {"type": "Error", "name": "...", "properties": {...}}
  ],
  "relationships": [
    {"from": "...", "to": "...", "type": "CAUSES"}
  ],
  "insights": ["..."]
}
```

### 8. **Métricas Prometheus**

```python
# Neo4j
neo4j_queries_total{operation, outcome, exception_type}
neo4j_query_latency_seconds{operation, outcome}

# Knowledge Graph
kg_queries_total{operation, outcome, exception_type}
kg_query_latency_seconds{operation, outcome}

# Consolidação
knowledge_consolidation_total{outcome, exception_type}
knowledge_consolidation_latency_seconds{outcome}
knowledge_entities_extracted_total
knowledge_relationships_created_total
```

## 🏗️ Arquitetura Completa

```
┌────────────────────────────────────────────────────────┐
│                  ENTRADA DE DADOS                      │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │         Memória Episódica (Qdrant)              │ │
│  │  - Experiências brutas                           │ │
│  │  - Embeddings vetoriais                          │ │
│  │  - Metadata temporal                             │ │
│  └────────────────┬─────────────────────────────────┘ │
└─────────────────┬─┴──────────────────────────────────┘
                   │
                   │ Recupera não consolidadas
                   ▼
┌─────────────────────────────────────────────────────────┐
│         Knowledge Consolidator Worker                   │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  1. Fetch: Busca experiências                  │    │
│  └────────────┬───────────────────────────────────┘    │
│               ▼                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  2. Extract: LLM extrai estrutura              │    │
│  │     - Entidades                                 │    │
│  │     - Relacionamentos                           │    │
│  │     - Insights                                  │    │
│  └────────────┬───────────────────────────────────┘    │
│               ▼                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  3. Persist: Salva no grafo                    │    │
│  └────────────┬───────────────────────────────────┘    │
└───────────────┼──────────────────────────────────────┘
                 │
                 │ Persiste estrutura
                 ▼
┌─────────────────────────────────────────────────────────┐
│         Memória Semântica (Neo4j)                       │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Grafo de Conhecimento                  │    │
│  │                                                 │    │
│  │  (Tool)──USES──>(Tech)                         │    │
│  │    │                                            │    │
│  │  CAN_FAIL_WITH                                 │    │
│  │    │                                            │    │
│  │    ▼                                            │    │
│  │  (Error)──SOLVED_BY──>(Solution)               │    │
│  │    │                                            │    │
│  │  RELATED_TO                                    │    │
│  │    │                                            │    │
│  │    ▼                                            │    │
│  │  (Concept)──IS_A──>(Category)                  │    │
│  └────────────────────────────────────────────────┘    │
└───────────────┬─────────────────────────────────────────┘
                 │
                 │ Agentes consultam
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Ferramentas de Consulta                    │
│                                                          │
│  - query_knowledge_graph()                              │
│  - find_related_concepts()                              │
│  - get_entity_details()                                 │
└─────────────────────────────────────────────────────────┘
```

## 🧪 Exemplo Completo: Consolidação de Experiência

### Experiência Original (Qdrant):

```json
{
  "type": "action_failure",
  "content": "Ao usar search_web('Python tutorial'), obtive TimeoutError após 30s. Resolvi aumentando timeout para 60s.",
  "metadata": {
    "tool_used": "search_web",
    "timestamp": 1704826800,
    "consolidated": false
  }
}
```

### Conhecimento Extraído pelo LLM:

```json
{
  "entities": [
    {
      "type": "Tool",
      "name": "search_web",
      "properties": {
        "category": "web",
        "timeout": 30
      }
    },
    {
      "type": "Error",
      "name": "TimeoutError",
      "properties": {
        "severity": "medium",
        "recoverable": true
      }
    },
    {
      "type": "Solution",
      "name": "increase_timeout",
      "properties": {
        "effectiveness": "high",
        "new_value": 60
      }
    }
  ],
  "relationships": [
    {
      "from": "search_web",
      "to": "TimeoutError",
      "type": "CAN_FAIL_WITH"
    },
    {
      "from": "TimeoutError",
      "to": "increase_timeout",
      "type": "SOLVED_BY"
    },
    {
      "from": "search_web",
      "to": "increase_timeout",
      "type": "FIXED_BY"
    }
  ],
  "insights": [
    "search_web pode falhar com timeout em consultas lentas",
    "Aumentar timeout resolve o problema mas pode impactar performance"
  ]
}
```

### Grafo Resultante (Neo4j):

```cypher
(:Tool {name: "search_web", category: "web", timeout: 30})
  -[:CAN_FAIL_WITH]->
(:Error {name: "TimeoutError", severity: "medium"})
  -[:SOLVED_BY]->
(:Solution {name: "increase_timeout", effectiveness: "high"})
  -[:MODIFIES]->
(:Tool {name: "search_web"})
```

### Consulta Posterior:

```python
# Agente pergunta: "Como resolver TimeoutError no search_web?"

query_knowledge_graph("Como resolver TimeoutError no search_web")

# Resposta automática do grafo:
# - TimeoutError pode ser resolvido por increase_timeout (efectividade: high)
# - search_web timeout padrão é 30s, recomenda-se 60s
# - Solução já foi aplicada com sucesso anteriormente
```

## 🔄 Integração com Outras Sprints

### Sprint 2 (Memória Episódica)

- Fonte de dados: Experiências brutas do Qdrant
- Consolidator marca experiências como processadas
- Mantém referência bidirecional

### Sprint 5 (Reflexion)

- Lições aprendidas são consolidadas como insights
- Padrões de erro viram conhecimento estruturado

### Sprint 6 (Action Module)

- Ferramentas são mapeadas como entidades
- Estatísticas de uso alimentam o grafo

### Sprint 7 (Self-Optimization)

- Melhorias aplicadas viram conhecimento
- Sistema consulta grafo para decidir otimizações

## 📈 Benefícios

### 1. **Conhecimento Duradouro**

Experiências temporais viram conhecimento permanente e estruturado.

### 2. **Descoberta de Padrões**

Grafo revela conexões não óbvias entre conceitos.

### 3. **Raciocínio Baseado em Conhecimento**

Agentes tomam decisões baseadas em conhecimento consolidado, não apenas experiências recentes.

### 4. **Escalabilidade**

Neo4j escala melhor que busca vetorial para queries complexas.

### 5. **Explica bilidade**

Caminhos no grafo explicam "como" o sistema chegou a uma conclusão.

## 📝 Checklist de Implementação

- [x] GraphDatabase com Neo4j
- [x] KnowledgeGraphManager para operações no grafo
- [x] KnowledgeConsolidator worker assíncrono
- [x] Extração de conhecimento com LLM
- [x] 3 ferramentas de consulta para agentes
- [x] Tipos de entidades e relacionamentos definidos
- [x] Métricas Prometheus completas
- [x] Resiliência com circuit breaker e retry
- [x] Integração com memória episódica
- [x] Registro no action_module
- [x] Documentação completa

## 🏆 Status: ✅ SPRINT 8 COMPLETA

A Sprint 8 transforma o Janus de um sistema com **memória** para um sistema com **sabedoria**. Experiências brutas são
destiladas em conhecimento estruturado, permitindo raciocínio mais profundo e descoberta de padrões complexos.

**Diferencial da Sprint 8:**
> Enquanto a memória episódica lembra "o que aconteceu", a memória semântica entende "o que significa" - transformando
> dados em sabedoria.
