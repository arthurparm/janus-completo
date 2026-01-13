"""
Sistema de Colaboração Multi-Agente (Sprint 11).

Implementa uma "Sociedade de Mentes" onde múltiplos agentes especializados
trabalham em conjunto, coordenados por um Agente Gestor de Projetos.
"""

import asyncio
import logging
from typing import Any
from pathlib import Path

from app.config import settings
from app.core.tools.os_tools import register_os_tools

from app.core.agents.structures import AgentRole, Task, TaskStatus, TaskPriority
from app.core.agents.workspace import SharedWorkspace
from app.core.agents.specialized_agent import SpecializedAgent

logger = logging.getLogger(__name__)

# Re-import missing utility if not in utils
from app.core.infrastructure.prompt_fallback import get_formatted_prompt


class MultiAgentSystem:
    """Sistema coordenado de múltiplos agentes."""

    def __init__(self):
        self.workspace = SharedWorkspace()
        self.agents: dict[str, SpecializedAgent] = {}
        self.project_manager: SpecializedAgent | None = None

        # Registra ferramentas de SO (SysAdmin)
        register_os_tools()

        self._ensure_workspace_directory()
        logger.info("Sistema Multi-Agente inicializado")

    def _ensure_workspace_directory(self):
        """Garante que o diretório workspace existe."""
        workspace_path = Path(settings.WORKSPACE_ROOT)
        try:
            if not workspace_path.exists():
                workspace_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Diretório workspace criado em: {workspace_path}")
            else:
                logger.info(f"Diretório workspace já existe: {workspace_path}")
        except Exception as e:
            logger.error(f"Erro ao criar diretório workspace em {workspace_path}: {e}")
            # Fallback para diretório temporário se não conseguir criar no local configurado
            import tempfile

            fallback_path = Path(tempfile.gettempdir()) / "janus_workspace"
            if not fallback_path.exists():
                fallback_path.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Usando diretório fallback: {fallback_path}")
            # Atualiza o settings para refletir o novo caminho
            settings.WORKSPACE_ROOT = str(fallback_path)

    async def create_agent(self, role: AgentRole) -> SpecializedAgent:
        """Cria um novo agente especializado e seu ator correspondente (ASYNC)."""
        agent = SpecializedAgent(role, self.workspace)
        await agent._initialize_agent()  # Accessing protected method since we are friend class/system

        self.agents[agent.agent_id] = agent

        # Inicializa o Ator para este agente
        # Import local para evitar ciclo
        from app.core.agents.agent_actor import AgentActor

        actor = AgentActor(agent)

        # Armazena o ator (em produção, idealmente gerenciado separadamente)
        # Hack para iniciar o consumidor em background na mesma loop
        asyncio.create_task(actor.start())

        logger.info(f"Ator iniciado para agente {agent.agent_id} ({role.value})")

        if role == AgentRole.PROJECT_MANAGER and not self.project_manager:
            self.project_manager = agent

        return agent

    async def dispatch_task(self, task: Task):
        """Despacha uma tarefa para a fila do agente responsável."""
        from app.core.infrastructure.message_broker import get_broker
        from app.models.schemas import TaskMessage

        if not task.assigned_to:
            raise ValueError("Tarefa sem agente atribuído")

        agent = self.agents.get(task.assigned_to)
        if not agent:
            raise ValueError(f"Agente {task.assigned_to} não encontrado")

        broker = await get_broker()
        queue_name = f"janus.agent.{agent.role.value}"

        # Cria payload
        payload = {
            "description": task.description,
            "dependencies": task.dependencies,
            "metadata": task.metadata,
        }

        msg = TaskMessage(
            task_id=task.id,
            task_type="agent_task",
            payload=payload,
            timestamp=datetime.now().timestamp(),
        )

        await broker.publish(queue_name, msg.model_dump())
        logger.info(f"Tarefa {task.id} despachada para fila {queue_name}")

    def get_agent(self, agent_id: str) -> SpecializedAgent | None:
        """Recupera um agente pelo ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> list[dict[str, Any]]:
        """Lista todos os agentes ativos."""
        return [
            {
                "agent_id": agent.agent_id,
                "role": agent.role.value,
                "tasks_assigned": len(self.workspace.get_tasks_by_agent(agent.agent_id)),
            }
            for agent in self.agents.values()
        ]

    async def execute_project(self, project_description: str) -> dict[str, Any]:
        """
        Executa um projeto completo usando coordenação multi-agente.

        O Gestor de Projetos analisa o requisito, divide em tarefas,
        atribui aos agentes especializados e coordena a execução.
        """
        if not self.project_manager:
            self.project_manager = await self.create_agent(AgentRole.PROJECT_MANAGER)

        logger.info(f"Iniciando projeto: {project_description}")

        # 1. PM analisa e decompõe o projeto
        decomposition_prompt = await get_formatted_prompt(
            "multi_agent_decomposition", project_description=project_description
        )

        pm_task = Task(
            description=decomposition_prompt,
            assigned_to=self.project_manager.agent_id,
            priority=TaskPriority.CRITICAL,
        )
        self.workspace.add_task(pm_task)

        # MUDANÇA PARA PARALELISMO:
        # Em vez de await self.project_manager.execute_task(pm_task),
        # nós despachamos para a fila.
        await self.dispatch_task(pm_task)

        # Para compatibilidade imediata com testes antigos que esperam retorno síncrono,
        # poderíamos esperar polling aqui. Mas como o objetivo é migrar para async,
        # retornamos status de "em andamento".

        return {
            "project_status": "started",
            "pm_task_id": pm_task.id,
            "message": "Projeto iniciado. Acompanhe via eventos ou polling.",
        }

    async def update_agent_config(self, agent_id: str, config) -> bool:
        """Atualiza a configuração de um agente específico."""
        agent = self.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agente {agent_id} não encontrado para atualização de configuração")
            return False

        try:
            await agent.update_config(config)
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar configuração do agente {agent_id}: {e}")
            return False

    def get_workspace_status(self) -> dict[str, Any]:
        """Retorna status do workspace compartilhado."""
        return {
            "total_artifacts": len(self.workspace.artifacts),
            "total_messages": len(self.workspace.messages),
            "total_tasks": len(self.workspace.tasks),
            "tasks_by_status": {
                status.value: len(self.workspace.get_tasks_by_status(status))
                for status in TaskStatus
            },
        }

    async def execute_tasks_parallel(
        self, task_ids: list[str] | None = None, concurrency: int = 4
    ) -> dict[str, Any]:
        """Executa múltiplas tarefas em paralelo respeitando dependências.

        - Seleciona tarefas por `task_ids` ou todas PENDING no workspace
        - Usa um semáforo para limitar paralelismo
        - Agenda novas tarefas assim que suas dependências forem concluídas
        - Marca tarefas impossíveis de resolver como BLOCKED
        """
        concurrency = max(concurrency, 1)

        # Seleção inicial de tarefas alvo
        if task_ids:
            target_tasks = [t for tid, t in self.workspace.tasks.items() if tid in task_ids]
        else:
            target_tasks = [
                t for t in self.workspace.tasks.values() if t.status == TaskStatus.PENDING
            ]

        # Mapa rápido
        task_map: dict[str, Task] = {t.id: t for t in target_tasks}
        if not task_map:
            return {
                "scheduled": 0,
                "completed": 0,
                "failed": 0,
                "blocked": [],
                "results": {},
            }

        # Dependentes e contagem de dependências não satisfeitas
        dependents: dict[str, list[str]] = {tid: [] for tid in task_map}
        remaining_deps: dict[str, int] = {}
        invalid_dependency: dict[str, bool] = {tid: False for tid in task_map}

        for t in target_tasks:
            deps = [d for d in (t.dependencies or []) if d in self.workspace.tasks]
            # Se há dependência inexistente, marca como inválida
            for d in t.dependencies or []:
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

        ready_queue = deque(
            [t for t in target_tasks if remaining_deps[t.id] == 0 and not invalid_dependency[t.id]]
        )

        # Controle de paralelismo
        sem = asyncio.Semaphore(concurrency)
        running: set = set()
        results: dict[str, Any] = {}

        async def _run_single(task: Task):
            async with sem:
                # Seleção simples de agente: usa assigned_to se disponível, senão PM
                agent: SpecializedAgent | None = None
                if task.assigned_to:
                    agent = self.get_agent(task.assigned_to)
                if agent is None:
                    if not self.project_manager:
                        self.project_manager = await self.create_agent(AgentRole.PROJECT_MANAGER)
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
                            if (
                                dep_task
                                and remaining_deps[dep] == 0
                                and not invalid_dependency.get(dep, False)
                            ):
                                if dep_task.status == TaskStatus.PENDING:
                                    ready_queue.append(dep_task)

        # Determina bloqueadas e falhas
        completed = sum(1 for r in results.values() if r.get("status") == "completed")
        failed = sum(1 for r in results.values() if r.get("status") == "failed")
        blocked: list[str] = []
        for tid, t in task_map.items():
            if t.status == TaskStatus.PENDING and (
                remaining_deps.get(tid, 0) > 0 or invalid_dependency.get(tid, False)
            ):
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
_multi_agent_system: MultiAgentSystem | None = None


def get_multi_agent_system() -> MultiAgentSystem:
    """Obtém a instância global do sistema multi-agente."""
    global _multi_agent_system
    if _multi_agent_system is None:
        _multi_agent_system = MultiAgentSystem()
    return _multi_agent_system
