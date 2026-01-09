import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from app.core.agents.meta_agent import MetaAgent
from app.core.infrastructure.message_broker import MessageBroker, get_broker

logger = logging.getLogger(__name__)


class MetaAgentWorker:
    """
    Worker que envolve o Meta-Agente para execução assíncrona orientada a eventos.
    Escuta a fila 'janus.meta_agent.cycle' para disparar ciclos de análise.
    Também possui um agendador interno para disparos periódicos (heartbeat).
    """

    def __init__(self, interval_seconds: int = 3600):
        self.agent = MetaAgent()
        self.broker: MessageBroker | None = None
        self.queue_name = "janus.meta_agent.cycle"
        self._is_running = False
        self._consumer_task: asyncio.Task | None = None
        self._scheduler_task: asyncio.Task | None = None
        self.interval_seconds = interval_seconds

    async def start(self):
        """Inicia o worker, consumidor e agendador."""
        if self._is_running:
            return

        self.broker = await get_broker()
        self._is_running = True
        logger.info(f"Iniciando MetaAgentWorker na fila {self.queue_name}")

        # Inicia consumidor RabbitMQ
        self._consumer_task = self.broker.start_consumer(
            queue_name=self.queue_name, callback=self._on_message, prefetch_count=1
        )

        # Inicia agendador de heartbeat
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Para o worker."""
        self._is_running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        if self._consumer_task:
            self._consumer_task.cancel()  # Broker usually handles this via close, but task might need cancel
            # Note: Broker.start_consumer returns a task? agent_actor.py suggests yes.
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        logger.info("MetaAgentWorker parado")

    async def _scheduler_loop(self):
        """Loop que publica eventos de gatilho periodicamente."""
        logger.info(f"MetaAgentWorker: Scheduler iniciado (intervalo={self.interval_seconds}s)")
        while self._is_running:
            try:
                await asyncio.sleep(self.interval_seconds)
                await self._trigger_cycle("scheduled_heartbeat")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no scheduler do MetaAgent: {e}")
                await asyncio.sleep(60)  # Backoff on error

    async def _trigger_cycle(self, source: str):
        """Publica uma mensagem para si mesmo para iniciar um ciclo."""
        if not self.broker:
            return

        task_id = str(uuid.uuid4())

        # Payload deve corresponder à estrutura de TaskMessage (dict)
        # O broker espera que o json recebido seja compatível com TaskMessage(**payload)
        # Mas aqui estamos publicando 'payload' que vai ser o corpo da mensagem.
        # Se olharmos o consumidor: payload = json.loads(message.body) -> TaskMessage(**payload)
        # Então precisamos enviar um dict que TEM task_id, task_type, etc.

        message_dict = {
            "task_id": task_id,
            "task_type": "meta_agent_cycle",
            "payload": {"source": source, "timestamp": datetime.now().isoformat()},
            "timestamp": datetime.now().timestamp(),
        }

        try:
            await self.broker.publish(queue_name=self.queue_name, message=message_dict)
            logger.debug(f"Gatilho de ciclo ({source}) publicado.")
        except Exception as e:
            logger.error(f"Falha ao publicar gatilho de ciclo: {e}")

    async def _on_message(self, message: Any):
        """
        Callback ao receber mensagem da fila.
        O payload pode ser ignorado ou usado para configurar a análise.
        Nota: agent_actor espera um TaskMessage object se tipado, mas o callback recebe o que o broker envia.
        O broker do Janus geralmente deserializa JSON.
        """
        logger.info("MetaAgentWorker recebeu sinal de execução.")

        try:
            # Executa o ciclo de análise
            # O MetaAgent já lida com seus próprios logs e métricas.
            await self.agent.run_analysis_cycle()

            # Opcional: Publicar o relatório em uma events exchange?
            # meta_agent.py já loga, mas poderíamos publicar 'janus.events.meta_agent.report'

        except Exception as e:
            logger.error(f"Erro fatal executando ciclo do MetaAgent via Worker: {e}", exc_info=True)
