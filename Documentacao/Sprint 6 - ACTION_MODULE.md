# Sprint 6: Agente Multitarefa e Gateway de Ferramentas

## 📋 Visão Geral

A Sprint 6 implementa o **Action Module**, um sistema extensível de gerenciamento de ferramentas (tools) que permite ao Janus interagir com o mundo externo de forma dinâmica, organizada e monitorada.

## 🎯 Objetivos Alcançados

### 1. **Action Module Core** (`app/core/action_module.py`)

Sistema centralizado de registro e gerenciamento de ferramentas com funcionalidades avançadas:

#### Componentes Principais:

##### **ActionRegistry**
- Registro centralizado de todas as ferramentas disponíveis
- Categorização por tipo (filesystem, api, database, computation, web, system, custom)
- Controle de permissões (read_only, safe, write, dangerous)
- Rate limiting por ferramenta
- Telemetria completa com Prometheus
- Histórico de chamadas

##### **DynamicToolGenerator**
Permite criar ferramentas em runtime de três formas:

1. **A partir de função Python:**
```python
def my_custom_function(x: int, y: int) -> int:
    return x + y

tool = DynamicToolGenerator.from_function_spec(
    name="add_numbers",
    description="Soma dois números",
    func=my_custom_function
)
```

2. **A partir de endpoint HTTP:**
```python
tool = DynamicToolGenerator.from_api_endpoint(
    name="get_users",
    description="Obtém lista de usuários",
    endpoint_url="https://api.example.com/users",
    method="GET",
    headers={"Authorization": "Bearer token"}
)
```

3. **A partir de código Python (string):**
```python
code = """
def execute(temperature_celsius: float) -> float:
    return temperature_celsius * 9/5 + 32
"""

tool = DynamicToolGenerator.from_python_code(
    name="celsius_to_fahrenheit",
    description="Converte Celsius para Fahrenheit",
    code=code,
    function_name="execute"
)
```

#### Categorias de Ferramentas:

```python
class ToolCategory(Enum):
    FILESYSTEM = "filesystem"      # Operações de arquivo
    API = "api"                    # Chamadas HTTP
    DATABASE = "database"          # Consultas a bancos
    COMPUTATION = "computation"    # Cálculos e processamento
    WEB = "web"                    # Busca web e scraping
    SYSTEM = "system"              # Informações do sistema
    CUSTOM = "custom"              # Ferramentas customizadas
```

#### Níveis de Permissão:

```python
class PermissionLevel(Enum):
    READ_ONLY = "read_only"        # Apenas leitura, sem side-effects
    SAFE = "safe"                  # Operações seguras
    WRITE = "write"                # Pode modificar dados
    DANGEROUS = "dangerous"        # Requer confirmação do usuário
```

#### Metadados de Ferramentas:

```python
@dataclass
class ToolMetadata:
    name: str
    category: ToolCategory
    description: str
    permission_level: PermissionLevel
    rate_limit_per_minute: Optional[int]  # None = sem limite
    requires_confirmation: bool
    tags: List[str]  # Para busca e organização
```

### 2. **Integração com Sistema Existente** (`app/core/agent_tools.py`)

Todas as ferramentas existentes foram registradas automaticamente no Action Module:

```python
def _register_all_tools_in_action_module():
    # Filesystem tools
    action_registry.register(
        write_file,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.WRITE,
        rate_limit_per_minute=30
    )

    # Memory tools
    action_registry.register(
        recall_experiences,
        category=ToolCategory.DATABASE,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["memory", "episodic"]
    )

    # Context tools (Sprint 3)
    action_registry.register(
        search_web,
        category=ToolCategory.WEB,
        permission_level=PermissionLevel.SAFE,
        rate_limit_per_minute=20,
        tags=["context", "search", "external"]
    )

    # Python sandbox (Sprint 4)
    action_registry.register(
        execute_python_code,
        category=ToolCategory.COMPUTATION,
        permission_level=PermissionLevel.SAFE,
        rate_limit_per_minute=30,
        tags=["python", "sandbox"]
    )

    # Faulty tools (Sprint 5)
    for faulty_tool in get_faulty_tools():
        action_registry.register(
            faulty_tool,
            category=ToolCategory.CUSTOM,
            tags=["faulty", "training", "reflexion"]
        )
```

### 3. **API REST para Gerenciamento** (`app/api/v1/endpoints/tools.py`)

Endpoints completos para gerenciar ferramentas via API:

#### `GET /api/v1/tools/`
Lista todas as ferramentas com filtros opcionais.

**Query Parameters:**
- `category`: Filtrar por categoria
- `permission_level`: Filtrar por nível de permissão
- `tags`: Filtrar por tags (separadas por vírgula)

**Response:**
```json
{
  "total": 15,
  "tools": [
    {
      "name": "write_file",
      "description": "Escreve conteúdo em um arquivo dentro do workspace seguro.",
      "category": "filesystem",
      "permission_level": "write",
      "rate_limit_per_minute": 30,
      "requires_confirmation": false,
      "tags": []
    },
    {
      "name": "search_web",
      "description": "Busca informações na web usando Tavily.",
      "category": "web",
      "permission_level": "safe",
      "rate_limit_per_minute": 20,
      "requires_confirmation": false,
      "tags": ["context", "search", "external"]
    }
  ]
}
```

#### `GET /api/v1/tools/{tool_name}`
Obtém detalhes de uma ferramenta específica.

#### `GET /api/v1/tools/stats/usage`
Estatísticas de uso de ferramentas.

**Response:**
```json
{
  "total_tools_registered": 15,
  "total_calls": 1247,
  "successful_calls": 1198,
  "success_rate": 0.961,
  "tool_usage": {
    "execute_python_code": {
      "total": 234,
      "success": 230,
      "avg_duration": 0.145
    },
    "search_web": {
      "total": 89,
      "success": 87,
      "avg_duration": 1.234
    }
  }
}
```

#### `POST /api/v1/tools/create/from-function`
Cria ferramenta dinamicamente a partir de código Python.

**Request:**
```json
{
  "name": "calculate_fibonacci",
  "description": "Calcula o n-ésimo número de Fibonacci",
  "code": "def execute(n: int) -> int:\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n + 1):\n        a, b = b, a + b\n    return b",
  "function_name": "execute",
  "category": "computation",
  "permission_level": "safe",
  "rate_limit_per_minute": 60,
  "tags": ["math", "fibonacci"]
}
```

⚠️ **Atenção:** Esta funcionalidade permite execução de código arbitrário. Use apenas em ambientes confiáveis.

#### `POST /api/v1/tools/create/from-api`
Cria ferramenta que chama endpoint HTTP.

**Request:**
```json
{
  "name": "get_github_user",
  "description": "Obtém informações de um usuário do GitHub",
  "endpoint_url": "https://api.github.com/users",
  "method": "GET",
  "headers": {
    "Accept": "application/vnd.github.v3+json"
  },
  "category": "api",
  "rate_limit_per_minute": 30
}
```

#### `DELETE /api/v1/tools/{tool_name}`
Remove uma ferramenta dinamicamente criada.

**Nota:** Ferramentas built-in são protegidas e não podem ser removidas.

#### `GET /api/v1/tools/categories/list`
Lista todas as categorias disponíveis.

#### `GET /api/v1/tools/permissions/list`
Lista todos os níveis de permissão.

### 4. **Métricas Prometheus**

O sistema expõe métricas detalhadas:

- `action_module_tool_calls_total{tool_name, category, outcome}`: Total de chamadas por ferramenta
- `action_module_tool_latency_seconds{tool_name, category}`: Latência de execução

### 5. **Rate Limiting Inteligente**

Cada ferramenta pode ter um limite de chamadas por minuto:

```python
action_registry.register(
    search_web,
    rate_limit_per_minute=20  # Máximo 20 chamadas/minuto
)

# Verifica antes de usar
if action_registry.check_rate_limit("search_web"):
    # Pode chamar
    result = search_web("consulta")
else:
    # Atingiu o limite, aguardar
    print("Rate limit atingido para search_web")
```

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Action Module                         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │            ActionRegistry (Singleton)              │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  Tool Registry                               │  │ │
│  │  │  - name -> BaseTool                          │  │ │
│  │  │  - name -> ToolMetadata                      │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  Rate Limiting                               │  │ │
│  │  │  - tool_name -> [timestamps]                 │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  Call History                                │  │ │
│  │  │  - [ToolCall...]                             │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         DynamicToolGenerator                       │ │
│  │  - from_function_spec()                            │ │
│  │  - from_api_endpoint()                             │ │
│  │  - from_python_code()                              │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │    Agent Manager       │
            │  (usa ferramentas)     │
            └────────────────────────┘
                         │
                         ▼
                  ┌────────────┐
                  │ Prometheus │
                  │ (métricas) │
                  └────────────┘
```

## 📊 Benefícios Implementados

### 1. **Extensibilidade**
- Adicionar novas ferramentas em runtime sem reiniciar o sistema
- Três métodos diferentes de criação de ferramentas
- Suporte a ferramentas customizadas e APIs externas

### 2. **Segurança**
- Controle granular de permissões
- Rate limiting por ferramenta
- Proteção de ferramentas built-in contra remoção
- Confirmação do usuário para operações perigosas

### 3. **Observabilidade**
- Telemetria completa com Prometheus
- Histórico de chamadas
- Estatísticas de uso e performance
- Rastreamento de erros

### 4. **Organização**
- Categorização clara por tipo de operação
- Sistema de tags para busca avançada
- Filtragem flexível

### 5. **Performance**
- Rate limiting evita sobrecarga
- Métricas para identificar gargalos
- Controle de recursos

## 🧪 Exemplos de Uso

### Exemplo 1: Criar Ferramenta de Cálculo

```python
from app.core.action_module import create_tool_from_function, ToolCategory

def calculate_compound_interest(
    principal: float,
    rate: float,
    time: int
) -> float:
    """Calcula juros compostos."""
    return principal * ((1 + rate / 100) ** time)

# Cria e registra
tool = create_tool_from_function(
    name="compound_interest",
    description="Calcula juros compostos: P * (1 + r)^t",
    func=calculate_compound_interest,
    category=ToolCategory.COMPUTATION,
    rate_limit_per_minute=100,
    tags=["finance", "math"]
)
```

### Exemplo 2: Integrar API Externa

```python
from app.core.action_module import DynamicToolGenerator, action_registry

tool = DynamicToolGenerator.from_api_endpoint(
    name="get_crypto_price",
    description="Obtém preço atual de criptomoeda",
    endpoint_url="https://api.coinbase.com/v2/prices/{currency}-USD/spot",
    method="GET"
)

action_registry.register(
    tool,
    category=ToolCategory.API,
    rate_limit_per_minute=10  # API gratuita tem limite
)
```

### Exemplo 3: Listar Ferramentas por Categoria

```python
from app.core.action_module import action_registry, ToolCategory

# Todas as ferramentas de filesystem
fs_tools = action_registry.list_tools(category=ToolCategory.FILESYSTEM)

for tool in fs_tools:
    metadata = action_registry.get_metadata(tool.name)
    print(f"- {metadata.name}: {metadata.description}")
    print(f"  Permissão: {metadata.permission_level.value}")
```

### Exemplo 4: Verificar Rate Limit

```python
from app.core.action_module import action_registry

tool_name = "search_web"

if action_registry.check_rate_limit(tool_name):
    result = search_web("Python asyncio")
    print(result)
else:
    print(f"Rate limit atingido para {tool_name}. Aguarde 1 minuto.")
```

### Exemplo 5: Estatísticas de Uso

```python
from app.core.action_module import action_registry

stats = action_registry.get_statistics()

print(f"Total de ferramentas: {stats['total_tools_registered']}")
print(f"Total de chamadas: {stats['total_calls']}")
print(f"Taxa de sucesso: {stats['success_rate']:.1%}")

print("\nTop 5 ferramentas mais usadas:")
sorted_tools = sorted(
    stats['tool_usage'].items(),
    key=lambda x: x[1]['total'],
    reverse=True
)[:5]

for tool_name, usage in sorted_tools:
    print(f"  {tool_name}: {usage['total']} chamadas, "
          f"{usage['avg_duration']:.3f}s média")
```

## 🔄 Integração com Outras Sprints

### Sprint 2 (Memória Episódica)
- Ferramentas de memória registradas e monitoradas
- Histórico de uso de ferramentas pode ser memorizado

### Sprint 3 (Contexto Ambiental)
- Ferramentas de busca web e contexto categorizadas como WEB
- Rate limiting para APIs externas

### Sprint 4 (Sandbox Python)
- Ferramentas de execução de código categorizadas como COMPUTATION
- Sandbox garante segurança mesmo com código dinâmico

### Sprint 5 (Reflexion)
- Ferramentas defeituosas marcadas com tags
- Sistema pode aprender quais ferramentas são confiáveis

## 📈 Métricas de Sucesso

**Indicadores:**

1. **Número de Ferramentas**: Total de ferramentas registradas
2. **Taxa de Uso**: Chamadas por ferramenta
3. **Success Rate**: % de chamadas bem-sucedidas
4. **Latência Média**: Tempo de execução por ferramenta
5. **Rate Limit Hits**: Quantas vezes o limite foi atingido

## 🚀 Próximos Passos (Futuro)

1. **Marketplace de Ferramentas**: Compartilhar ferramentas entre instâncias
2. **Versionamento**: Suportar múltiplas versões de uma ferramenta
3. **A/B Testing**: Testar diferentes implementações
4. **Auto-descoberta**: Detectar APIs automaticamente
5. **Ferramentas Colaborativas**: Múltiplos agentes usando ferramentas compartilhadas

## 📝 Checklist de Implementação

- [x] ActionRegistry completo com categorização e permissões
- [x] DynamicToolGenerator com 3 métodos de criação
- [x] Rate limiting por ferramenta
- [x] Sistema de tags e filtragem
- [x] Métricas Prometheus
- [x] Histórico de chamadas e telemetria
- [x] API REST completa (/list, /create, /delete, /stats)
- [x] Integração com ferramentas existentes
- [x] Proteção de ferramentas built-in
- [x] Documentação completa

## 🏆 Status: ✅ SPRINT 6 COMPLETA

A Sprint 6 implementa com sucesso o Action Module, transformando o Janus em um agente verdadeiramente multitarefa com capacidade de criar, gerenciar e monitorar ferramentas dinamicamente.

O sistema agora possui:
- **Gateway de Ferramentas** extensível e organizado
- **Criação Dinâmica** de ferramentas em runtime
- **Telemetria Completa** para observabilidade
- **Controle Fino** de permissões e rate limiting
- **API REST** para gerenciamento via HTTP
