# Sprint 11: Colaboração Agêntica - Sociedade de Mentes

## 📋 Visão Geral

A Sprint 11 transforma o Janus de um sistema single-agent para uma **"Sociedade de Mentes"**, onde múltiplos agentes
especializados trabalham colaborativamente, coordenados por um **Agente Gestor de Projetos**, compartilhando informações
através de um **Workspace comum**.

---

## 🎯 Objetivos

1. **Sistema Multi-Agente**: Múltiplos agentes especializados trabalhando simultaneamente
2. **Agente Gestor de Projetos**: Coordenador que decompõe projetos e delega tarefas
3. **Workspace Compartilhado**: Espaço para troca de artefatos, mensagens e tarefas
4. **Fluxos Colaborativos**: Agentes se comunicam e compartilham resultados
5. **Especialização por Papel**: Cada agente tem expertise específica

---

## 🏗️ Arquitetura

### Visão Geral do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│            Sistema Multi-Agente (MultiAgentSystem)          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         Agente Gestor de Projetos (PM)                │  │
│  │  - Analisa requisitos                                 │  │
│  │  - Decompõe em tarefas                                │  │
│  │  - Delega para agentes especializados                 │  │
│  │  - Monitora progresso                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Workspace Compartilhado                      │  │
│  │  - Tarefas (Task Queue)                               │  │
│  │  - Artefatos (Arquivos, Dados)                        │  │
│  │  - Mensagens (Inter-agent Communication)              │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓                                 │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │Researcher│  Coder   │  Tester  │Documenter│Optimizer │   │
│  │  Agent   │  Agent   │  Agent   │  Agent   │  Agent   │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Fluxo de Execução de Projeto

```
1. Usuário → [POST /collaboration/projects/execute]
                      ↓
2. Sistema cria/usa Gestor de Projetos
                      ↓
3. PM analisa e decompõe projeto em tarefas
   - Tarefa 1: Pesquisar tecnologias (→ Researcher)
   - Tarefa 2: Implementar código (→ Coder)
   - Tarefa 3: Testar solução (→ Tester)
   - Tarefa 4: Documentar (→ Documenter)
                      ↓
4. PM cria agentes necessários e atribui tarefas
                      ↓
5. Agentes executam tarefas em paralelo/sequencial
   - Comunicam entre si via mensagens
   - Compartilham artefatos no workspace
                      ↓
6. PM agrega resultados e retorna ao usuário
```

---

## 🔧 Implementação

### 1. Papéis de Agentes (`AgentRole`)

```python
class AgentRole(Enum):
    PROJECT_MANAGER = "project_manager"  # Coordenador geral
    RESEARCHER = "researcher"  # Pesquisa e análise
    CODER = "coder"  # Geração de código
    TESTER = "tester"  # Testes e validação
    DOCUMENTER = "documenter"  # Documentação
    OPTIMIZER = "optimizer"  # Otimização e refatoração
```

#### **Características de Cada Papel:**

| Papel               | LLM               | Prioridade     | Responsabilidades                                  |
|---------------------|-------------------|----------------|----------------------------------------------------|
| **Project Manager** | ORCHESTRATOR      | HIGH_QUALITY   | Análise, decomposição, coordenação, monitoramento  |
| **Researcher**      | ORCHESTRATOR      | FAST_AND_CHEAP | Busca web, análise de docs, síntese de informações |
| **Coder**           | CODE_GENERATOR    | HIGH_QUALITY   | Implementação, código limpo, best practices        |
| **Tester**          | CODE_GENERATOR    | FAST_AND_CHEAP | Testes, validação, identificação de bugs           |
| **Documenter**      | KNOWLEDGE_CURATOR | FAST_AND_CHEAP | Docs técnicas, guias, API docs                     |
| **Optimizer**       | CODE_GENERATOR    | HIGH_QUALITY   | Refatoração, performance, otimizações              |

### 2. Workspace Compartilhado (`SharedWorkspace`)

```python
@dataclass
class SharedWorkspace:
    artifacts: Dict[str, Any]  # Artefatos compartilhados
    messages: List[Dict[str, Any]]  # Mensagens entre agentes
    tasks: Dict[str, Task]  # Tarefas do projeto
```

#### **Funcionalidades:**

**Artefatos:**

```python
# Adicionar artefato
workspace.add_artifact(
    key="implementation_v1.py",
    value="def factorial(n): ...",
    author="coder_abc123"
)

# Recuperar artefato
code = workspace.get_artifact("implementation_v1.py")
```

**Mensagens:**

```python
# Enviar mensagem
workspace.send_message(
    from_agent="coder_abc123",
    to_agent="tester_def456",
    content="Código pronto para testes em implementation_v1.py"
)

# Ler mensagens
messages = workspace.get_messages_for("tester_def456")
```

**Tarefas:**

```python
# Criar tarefa
task = Task(
    description="Implementar função de fatorial recursivo",
    priority=TaskPriority.HIGH,
    assigned_to="coder_abc123"
)
workspace.add_task(task)

# Buscar tarefas
pending_tasks = workspace.get_tasks_by_status(TaskStatus.PENDING)
my_tasks = workspace.get_tasks_by_agent("coder_abc123")
```

### 3. Modelo de Tarefa (`Task`)

```python
@dataclass
class Task:
    id: str  # UUID único
    description: str  # O que fazer
    assigned_to: Optional[str]  # Agent ID
    status: TaskStatus  # PENDING/IN_PROGRESS/COMPLETED/FAILED
    priority: TaskPriority  # LOW/MEDIUM/HIGH/CRITICAL
    dependencies: List[str]  # Task IDs dependentes
    result: Optional[str]  # Resultado da execução
    error: Optional[str]  # Erro (se falhou)
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]
```

### 4. Agente Especializado (`SpecializedAgent`)

```python
class SpecializedAgent:
    def __init__(self, role: AgentRole, workspace: SharedWorkspace):
        self.role = role
        self.agent_id = f"{role.value}_{uuid4()}"
        self.workspace = workspace
        self.executor = AgentExecutor(...)  # LangChain agent

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Executa uma tarefa com observabilidade completa."""
        # 1. Atualiza status para IN_PROGRESS
        # 2. Invoca AgentExecutor com prompt especializado
        # 3. Registra métricas (duração, sucesso/falha)
        # 4. Atualiza task com resultado
        # 5. Retorna resultado estruturado

    def communicate(self, to_agent_id: str, message: str):
        """Envia mensagem para outro agente."""
        self.workspace.send_message(self.agent_id, to_agent_id, message)
```

### 5. Sistema Multi-Agente (`MultiAgentSystem`)

```python
class MultiAgentSystem:
    def __init__(self):
        self.workspace = SharedWorkspace()
        self.agents: Dict[str, SpecializedAgent] = {}
        self.project_manager: Optional[SpecializedAgent] = None

    def create_agent(self, role: AgentRole) -> SpecializedAgent:
        """Cria um novo agente especializado."""

    async def execute_project(self, description: str) -> Dict[str, Any]:
        """
        Executa projeto completo com coordenação multi-agente:
        1. PM analisa e decompõe
        2. PM cria agentes necessários
        3. PM atribui tarefas
        4. Agentes executam colaborativamente
        5. PM agrega e retorna resultados
        """
```

---

## 🌐 API Endpoints

### **Gerenciamento de Agentes**

#### 1. `POST /api/v1/collaboration/agents/create`

Cria um novo agente especializado.

**Request:**

```json
{
  "role": "coder"
}
```

**Response:**

```json
{
  "agent_id": "coder_a1b2c3d4",
  "role": "coder",
  "message": "Agente coder criado com sucesso"
}
```

#### 2. `GET /api/v1/collaboration/agents`

Lista todos os agentes ativos.

**Response:**

```json
{
  "total_agents": 5,
  "agents": [
    {
      "agent_id": "project_manager_xyz",
      "role": "project_manager",
      "tasks_assigned": 3
    },
    {
      "agent_id": "coder_abc",
      "role": "coder",
      "tasks_assigned": 1
    }
  ]
}
```

#### 3. `GET /api/v1/collaboration/agents/{agent_id}`

Detalhes de um agente específico.

---

### **Gerenciamento de Tarefas**

#### 4. `POST /api/v1/collaboration/tasks/create`

Cria uma nova tarefa.

**Request:**

```json
{
  "description": "Implementar função de fibonacci",
  "assigned_to": "coder_abc",
  "priority": "high",
  "dependencies": []
}
```

#### 5. `POST /api/v1/collaboration/tasks/execute`

Executa uma tarefa usando um agente.

**Request:**

```json
{
  "task_id": "task-uuid-123",
  "agent_id": "coder_abc"
}
```

**Response:**

```json
{
  "task_id": "task-uuid-123",
  "status": "completed",
  "result": "Função implementada com sucesso...",
  "duration_seconds": 12.5
}
```

#### 6. `GET /api/v1/collaboration/tasks`

Lista tarefas (opcionalmente filtradas por status).

#### 7. `GET /api/v1/collaboration/tasks/{task_id}`

Detalhes de uma tarefa específica.

---

### **Execução de Projetos**

#### 8. `POST /api/v1/collaboration/projects/execute` ⭐

**Endpoint principal** - Executa projeto completo com coordenação multi-agente.

**Request:**

```json
{
  "description": "Criar uma API REST para gerenciar usuários com CRUD completo, incluindo testes e documentação"
}
```

**Response:**

```json
{
  "project_description": "Criar uma API REST...",
  "total_tasks": 4,
  "pm_analysis": {
    "task_id": "...",
    "status": "completed",
    "result": "Projeto decomposto em 4 tarefas..."
  },
  "task_results": [
    {
      "task_id": "task-1",
      "status": "completed",
      "result": "..."
    }
  ],
  "workspace_artifacts": [
    "api_spec.yaml",
    "implementation.py",
    "tests.py"
  ],
  "messages_exchanged": 12
}
```

---

### **Workspace Compartilhado**

#### 9. `POST /api/v1/collaboration/workspace/messages/send`

Envia mensagem entre agentes.

**Request:**

```json
{
  "from_agent": "coder_abc",
  "to_agent": "tester_xyz",
  "content": "Código pronto para testes"
}
```

#### 10. `GET /api/v1/collaboration/workspace/messages/{agent_id}`

Recupera mensagens de um agente.

#### 11. `POST /api/v1/collaboration/workspace/artifacts/add`

Adiciona artefato ao workspace.

**Request:**

```json
{
  "key": "implementation.py",
  "value": "def main(): ...",
  "author": "coder_abc"
}
```

#### 12. `GET /api/v1/collaboration/workspace/artifacts/{key}`

Recupera um artefato.

#### 13. `GET /api/v1/collaboration/workspace/status`

Status geral do workspace.

**Response:**

```json
{
  "total_artifacts": 5,
  "total_messages": 12,
  "total_tasks": 8,
  "tasks_by_status": {
    "pending": 2,
    "in_progress": 1,
    "completed": 5,
    "failed": 0,
    "blocked": 0
  }
}
```

---

### **Sistema**

#### 14. `POST /api/v1/collaboration/system/shutdown`

Desliga todos os agentes.

#### 15. `GET /api/v1/collaboration/health`

Health check do sistema.

---

## 📊 Métricas Prometheus

```python
# Total de tarefas por agente e status
AGENT_TASKS_COUNTER = Counter(
    "multi_agent_tasks_total",
    ["agent_role", "status"]  # status: completed/failed
)

# Colaborações entre agentes
AGENT_COLLABORATION_COUNTER = Counter(
    "multi_agent_collaborations_total",
    ["initiator", "collaborator"]
)

# Duração de tarefas
AGENT_TASK_DURATION = Histogram(
    "multi_agent_task_duration_seconds",
    ["agent_role"]
)

# Agentes ativos
ACTIVE_AGENTS_GAUGE = Gauge(
    "multi_agent_active_agents"
)
```

---

## 🎓 Casos de Uso

### Caso 1: Desenvolvimento Completo de Feature

**Input:**

```
"Implementar autenticação JWT com registro de usuários,
login, refresh token, incluindo testes e documentação"
```

**Fluxo:**

1. **PM** analisa e decompõe:
    - Tarefa 1 (Researcher): "Pesquisar best practices de JWT"
    - Tarefa 2 (Coder): "Implementar endpoints de auth"
    - Tarefa 3 (Tester): "Criar testes unitários e integração"
    - Tarefa 4 (Documenter): "Documentar API de autenticação"

2. **PM** cria agentes e atribui tarefas

3. **Researcher** executa:
    - Busca na web sobre JWT
    - Adiciona artefato: `jwt_research.md`
    - Envia mensagem ao Coder

4. **Coder** executa:
    - Lê `jwt_research.md`
    - Implementa código
    - Adiciona artefato: `auth.py`
    - Envia mensagem ao Tester

5. **Tester** executa:
    - Lê `auth.py`
    - Cria testes
    - Adiciona artefato: `test_auth.py`
    - Reporta bugs ao Coder (se houver)

6. **Documenter** executa:
    - Lê `auth.py`
    - Cria documentação
    - Adiciona artefato: `auth_api_docs.md`

7. **PM** agrega resultados e retorna ao usuário

### Caso 2: Otimização de Código Existente

**Input:**

```
"Otimizar a função de busca no arquivo search.py,
criar benchmarks e documentar as melhorias"
```

**Fluxo:**

1. PM → Researcher: "Analisar gargalos de performance"
2. PM → Optimizer: "Aplicar otimizações"
3. PM → Tester: "Criar benchmarks"
4. PM → Documenter: "Documentar mudanças"

---

## ⚙️ Configuração

Não requer configuração adicional além das dependências existentes:

- LangChain (agentes)
- LLM Manager (Sprint 10)
- Agent Tools (ferramentas disponíveis)

---

## 🧪 Testes

### Teste de Criação de Agentes

```bash
curl -X POST http://localhost:8000/api/v1/collaboration/agents/create \
  -H "Content-Type: application/json" \
  -d '{"role": "coder"}'
```

### Teste de Execução de Projeto

```bash
curl -X POST http://localhost:8000/api/v1/collaboration/projects/execute \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Criar função para calcular números primos até N"
  }'
```

---

## 🔄 Comparação: Single vs Multi-Agent

| Aspecto            | Single-Agent (Sprints 1-10)        | Multi-Agent (Sprint 11)          |
|--------------------|------------------------------------|----------------------------------|
| **Abordagem**      | Um agente faz tudo sequencialmente | Múltiplos agentes especializados |
| **Paralelização**  | Não (uma tarefa por vez)           | Sim (tarefas independentes)      |
| **Especialização** | Generalista                        | Especialistas por domínio        |
| **Coordenação**    | Não necessária                     | PM coordena equipe               |
| **Comunicação**    | N/A                                | Mensagens inter-agent            |
| **Workspace**      | Local                              | Compartilhado                    |
| **Complexidade**   | Baixa                              | Alta                             |
| **Adequado para**  | Tarefas simples/lineares           | Projetos complexos               |

---

## 🚀 Próximos Passos

1. **Sprint 12**: Resiliência e observabilidade avançada (Grafana dashboards)
2. **Sprint 13**: Meta-Agente de Auto-Otimização (consciência proativa)
3. **Melhorias Futuras**:
    - Execução paralela real de tarefas independentes
    - Resolução automática de dependências entre tarefas
    - Negociação entre agentes (quando há conflitos)
    - Aprendizado colaborativo (agentes aprendem uns com os outros)

---

## 📚 Referências

- **Multi-Agent Systems**: Paradigma de IA distribuída
- **Society of Mind**: Marvin Minsky (múltiplas mentes especializadas)
- **LangChain Multi-Agent**: Framework de coordenação
- **ReAct Pattern**: Raciocínio e ação iterativa

---

## ✅ Critérios de Aceitação

- [x] Sistema suporta criação de agentes especializados
- [x] Agente Gestor de Projetos coordena outros agentes
- [x] Workspace compartilhado funciona (artefatos, mensagens, tarefas)
- [x] Agentes se comunicam entre si
- [x] Fluxo de projeto completo (análise → decomposição → execução)
- [x] Métricas Prometheus registram atividades
- [x] API endpoints permitem controle completo
- [x] Documentação completa
- [x] Testes HTTP funcionais
