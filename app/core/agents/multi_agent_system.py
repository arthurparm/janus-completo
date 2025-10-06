"""
Sistema de Colaboração Multi-Agente (Sprint 11).

Implementa uma "Sociedade de Mentes" onde múltiplos agentes especializados
trabalham em conjunto, coordenados por um Agente Gestor de Projetos.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from prometheus_client import Counter, Histogram, Gauge

from app.core.agent_tools import get_all_tools
from app.core.llm_manager import get_llm, ModelRole, ModelPriority

logger = logging.getLogger(__name__)

# --- Métricas ---
AGENT_TASKS_COUNTER = Counter(
    "multi_agent_tasks_total",
    "Total de tarefas executadas por agentes",
    ["agent_role", "status"]
)

AGENT_COLLABORATION_COUNTER = Counter(
    "multi_agent_collaborations_total",
    "Total de colaborações entre agentes",
    ["initiator", "collaborator"]
)

AGENT_TASK_DURATION = Histogram(
    "multi_agent_task_duration_seconds",
    "Duração de execução de tarefas por agente",
    ["agent_role"]
)

ACTIVE_AGENTS_GAUGE = Gauge(
    "multi_agent_active_agents",
    "Número de agentes ativos no sistema"
)


# --- Enums ---

class AgentRole(Enum):
    """Papéis especializados de agentes."""
    PROJECT_MANAGER = "project_manager"  # Coordenador geral
    RESEARCHER = "researcher"  # Pesquisa e análise
    CODER = "coder"  # Geração de código
    TESTER = "tester"  # Testes e validação
    DOCUMENTER = "documenter"  # Documentação
    OPTIMIZER = "optimizer"  # Otimização e refatoração


class TaskStatus(Enum):
    """Status de uma tarefa."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Prioridade de uma tarefa."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# --- Modelos de Dados ---

@dataclass
class Task:
    """Representa uma tarefa no sistema multi-agente."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    assigned_to: Optional[str] = None  # Agent ID
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class SharedWorkspace:
    """Espaço de trabalho compartilhado entre agentes."""
    artifacts: Dict[str, Any] = field(default_factory=dict)  # Arquivos, dados, resultados
    messages: List[Dict[str, Any]] = field(default_factory=list)  # Mensagens entre agentes
    tasks: Dict[str, Task] = field(default_factory=dict)  # Tarefas do projeto

    def add_artifact(self, key: str, value: Any, author: str):
        """Adiciona um artefato ao workspace."""
        self.artifacts[key] = {
            "value": value,
            "author": author,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"Artefato '{key}' adicionado ao workspace por {author}")

    def get_artifact(self, key: str) -> Optional[Any]:
        """Recupera um artefato do workspace."""
        artifact = self.artifacts.get(key)
        return artifact["value"] if artifact else None

    def send_message(self, from_agent: str, to_agent: str, content: str):
        """Envia uma mensagem entre agentes."""
        message = {
            "id": str(uuid.uuid4()),
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message)
        AGENT_COLLABORATION_COUNTER.labels(initiator=from_agent, collaborator=to_agent).inc()
        logger.info(f"Mensagem enviada: {from_agent} → {to_agent}")

    def get_messages_for(self, agent_id: str) -> List[Dict[str, Any]]:
        """Recupera mensagens destinadas a um agente."""
        return [msg for msg in self.messages if msg["to"] == agent_id]

    def add_task(self, task: Task):
        """Adiciona uma tarefa ao workspace."""
        self.tasks[task.id] = task
        logger.info(f"Tarefa '{task.id}' adicionada: {task.description}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """Recupera uma tarefa pelo ID."""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Recupera tarefas por status."""
        return [task for task in self.tasks.values() if task.status == status]

    def get_tasks_by_agent(self, agent_id: str) -> List[Task]:
        """Recupera tarefas atribuídas a um agente."""
        return [task for task in self.tasks.values() if task.assigned_to == agent_id]


# --- Agente Especializado ---

class SpecializedAgent:
    """Agente especializado com papel específico."""

    def __init__(
            self,
            role: AgentRole,
            workspace: SharedWorkspace,
            agent_id: Optional[str] = None
    ):
        self.role = role
        self.agent_id = agent_id or f"{role.value}_{uuid.uuid4().hex[:8]}"
        self.workspace = workspace
        self.executor: Optional[AgentExecutor] = None
        self._initialize_agent()
        ACTIVE_AGENTS_GAUGE.inc()
        logger.info(f"Agente '{self.agent_id}' ({role.value}) inicializado")

    def _initialize_agent(self):
        """Inicializa o executor do agente com prompt especializado."""
        prompts = {
            AgentRole.PROJECT_MANAGER: """Você é um Gerente de Projetos especializado em coordenar equipes de agentes.

Suas responsabilidades:
- Analisar requisitos e dividir projetos em tarefas menores
- Atribuir tarefas aos agentes especializados apropriados
- Monitorar o progresso e identificar bloqueios
- Facilitar a comunicação entre agentes
- Garantir a qualidade e completude do trabalho

Você tem acesso a ferramentas para: {tools}

Use este formato:
Question: a pergunta ou solicitação
Thought: pense sobre o que fazer
Action: a ação a tomar, deve ser uma de [{tool_names}]
Action Input: o input para a ação
Observation: o resultado da ação
... (repita Thought/Action/Action Input/Observation conforme necessário)
Thought: Eu sei a resposta final
Final Answer: a resposta final

Question: {input}
{agent_scratchpad}""",

            AgentRole.RESEARCHER: """Você é um Agente de Pesquisa especializado em análise e investigação.

Suas responsabilidades:
- Buscar informações relevantes (web, documentação, memória)
- Analisar e sintetizar dados
- Identificar padrões e insights
- Fornecer relatórios estruturados

Ferramentas disponíveis: {tools}

Use este formato:
Question: {input}
Thought: [seu raciocínio]
Action: [{tool_names}]
Action Input: [input]
Observation: [resultado]
...
Final Answer: [resposta]
{agent_scratchpad}""",

            AgentRole.CODER: """Você é um Agente Desenvolvedor especializado em escrever código de alta qualidade.

Suas responsabilidades:
- Implementar funcionalidades conforme especificado
- Escrever código limpo e bem documentado
- Seguir best practices e padrões
- Usar o sandbox Python para execução segura

Ferramentas: {tools}

Formato:
Question: {input}
Thought: [raciocínio]
Action: [{tool_names}]
Action Input: [input]
Observation: [resultado]
...
Final Answer: [código/resultado]
{agent_scratchpad}""",

            AgentRole.TESTER: """Você é um Agente de Testes especializado em validação e qualidade.

Suas responsabilidades:
- Criar casos de teste
- Executar testes e validações
- Identificar bugs e problemas
- Reportar resultados detalhadamente

Ferramentas: {tools}
Formato: Question: {input}, Thought, Action [{tool_names}], Action Input, Observation, ..., Final Answer
{agent_scratchpad}""",

            AgentRole.DOCUMENTER: """Você é um Agente Documentador especializado em criar documentação clara.

Suas responsabilidades:
- Escrever documentação técnica
- Criar guias e tutoriais
- Documentar APIs e código
- Manter documentação atualizada

Ferramentas: {tools}
Formato: Question: {input}, Thought, Action [{tool_names}], Action Input, Observation, ..., Final Answer
{agent_scratchpad}""",

            AgentRole.OPTIMIZER: """Você é um Agente Otimizador especializado em melhorar performance e qualidade.

Suas responsabilidades:
- Analisar código para otimizações
- Identificar gargalos de performance
- Sugerir refatorações
- Aplicar best practices

Ferramentas: {tools}
Formato: Question: {input}, Thought, Action [{tool_names}], Action Input, Observation, ..., Final Answer
{agent_scratchpad}"""
        }

        prompt_text = prompts.get(self.role, prompts[AgentRole.PROJECT_MANAGER])
        prompt = PromptTemplate.from_template(prompt_text)

        # Selecionar LLM baseado no papel
        llm_mapping = {
            AgentRole.PROJECT_MANAGER: (ModelRole.ORCHESTRATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.CODER: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.RESEARCHER: (ModelRole.ORCHESTRATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.TESTER: (ModelRole.CODE_GENERATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.DOCUMENTER: (ModelRole.KNOWLEDGE_CURATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.OPTIMIZER: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
        }

        llm_role, llm_priority = llm_mapping.get(self.role, (ModelRole.ORCHESTRATOR, ModelPriority.LOCAL_ONLY))
        llm = get_llm(role=llm_role, priority=llm_priority)

        tools = get_all_tools()
        agent = create_react_agent(llm, tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """Executa uma tarefa atribuída ao agente."""
        if task.status != TaskStatus.PENDING:
            raise ValueError(f"Tarefa {task.id} não está em estado PENDING")

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        task.assigned_to = self.agent_id

        logger.info(f"Agente {self.agent_id} iniciando tarefa: {task.description}")

        try:
            # Executar a tarefa
            start_time = asyncio.get_event_loop().time()
            result = await asyncio.to_thread(
                self.executor.invoke,
                {"input": task.description}
            )
            duration = asyncio.get_event_loop().time() - start_time

            # Atualizar task
            task.status = TaskStatus.COMPLETED
            task.result = result.get("output", "")
            task.completed_at = datetime.now()

            # Métricas
            AGENT_TASKS_COUNTER.labels(agent_role=self.role.value, status="completed").inc()
            AGENT_TASK_DURATION.labels(agent_role=self.role.value).observe(duration)

            logger.info(f"Tarefa {task.id} concluída com sucesso")

            return {
                "task_id": task.id,
                "status": "completed",
                "result": task.result,
                "duration_seconds": duration
            }

        except Exception as e:
            logger.error(f"Erro ao executar tarefa {task.id}: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            AGENT_TASKS_COUNTER.labels(agent_role=self.role.value, status="failed").inc()

            return {
                "task_id": task.id,
                "status": "failed",
                "error": str(e)
            }

    def communicate(self, to_agent_id: str, message: str):
        """Envia uma mensagem para outro agente."""
        self.workspace.send_message(self.agent_id, to_agent_id, message)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Recupera mensagens destinadas a este agente."""
        return self.workspace.get_messages_for(self.agent_id)

    def shutdown(self):
        """Desliga o agente."""
        ACTIVE_AGENTS_GAUGE.dec()
        logger.info(f"Agente {self.agent_id} desligado")


# --- Sistema Multi-Agente ---

class MultiAgentSystem:
    """Sistema coordenado de múltiplos agentes."""

    def __init__(self):
        self.workspace = SharedWorkspace()
        self.agents: Dict[str, SpecializedAgent] = {}
        self.project_manager: Optional[SpecializedAgent] = None
        logger.info("Sistema Multi-Agente inicializado")

    def create_agent(self, role: AgentRole) -> SpecializedAgent:
        """Cria um novo agente especializado."""
        agent = SpecializedAgent(role, self.workspace)
        self.agents[agent.agent_id] = agent

        if role == AgentRole.PROJECT_MANAGER and not self.project_manager:
            self.project_manager = agent

        return agent

    def get_agent(self, agent_id: str) -> Optional[SpecializedAgent]:
        """Recupera um agente pelo ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos os agentes ativos."""
        return [
            {
                "agent_id": agent.agent_id,
                "role": agent.role.value,
                "tasks_assigned": len(self.workspace.get_tasks_by_agent(agent.agent_id))
            }
            for agent in self.agents.values()
        ]

    async def execute_project(self, project_description: str) -> Dict[str, Any]:
        """
        Executa um projeto completo usando coordenação multi-agente.

        O Gestor de Projetos analisa o requisito, divide em tarefas,
        atribui aos agentes especializados e coordena a execução.
        """
        if not self.project_manager:
            self.project_manager = self.create_agent(AgentRole.PROJECT_MANAGER)

        logger.info(f"Iniciando projeto: {project_description}")

        # 1. PM analisa e decompõe o projeto
        decomposition_prompt = f"""Analise este projeto e decomponha em tarefas específicas:

Projeto: {project_description}

Para cada tarefa, especifique:
1. Descrição clara da tarefa
2. Agente mais adequado (researcher/coder/tester/documenter/optimizer)
3. Prioridade (low/medium/high/critical)
4. Dependências (se houver)

Retorne em formato estruturado."""

        pm_task = Task(
            description=decomposition_prompt,
            assigned_to=self.project_manager.agent_id,
            priority=TaskPriority.CRITICAL
        )
        self.workspace.add_task(pm_task)

        pm_result = await self.project_manager.execute_task(pm_task)

        # 2. Criar agentes necessários e distribuir tarefas
        # (Simplificado - em produção, parsear resultado do PM)
        tasks_created = []
        subtask = Task(
            description=f"Executar parte do projeto: {project_description}",
            priority=TaskPriority.HIGH
        )
        self.workspace.add_task(subtask)
        tasks_created.append(subtask.id)

        # 3. Atribuir e executar tarefas
        results = []
        for task_id in tasks_created:
            task = self.workspace.get_task(task_id)
            if task:
                # Selecionar agente apropriado (simplificado)
                agent = self.project_manager
                result = await agent.execute_task(task)
                results.append(result)

        return {
            "project_description": project_description,
            "total_tasks": len(tasks_created),
            "pm_analysis": pm_result,
            "task_results": results,
            "workspace_artifacts": list(self.workspace.artifacts.keys()),
            "messages_exchanged": len(self.workspace.messages)
        }

    def get_workspace_status(self) -> Dict[str, Any]:
        """Retorna status do workspace compartilhado."""
        return {
            "total_artifacts": len(self.workspace.artifacts),
            "total_messages": len(self.workspace.messages),
            "total_tasks": len(self.workspace.tasks),
            "tasks_by_status": {
                status.value: len(self.workspace.get_tasks_by_status(status))
                for status in TaskStatus
            }
        }

    def shutdown_all(self):
        """Desliga todos os agentes."""
        for agent in self.agents.values():
            agent.shutdown()
        self.agents.clear()
        self.project_manager = None
        logger.info("Todos os agentes foram desligados")


# --- Instância Global ---
_multi_agent_system: Optional[MultiAgentSystem] = None


def get_multi_agent_system() -> MultiAgentSystem:
    """Obtém a instância global do sistema multi-agente."""
    global _multi_agent_system
    if _multi_agent_system is None:
        _multi_agent_system = MultiAgentSystem()
    return _multi_agent_system
