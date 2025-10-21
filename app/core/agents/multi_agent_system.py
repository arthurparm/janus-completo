"""
Sistema de Colaboração Multi-Agente (Sprint 11).

Implementa uma "Sociedade de Mentes" onde múltiplos agentes especializados
trabalham em conjunto, coordenados por um Agente Gestor de Projetos.
"""
import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from langchain.agents import AgentExecutor, create_react_agent
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.prompts import PromptTemplate
from prometheus_client import Counter, Histogram, Gauge

from app.core.llm.llm_manager import get_llm, ModelRole, ModelPriority
from app.core.tools import get_all_tools
from app.repositories.agent_config_repository import AgentConfigRepository
from app.core.infrastructure.prompt_loader import get_prompt_advanced

logger = logging.getLogger(__name__)


def _clean_json_output(text: str) -> str:
    """
    Remove markdown code blocks e limpa o output para parsing JSON.

    Args:
        text: Texto que pode conter JSON envolto em markdown

    Returns:
        JSON limpo sem markdown
    """
    if not text:
        return text

    # Remove markdown code blocks (```json ... ``` ou ``` ... ```)
    text = re.sub(r'^```(?:json)?\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    return text


def _create_tool_wrapper(tool):
    """
    Cria um wrapper para ferramentas que trata o input corretamente.

    O LangChain às vezes passa o JSON inteiro como string no primeiro parâmetro.
    Este wrapper detecta isso e faz o parse correto, suportando sync e async.
    """
    from functools import wraps
    from langchain.tools import BaseTool, StructuredTool
    import inspect

    logger.info(f"[WRAPPER INIT] Criando wrapper para {tool.name} - type={type(tool)}")

    # Detecta qual método usar
    if hasattr(tool, 'func') and callable(tool.func):
        original_func = tool.func
        logger.info(f"[WRAPPER INIT] {tool.name} - Usando tool.func")
    elif hasattr(tool, '_run') and callable(tool._run):
        original_func = tool._run
        logger.info(f"[WRAPPER INIT] {tool.name} - Usando tool._run")
    else:
        logger.warning(f"[WRAPPER INIT] {tool.name} - Nenhum método encontrado, retornando original")
        return tool

    is_async = inspect.iscoroutinefunction(original_func)

    if is_async:
        @wraps(original_func)
        async def async_wrapper(*args, **kwargs):
            tool_name = getattr(tool, 'name', 'unknown')
            logger.debug(f"[WRAPPER ASYNC] {tool_name} - args={args}, kwargs={kwargs}")

            # Se recebeu apenas 1 argumento e ele parece ser um JSON string
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
                arg = args[0]
                logger.debug(f"[WRAPPER] {tool_name} - Argumento string recebido: {arg[:150]}")

                try:
                    # Limpa o argumento de forma agressiva
                    cleaned = arg.strip()

                    # Remove markdown code fences (```json, ```, etc)
                    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                    cleaned = re.sub(r'\s*```$', '', cleaned)
                    cleaned = cleaned.strip()

                    # Remove quebras de linha e espaços extras dentro do JSON
                    # (mas preserva \n dentro de strings)
                    if cleaned.startswith('{') and cleaned.endswith('}'):
                        logger.debug(f"[WRAPPER] {tool_name} - JSON detectado após limpeza: {cleaned[:150]}")
                        parsed = json.loads(cleaned)

                        if isinstance(parsed, dict):
                            logger.info(f"[WRAPPER] {tool_name} - ✅ JSON parseado: {list(parsed.keys())}")
                            # Chama a função com os parâmetros corretos
                            return await original_func(**parsed)

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[WRAPPER] {tool_name} - ❌ Falha ao parsear: {e}")
                    logger.debug(f"[WRAPPER] {tool_name} - String que falhou: {arg[:200]}")

            # Se não conseguiu fazer parse ou não era JSON, chama normalmente
            return await original_func(*args, **kwargs)

        # Substitui AMBOS func e _run
        if hasattr(tool, 'func'):
            tool.func = async_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool.func substituído (async)")
        if hasattr(tool, '_run'):
            tool._run = async_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool._run substituído (async)")

    else:
        @wraps(original_func)
        def sync_wrapper(*args, **kwargs):
            tool_name = getattr(tool, 'name', 'unknown')
            logger.debug(f"[WRAPPER SYNC] {tool_name} - args={args}, kwargs={kwargs}")

            # Se recebeu apenas 1 argumento e ele parece ser um JSON string
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], str):
                arg = args[0]
                logger.debug(f"[WRAPPER] {tool_name} - Argumento string recebido: {arg[:150]}")

                try:
                    # Limpa o argumento de forma agressiva
                    cleaned = arg.strip()

                    # Remove markdown code fences (```json, ```, etc)
                    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                    cleaned = re.sub(r'\s*```$', '', cleaned)
                    cleaned = cleaned.strip()

                    # Remove quebras de linha e espaços extras dentro do JSON
                    # (mas preserva \n dentro de strings)
                    if cleaned.startswith('{') and cleaned.endswith('}'):
                        logger.debug(f"[WRAPPER] {tool_name} - JSON detectado após limpeza: {cleaned[:150]}")
                        parsed = json.loads(cleaned)

                        if isinstance(parsed, dict):
                            logger.info(f"[WRAPPER] {tool_name} - ✅ JSON parseado: {list(parsed.keys())}")
                            # Chama a função com os parâmetros corretos
                            return original_func(**parsed)

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"[WRAPPER] {tool_name} - ❌ Falha ao parsear: {e}")
                    logger.debug(f"[WRAPPER] {tool_name} - String que falhou: {arg[:200]}")

            # Se não conseguiu fazer parse ou não era JSON, chama normalmente
            return original_func(*args, **kwargs)

        # Substitui AMBOS func e _run
        if hasattr(tool, 'func'):
            tool.func = sync_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool.func substituído (sync)")
        if hasattr(tool, '_run'):
            tool._run = sync_wrapper
            logger.info(f"[WRAPPER INIT] {tool.name} - tool._run substituído (sync)")

    return tool

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

    def get_ready_tasks(self) -> List[Task]:
        """Retorna tarefas PENDING cujas dependências já estão COMPLETED.

        Tarefas com dependências inexistentes ou falhas não são consideradas prontas.
        """
        ready: List[Task] = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps = task.dependencies or []
            if not deps:
                ready.append(task)
                continue
            all_ok = True
            for dep_id in deps:
                dep = self.tasks.get(dep_id)
                if dep is None:
                    all_ok = False
                    break
                if dep.status != TaskStatus.COMPLETED:
                    all_ok = False
                    break
            if all_ok:
                ready.append(task)
        return ready


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
        self.config_repo = AgentConfigRepository()
        self._initialize_agent()
        ACTIVE_AGENTS_GAUGE.inc()
        logger.info(f"Agente '{self.agent_id}' ({role.value}) inicializado")

    def _get_prompt_for_role(self, config) -> str:
        """Obtém o prompt para o papel do agente (do banco ou fallback)."""
        if config and config.prompt_template:
            return config.prompt_template

        # Fallback para prompts padrão
        prompts = {
            AgentRole.PROJECT_MANAGER: """Você é um Gerente de Projetos especializado em coordenar equipes de agentes.

Suas responsabilidades:
- Analisar requisitos e dividir projetos em tarefas menores e específicas
- Atribuir tarefas aos agentes especializados apropriados
- Monitorar o progresso e identificar bloqueios
- Facilitar a comunicação entre agentes
- Garantir a qualidade e completude do trabalho

IMPORTANTE: Ao usar ferramentas:
- Para list_directory: Use path="/app/workspace"
- Para write_file: Forneça file_path, content, overwrite

Ferramentas disponíveis: {tools}
Nomes das ferramentas: {tool_names}

==== FORMATO OBRIGATÓRIO (SIGA EXATAMENTE) ====
VOCÊ DEVE SEMPRE USAR ESTE FORMATO:

Thought: [seu raciocínio sobre o que fazer]
Action: [nome_da_ferramenta - deve ser UMA de {tool_names}]
Action Input: {{"parametro": "valor"}}

... aguarde a Observation ...

Observation: [resultado da ferramenta]
Thought: [continue raciocinando ou conclua]
... repita Thought/Action/Observation quantas vezes necessário ...

Thought: Eu sei a resposta final
Final Answer: [resposta em texto puro, SEM ```]

REGRAS ABSOLUTAS:
1. Action Input DEVE ser JSON válido em UMA linha
2. NUNCA use ``` (code blocks) em Action Input ou Final Answer
3. Se precisar retornar JSON, coloque direto no Final Answer SEM ```
4. Escape strings corretamente: use \\n para quebras de linha

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
- Criar arquivos usando write_file

Ferramentas disponíveis: {tools}
Nomes: {tool_names}

==== FORMATO OBRIGATÓRIO (CRÍTICO) ====

Thought: [seu raciocínio]
Action: [nome_ferramenta]
Action Input: {{"parametro": "valor"}}

Observation: [resultado]
... repita ...

Final Answer: [resposta SEM ```]

REGRAS PARA write_file:
1. Sempre forneça: file_path, content, overwrite
2. content deve ser STRING com \\n para quebras de linha
3. JSON em UMA linha
4. Use ' (aspas simples) dentro de strings Python
5. NUNCA use ``` em nenhum lugar

EXEMPLO PERFEITO:
Action: write_file
Action Input: {{"file_path": "app.py", "content": "def hello():\\n    print('Hello World')\\n\\nif __name__ == '__main__':\\n    hello()", "overwrite": false}}

Question: {input}
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

        return prompts.get(self.role, prompts[AgentRole.PROJECT_MANAGER])

    def _get_llm_config_for_role(self, config):
        """Obtém configuração do LLM para o papel do agente (do banco ou fallback)."""
        if config and config.llm_config:
            llm_role_str = config.llm_config.get('role', 'ORCHESTRATOR')
            llm_priority_str = config.llm_config.get('priority', 'HIGH_QUALITY')

            # Converter strings para enums
            try:
                llm_role = ModelRole[llm_role_str]
                llm_priority = ModelPriority[llm_priority_str]
                return llm_role, llm_priority
            except KeyError as e:
                logger.warning(f"Configuração LLM inválida no banco: {e}. Usando fallback.")

        # Fallback para mapeamento padrão
        llm_mapping = {
            AgentRole.PROJECT_MANAGER: (ModelRole.ORCHESTRATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.CODER: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
            AgentRole.RESEARCHER: (ModelRole.ORCHESTRATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.TESTER: (ModelRole.CODE_GENERATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.DOCUMENTER: (ModelRole.KNOWLEDGE_CURATOR, ModelPriority.FAST_AND_CHEAP),
            AgentRole.OPTIMIZER: (ModelRole.CODE_GENERATOR, ModelPriority.HIGH_QUALITY),
        }

        return llm_mapping.get(self.role, (ModelRole.ORCHESTRATOR, ModelPriority.LOCAL_ONLY))

    def _initialize_agent(self):
        """Inicializa o executor do agente com prompt especializado."""
        # Tentar carregar configuração do banco de dados
        config = None
        try:
            config = self.config_repo.get_active_config(
                agent_name=self.agent_id,
                agent_role=self.role.value
            )
            if config:
                logger.info(f"Configuração dinâmica carregada para {self.role.value} ({self.agent_id})")
        except Exception as e:
            logger.warning(f"Falha ao carregar configuração dinâmica para {self.role.value}: {e}")

        # Carregar prompt (do banco ou fallback)
        prompt_text = self._get_prompt_for_role(config)
        prompt = PromptTemplate.from_template(prompt_text)

        # Selecionar LLM (do banco ou fallback)
        llm_role, llm_priority = self._get_llm_config_for_role(config)
        llm = get_llm(role=llm_role, priority=llm_priority)

        # Pega as ferramentas e adiciona wrapper para corrigir parsing
        tools = get_all_tools()
        wrapped_tools = [_create_tool_wrapper(tool) for tool in tools]

        agent = create_react_agent(llm, wrapped_tools, prompt)

        # Mensagem de erro personalizada para parsing
        parsing_error_message = """Erro no formato da sua resposta. Use EXATAMENTE este formato:

Thought: [seu raciocínio]
Action: [nome_da_ferramenta]
Action Input: {{"parametro": "valor"}}

IMPORTANTE: O Action Input deve ser JSON VÁLIDO em UMA LINHA.
Para write_file use: {{"file_path": "arquivo.py", "content": "codigo\\naqui", "overwrite": false}}
"""

        # Configurações do executor (do banco ou padrão)
        max_iterations = 15
        max_execution_time = 180
        if config and config.execution_config:
            max_iterations = config.execution_config.get('max_iterations', 15)
            max_execution_time = config.execution_config.get('max_execution_time', 180)

        self.executor = AgentExecutor(
            agent=agent,
            tools=wrapped_tools,  # Usa as ferramentas com wrapper
            verbose=True,
            max_iterations=max_iterations,
            max_execution_time=max_execution_time,
            early_stopping_method="generate",
            handle_parsing_errors=parsing_error_message
        )

    async def execute_task(self, task: Task, max_retries: int = 2) -> Dict[str, Any]:
        """
        Executa uma tarefa atribuída ao agente com retry automático.

        Args:
            task: Tarefa a ser executada
            max_retries: Número máximo de tentativas (padrão: 2)

        Returns:
            Dicionário com resultado da execução
        """
        if task.status != TaskStatus.PENDING:
            raise ValueError(f"Tarefa {task.id} não está em estado PENDING")

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        task.assigned_to = self.agent_id

        logger.info(f"Agente {self.agent_id} iniciando tarefa: {task.description}")

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.warning(f"Tentativa {attempt + 1}/{max_retries + 1} para tarefa {task.id}")
                    await asyncio.sleep(2 ** attempt)  # Backoff exponencial

                # Executar a tarefa
                start_time = asyncio.get_event_loop().time()
                result = await asyncio.to_thread(
                    self.executor.invoke,
                    {"input": task.description}
                )
                duration = asyncio.get_event_loop().time() - start_time

                # Limpar output (remover markdown se presente)
                output = result.get("output", "")
                cleaned_output = _clean_json_output(output)

                # Validar que o resultado não está vazio
                if not cleaned_output or cleaned_output.strip() == "":
                    raise ValueError("Agente retornou output vazio")

                # Atualizar task
                task.status = TaskStatus.COMPLETED
                task.result = cleaned_output
                task.completed_at = datetime.now()

                # Métricas
                AGENT_TASKS_COUNTER.labels(agent_role=self.role.value, status="completed").inc()
                AGENT_TASK_DURATION.labels(agent_role=self.role.value).observe(duration)

                logger.info(f"Tarefa {task.id} concluída com sucesso (tentativa {attempt + 1})")

                return {
                    "task_id": task.id,
                    "status": "completed",
                    "result": task.result,
                    "duration_seconds": duration,
                    "attempts": attempt + 1
                }

            except asyncio.TimeoutError as e:
                last_error = f"Timeout ao executar tarefa: {e}"
                logger.warning(f"Timeout na tentativa {attempt + 1} para tarefa {task.id}")
                if attempt == max_retries:
                    break
                continue

            except ValueError as e:
                # Erros de validação (parsing, output vazio, etc)
                last_error = f"Erro de validação: {e}"
                logger.warning(f"Erro de validação na tentativa {attempt + 1} para tarefa {task.id}: {e}")
                if attempt == max_retries:
                    break
                continue

            except Exception as e:
                last_error = str(e)
                logger.error(f"Erro na tentativa {attempt + 1} para tarefa {task.id}: {e}", exc_info=True)
                if attempt == max_retries:
                    break
                continue

        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Tarefa {task.id} falhou após {max_retries + 1} tentativas: {last_error}")
        task.status = TaskStatus.FAILED
        task.error = last_error
        task.completed_at = datetime.now()
        AGENT_TASKS_COUNTER.labels(agent_role=self.role.value, status="failed").inc()

        return {
            "task_id": task.id,
            "status": "failed",
            "error": last_error,
            "attempts": max_retries + 1
        }

    def communicate(self, to_agent_id: str, message: str):
        """Envia uma mensagem para outro agente."""
        self.workspace.send_message(self.agent_id, to_agent_id, message)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Recupera mensagens destinadas a este agente."""
        return self.workspace.get_messages_for(self.agent_id)

    def update_config(self, config):
        """Atualiza a configuração do agente dinamicamente."""
        try:
            logger.info(f"Atualizando configuração do agente {self.agent_id}")
            self._initialize_agent()
            logger.info(f"Configuração do agente {self.agent_id} atualizada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração do agente {self.agent_id}: {e}")
            raise

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
        self._ensure_workspace_directory()
        logger.info("Sistema Multi-Agente inicializado")

    def _ensure_workspace_directory(self):
        """Garante que o diretório workspace existe."""
        from pathlib import Path
        workspace_path = Path("/app/workspace")
        if not workspace_path.exists():
            workspace_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório workspace criado em: {workspace_path}")
        else:
            logger.info(f"Diretório workspace já existe: {workspace_path}")

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

    def update_agent_config(self, agent_id: str, config) -> bool:
        """Atualiza a configuração de um agente específico."""
        agent = self.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agente {agent_id} não encontrado para atualização de configuração")
            return False

        try:
            agent.update_config(config)
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração do agente {agent_id}: {e}")
            return False

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

    async def execute_tasks_parallel(
            self,
            task_ids: Optional[List[str]] = None,
            concurrency: int = 4
    ) -> Dict[str, Any]:
        """Executa múltiplas tarefas em paralelo respeitando dependências.

        - Seleciona tarefas por `task_ids` ou todas PENDING no workspace
        - Usa um semáforo para limitar paralelismo
        - Agenda novas tarefas assim que suas dependências forem concluídas
        - Marca tarefas impossíveis de resolver como BLOCKED
        """
        if concurrency < 1:
            concurrency = 1

        # Seleção inicial de tarefas alvo
        if task_ids:
            target_tasks = [t for tid, t in self.workspace.tasks.items() if tid in task_ids]
        else:
            target_tasks = [t for t in self.workspace.tasks.values() if t.status == TaskStatus.PENDING]

        # Mapa rápido
        task_map: Dict[str, Task] = {t.id: t for t in target_tasks}
        if not task_map:
            return {
                "scheduled": 0,
                "completed": 0,
                "failed": 0,
                "blocked": [],
                "results": {},
            }

        # Dependentes e contagem de dependências não satisfeitas
        dependents: Dict[str, List[str]] = {tid: [] for tid in task_map}
        remaining_deps: Dict[str, int] = {}
        invalid_dependency: Dict[str, bool] = {tid: False for tid in task_map}

        for t in target_tasks:
            deps = [d for d in (t.dependencies or []) if d in self.workspace.tasks]
            # Se há dependência inexistente, marca como inválida
            for d in (t.dependencies or []):
                if d not in self.workspace.tasks:
                    invalid_dependency[t.id] = True
            remaining = 0
            for d in deps:
                dep_task = self.workspace.tasks.get(d)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    remaining += 1
                # Registra relacionamento dependente → depende de
                if d in task_map:
                    dependents[d].append(t.id)
            remaining_deps[t.id] = remaining

        # Fila de prontas
        from collections import deque
        ready_queue = deque([t for t in target_tasks if remaining_deps[t.id] == 0 and not invalid_dependency[t.id]])

        # Controle de paralelismo
        sem = asyncio.Semaphore(concurrency)
        running: set = set()
        results: Dict[str, Any] = {}

        async def _run_single(task: Task):
            async with sem:
                # Seleção simples de agente: usa assigned_to se disponível, senão PM
                agent: Optional[SpecializedAgent] = None
                if task.assigned_to:
                    agent = self.get_agent(task.assigned_to)
                if agent is None:
                    if not self.project_manager:
                        self.project_manager = self.create_agent(AgentRole.PROJECT_MANAGER)
                    agent = self.project_manager
                try:
                    return await agent.execute_task(task)
                except Exception as e:
                    return {"task_id": task.id, "status": "failed", "error": str(e)}

        # Loop principal de agendamento
        scheduled_count = 0
        while ready_queue or running:
            # Agenda todas as tarefas atualmente prontas
            while ready_queue:
                t = ready_queue.popleft()
                scheduled_count += 1
                fut = asyncio.create_task(_run_single(t))
                # Anexa o ID para identificação
                fut._task_id = t.id  # type: ignore[attr-defined]
                running.add(fut)

            if not running:
                break

            done, pending = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
            running = pending
            for fut in done:
                tid = getattr(fut, "_task_id", None)
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"task_id": tid, "status": "failed", "error": str(e)}
                if tid:
                    results[tid] = res
                    # Atualiza dependentes
                    status = res.get("status")
                    if status == "completed":
                        for dep in dependents.get(tid, []):
                            remaining_deps[dep] = max(0, remaining_deps[dep] - 1)
                            dep_task = task_map.get(dep)
                            if dep_task and remaining_deps[dep] == 0 and not invalid_dependency.get(dep, False):
                                if dep_task.status == TaskStatus.PENDING:
                                    ready_queue.append(dep_task)

        # Determina bloqueadas e falhas
        completed = sum(1 for r in results.values() if r.get("status") == "completed")
        failed = sum(1 for r in results.values() if r.get("status") == "failed")
        blocked: List[str] = []
        for tid, t in task_map.items():
            if t.status == TaskStatus.PENDING and (
                    remaining_deps.get(tid, 0) > 0 or invalid_dependency.get(tid, False)):
                t.status = TaskStatus.BLOCKED
                blocked.append(tid)

        return {
            "scheduled": scheduled_count,
            "completed": completed,
            "failed": failed,
            "blocked": blocked,
            "results": results,
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
