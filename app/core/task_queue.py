# app/core/task_queue.py
import asyncio
from pydantic import BaseModel
from app.core.schemas import AgentType

class Task(BaseModel):
    """Define a estrutura de uma tarefa de auto-otimização."""
    task_description: str
    target_agent: AgentType = AgentType.TOOL_USER

class TaskQueue:
    """
    Uma fila de tarefas assíncrona para gerir as missões de auto-otimização
    geradas pelo Meta-Agente.
    """
    def __init__(self):
        self._queue: asyncio.Queue[Task] = asyncio.Queue()

    async def add_task(self, task: Task):
        """Adiciona uma nova tarefa à fila."""
        await self._queue.put(task)

    async def get_task(self) -> Task:
        """Obtém a próxima tarefa da fila, aguardando se estiver vazia."""
        return await self._queue.get()

    def task_done(self):
        """Sinaliza que uma tarefa foi concluída."""
        self._queue.task_done()

# Instância única (singleton) para ser usada em toda a aplicação.
task_queue = TaskQueue()
