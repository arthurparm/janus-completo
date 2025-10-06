# Sprint 3: Inteligência e Consciência - Despertar

## Status: ✅ IMPLEMENTADA

A Sprint 3 foi **totalmente implementada** com funcionalidades avançadas de **contexto ambiental** e **busca sofisticada de memórias**, permitindo ao Janus ter consciência temporal e percepção do ambiente externo.

---

## 🎯 Objetivos da Sprint

1. **Habilitar uso da memória episódica**: Implementar funções sofisticadas de busca que permitem ao agente recuperar experiências passadas relevantes com base no contexto atual
2. **Criar percepção ambiental**: Desenvolver módulo de contexto que integra data/hora atual e busca na web para enriquecer a consciência do agente

---

## 🏗️ Arquitetura Implementada

### 1. Context Manager (`app/core/context_manager.py`)

Módulo central responsável por fornecer consciência ambiental ao agente.

**Componentes:**

#### 1.1 ContextInfo
```python
class ContextInfo(BaseModel):
    timestamp: str              # Timestamp UTC atual
    datetime_info: Dict         # Informações detalhadas de data/hora
    system_info: Dict          # Informações do sistema operacional
    environment: str           # Ambiente de execução (dev/prod)
```

#### 1.2 WebSearchResult
```python
class WebSearchResult(BaseModel):
    query: str                 # Query utilizada
    results: List[Dict]        # Resultados da busca (título, URL, conteúdo, score)
    timestamp: str             # Timestamp da busca
```

#### 1.3 ContextManager
Classe principal com métodos:

- **`get_current_context()`**: Retorna contexto completo (data/hora + sistema)
- **`search_web(query, max_results, search_depth)`**: Busca na web via Tavily
- **`get_enriched_context(query, include_web_search)`**: Contexto completo + busca web opcional
- **`format_context_for_prompt()`**: Formata contexto como string para prompts de LLM

**Integração Tavily:**
- Busca inteligente na web
- Suporte a diferentes profundidades (basic/advanced)
- Tratamento robusto de erros
- Fallback gracioso se API key não configurada

---

### 2. Busca Avançada de Memórias (`app/core/memory_core.py`)

Novas funções adicionadas à classe `EpisodicMemory`:

#### 2.1 `arecall_filtered()`
Busca com múltiplos filtros:
```python
async def arecall_filtered(
    query: str,
    n_results: int = 5,
    filter_by_type: Optional[str] = None,      # Filtra por tipo de experiência
    filter_by_origin: Optional[str] = None,    # Filtra por origem
    min_score: float = 0.0,                    # Score mínimo de similaridade
    time_range: Optional[tuple] = None         # Intervalo de tempo (start, end)
) -> List[dict]
```

**Recursos:**
- Filtros compostos usando Qdrant Filter API
- Score threshold para garantir relevância
- Filtro temporal para memórias recentes
- Fallback para busca simples em caso de erro

#### 2.2 `arecall_by_timeframe()`
Busca memórias em período específico:
```python
async def arecall_by_timeframe(
    query: str,
    hours_ago: int = 24,
    n_results: int = 5
) -> List[dict]
```

#### 2.3 `arecall_recent_failures()`
Busca específica por falhas para análise:
```python
async def arecall_recent_failures(
    n_results: int = 10
) -> List[dict]
```

---

### 3. Ferramentas do Agente (`app/core/agent_tools.py`)

Novas ferramentas adicionadas para uso pelos agentes:

#### 3.1 `get_current_datetime()`
Retorna data e hora atual formatadas

#### 3.2 `get_system_info()`
Retorna informações do sistema e ambiente

#### 3.3 `search_web(query, max_results)`
Busca informações na web via Tavily

#### 3.4 `get_enriched_context(query, include_web)`
Retorna contexto completo com busca web opcional

**Integração com Agentes:**
- Tools adicionadas ao `unified_tools` (agentes normais)
- `get_current_datetime` adicionada ao `meta_agent_tools`
- Fábrica `get_tools_for_agent()` atualizada

---

### 4. API Endpoints (`app/api/v1/endpoints/context.py`)

Novos endpoints REST para contexto ambiental:

#### 4.1 `GET /api/v1/context/current`
```json
{
  "timestamp": "2025-10-06T14:30:00.000Z",
  "datetime_info": {
    "utc": "2025-10-06 14:30:00 UTC",
    "date": "2025-10-06",
    "time": "14:30:00",
    "day_of_week": "Monday",
    "month": "October",
    "year": "2025",
    "unix_timestamp": "1728224400"
  },
  "system_info": {
    "platform": "Windows",
    "platform_version": "10.0.19045",
    "architecture": "AMD64",
    "python_version": "3.11.0"
  },
  "environment": "development"
}
```

#### 4.2 `GET /api/v1/context/web-search`
Query params:
- `query` (required): Texto de busca
- `max_results` (1-10): Número de resultados
- `search_depth` (basic/advanced): Profundidade

Response:
```json
{
  "query": "latest AI developments",
  "results": [
    {
      "title": "...",
      "url": "...",
      "content": "...",
      "score": 0.95
    }
  ],
  "timestamp": "2025-10-06T14:30:00.000Z"
}
```

#### 4.3 `POST /api/v1/context/enriched`
Body:
```json
{
  "query": "optional search query",
  "include_web_search": true,
  "max_web_results": 3
}
```

#### 4.4 `GET /api/v1/context/format-prompt`
Retorna contexto formatado para inclusão em prompts

---

## 📦 Dependências Adicionadas

### requirements.txt
```txt
tavily-python>=0.3.0
```

### pyproject.toml
```toml
tavily-python = ">=0.3.0"
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (`.env`)

```env
# Sprint 3: Web Search (Tavily)
TAVILY_API_KEY=tvly-dev-xxxxxxxxxxxxxxxxxxxxx
```

### Config Settings (`app/config.py`)

```python
class AppSettings(BaseSettings):
    # Sprint 3: Web Search (Tavily)
    TAVILY_API_KEY: Optional[SecretStr] = None
```

---

## 🔧 Como Usar

### 1. Via API

```bash
# Obter contexto atual
curl http://localhost:8000/api/v1/context/current

# Buscar na web
curl "http://localhost:8000/api/v1/context/web-search?query=Python%20best%20practices&max_results=5"

# Contexto enriquecido
curl -X POST http://localhost:8000/api/v1/context/enriched \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "include_web_search": true}'
```

### 2. Programaticamente

```python
from app.core.context_manager import context_manager

# Obter contexto atual
context = context_manager.get_current_context()
print(context.datetime_info)

# Buscar na web
results = context_manager.search_web("Python tutorials", max_results=5)
for result in results.results:
    print(f"{result['title']}: {result['url']}")

# Contexto enriquecido
enriched = context_manager.get_enriched_context(
    query="latest Python news",
    include_web_search=True
)
```

### 3. Busca Avançada de Memórias

```python
from app.core.memory_core import memory_core

# Busca filtrada
memories = await memory_core.arecall_filtered(
    query="erro de conexão",
    filter_by_type="action_failure",
    hours_ago=24,
    min_score=0.7
)

# Busca por período
recent = await memory_core.arecall_by_timeframe(
    query="deploy",
    hours_ago=12,
    n_results=10
)

# Buscar falhas recentes
failures = await memory_core.arecall_recent_failures(n_results=20)
```

---

## 🎯 Casos de Uso

### 1. Consciência Temporal
O agente agora sabe a data/hora atual, permitindo:
- Agendar tarefas
- Entender contexto temporal de eventos
- Diferenciar entre manhã/tarde/noite

### 2. Busca Contextualizada na Web
O agente pode buscar informações atualizadas:
- Verificar documentação recente
- Pesquisar soluções para erros
- Obter informações sobre tecnologias

### 3. Memória Inteligente
Busca sofisticada de experiências passadas:
- Filtrar por tipo de evento
- Buscar apenas em período específico
- Analisar padrões de falhas

### 4. Enriquecimento de Prompts
Contexto ambiental em prompts LLM:
```python
context_str = context_manager.format_context_for_prompt(
    include_datetime=True,
    include_system=True
)
prompt = f"{context_str}\n\n{user_question}"
```

---

## 🧪 Testes

### Teste de Contexto Atual
```http
GET http://localhost:8000/api/v1/context/current
Accept: application/json
```

### Teste de Busca Web
```http
GET http://localhost:8000/api/v1/context/web-search?query=FastAPI&max_results=3
Accept: application/json
```

### Teste de Contexto Enriquecido
```http
POST http://localhost:8000/api/v1/context/enriched
Content-Type: application/json

{
  "query": "Python async programming",
  "include_web_search": true,
  "max_web_results": 5
}
```

---

## 📊 Métricas e Observabilidade

O sistema mantém as métricas existentes:
- Latência de busca de memória
- Taxa de acerto/erro em buscas
- Uso de APIs externas (Tavily)

---

## 🚀 Melhorias Futuras

1. **Cache de Busca Web**: Implementar cache para reduzir chamadas à API Tavily
2. **Filtros Avançados**: Adicionar mais filtros (tags, prioridade, etc.)
3. **Contexto Geográfico**: Adicionar localização ao contexto
4. **Integração com Neo4j**: Relacionar contexto temporal com memória semântica
5. **Análise de Tendências**: Detectar padrões temporais nas memórias

---

## 🔗 Relação com Outras Sprints

- **Sprint 2 (Memória Episódica)**: Base para busca avançada
- **Sprint 4 (ReAct Cycle)**: Uso de contexto em decisões do agente
- **Sprint 5 (Reflexion)**: Análise temporal de falhas
- **Sprint 8 (Knowledge Consolidator)**: Enriquecimento temporal do grafo de conhecimento

---

## ✅ Checklist de Implementação

- [x] Criar módulo `context_manager.py`
- [x] Implementar integração com Tavily
- [x] Adicionar funções de busca filtrada à memória
- [x] Criar ferramentas de contexto para agentes
- [x] Implementar endpoints API
- [x] Adicionar dependências ao projeto
- [x] Configurar variáveis de ambiente
- [x] Atualizar documentação
- [x] Testes básicos de integração

---

## 📝 Notas Técnicas

### Segurança
- API key do Tavily armazenada como `SecretStr`
- Fallback gracioso se API não disponível
- Validação de queries antes de buscar

### Performance
- Busca web assíncrona
- Cache de contexto (pode ser implementado)
- Filtros no nível do Qdrant (eficiente)

### Resiliência
- Try/except em todas as chamadas externas
- Logs estruturados para debugging
- Timeout configurável para buscas

---

**Sprint implementada por:** Claude Code
**Data:** 2025-10-06
**Status:** ✅ Produção Ready
