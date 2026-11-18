import asyncio
import structlog
from typing import Any

from app.core.agents.multi_agent_system import SpecializedAgent, Task, TaskStatus
from app.core.infrastructure.message_broker import MessageBroker, get_broker
from app.models.schemas import TaskMessage

logger = structlog.get_logger(__name__)


class AgentActor:
    """
    Ator que encapsula um agente especializado e processa mensagens de uma fila RabbitMQ.
    """

    def __init__(self, agent: SpecializedAgent):
        self.agent = agent
        self.broker: MessageBroker | None = None
        self.queue_name = f"janus.agent.{agent.role.value}"
        self.results_queue = "janus.agent.results"
        self._is_running = False
        self._consumer_task: asyncio.Task | None = None

    async def start(self):
        """Inicia o ator e o consumidor da fila."""
        if self._is_running:
            return

        self.broker = await get_broker()
        self._is_running = True
        logger.info("log_info", message=f"Iniciando AgentActor para {self.agent.role.value} na fila {self.queue_name}")

        # Inicia consumidor
        self._consumer_task = self.broker.start_consumer(
            queue_name=self.queue_name,
            callback=self._on_message,
            prefetch_count=1,  # Um agente processa uma tarefa por vez para evitar sobrecarga
        )

    async def stop(self):
        """Para o ator."""
        self._is_running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("log_info", message=f"AgentActor para {self.agent.role.value} parado")

    async def _on_message(self, message: TaskMessage):
        """Callback processar mensagem da fila."""
        logger.info("log_info", message=f"AgentActor {self.agent.role.value} recebeu tarefa: {message.task_id}")

        try:
            # Reconstrói objeto Task (simplificado)
            # Na prática, o payload deve conter tudo que o agente precisa
            task_data = message.payload
            task = Task(
                id=message.task_id,
                description=task_data.get("description", ""),
                status=TaskStatus.PENDING,  # Será atualizado pelo agente
                dependencies=task_data.get("dependencies", []),
                metadata=task_data.get("metadata", {}),
            )

            # Callbacks de progresso
            async def on_agent_event(event_type: str, content: str):
                conversation_id = task.metadata.get("conversation_id", "global")
                await self._publish_event(task.id, event_type, content, conversation_id)

            # Injeta callback no agente (requer suporte no SpecializedAgent)
            # Para não quebrar, verificamos se o agente suporta
            if hasattr(self.agent, "set_event_callback"):
                self.agent.set_event_callback(on_agent_event)

            # Executa a tarefa usando a lógica do agente
            result = await self.agent.execute_task(task)

            # Publica resultado
            await self._publish_result(result)

        except Exception as e:
            logger.error("log_error", message=f"Erro fatal no AgentActor {self.agent.role.value}: {e}", exc_info=True)
            # Tenta publicar erro
            await self._publish_result(
                {
                    "task_id": message.task_id,
                    "status": "failed",
                    "error": str(e),
                    "agent_role": self.agent.role.value,
                }
            )

    async def _publish_result(self, result: dict[str, Any]):
        """Publica o resultado na fila de resultados."""
        if not self.broker:
            return

        try:
            # Cria mensagem de resultado
            msg = TaskMessage(
                task_id=result.get("task_id", "unknown"),
                task_type="task_result",
                payload=result,
                timestamp=asyncio.get_event_loop().time(),
            )

            await self.broker.publish(queue_name=self.results_queue, message=msg.model_dump())
            logger.info("log_info", message=f"Resultado da tarefa {msg.task_id} publicado por {self.agent.role.value}")

        except Exception as e:
            logger.error("log_error", message=f"Erro ao publicar resultado da tarefa {result.get('task_id')}: {e}")

    async def _publish_event(
        self, task_id: str, event_type: str, content: str, conversation_id: str = "global"
    ):
        """Publica um evento de progresso na exchange de eventos."""
        if not self.broker:
            return

        try:
            event_payload = {
                "task_id": task_id,
                "agent_role": self.agent.role.value,
                "event_type": event_type,
                "content": content,
                "conversation_id": conversation_id,
                "timestamp": asyncio.get_event_loop().time(),
            }

            # Routing key estruturada: janus.event.conversation.{cid}.agent.{role}
            routing_key = (
                f"janus.event.conversation.{conversation_id}.agent.{self.agent.role.value}"
            )

            await self.broker.publish_to_exchange(
                exchange_name="janus.events", routing_key=routing_key, message=event_payload
            )

        except Exception as e:
            logger.warning("log_warning", message=f"Erro ao publicar evento {event_type} para tarefa {task_id}: {e}")
