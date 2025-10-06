"""
Message Broker - Sprint 1

Sistema de comunicação assíncrona e distribuída usando RabbitMQ.
Permite que diferentes componentes do Janus troquem mensagens de forma desacoplada.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

import aio_pika
from aio_pika import Connection, Channel, Exchange, Queue, Message
from aio_pika.abc import AbstractIncomingMessage
from prometheus_client import Counter, Histogram, Gauge

from app.config import settings
from app.core.infrastructure.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

# Métricas
MESSAGE_PUBLISHED = Counter(
    "message_broker_published_total",
    "Total de mensagens publicadas",
    ["queue", "outcome"]
)
MESSAGE_CONSUMED = Counter(
    "message_broker_consumed_total",
    "Total de mensagens consumidas",
    ["queue", "outcome"]
)
MESSAGE_LATENCY = Histogram(
    "message_broker_latency_seconds",
    "Latência de processamento de mensagens",
    ["queue", "operation"]
)
QUEUE_DEPTH = Gauge(
    "message_broker_queue_depth",
    "Profundidade da fila",
    ["queue"]
)
ACTIVE_CONSUMERS = Gauge(
    "message_broker_active_consumers",
    "Consumidores ativos",
    ["queue"]
)

# Circuit Breakers
_publish_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
_consume_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)


class QueueName(str, Enum):
    """Filas disponíveis no sistema."""
    KNOWLEDGE_CONSOLIDATION = "janus.knowledge.consolidation"
    DATA_HARVESTING = "janus.data.harvesting"
    AGENT_TASKS = "janus.agent.tasks"
    META_AGENT_CYCLE = "janus.meta_agent.cycle"
    NEURAL_TRAINING = "janus.neural.training"


@dataclass
class TaskMessage:
    """Estrutura de mensagem de tarefa."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    timestamp: float
    retry_count: int = 0
    correlation_id: Optional[str] = None

    def to_json(self) -> str:
        """Serializa para JSON."""
        return json.dumps({
            "task_id": self.task_id,
            "task_type": self.task_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "correlation_id": self.correlation_id
        })

    @classmethod
    def from_json(cls, data: str) -> "TaskMessage":
        """Deserializa de JSON."""
        obj = json.loads(data)
        return cls(**obj)


class MessageBroker:
    """
    Cliente RabbitMQ assíncrono para publicação e consumo de mensagens.
    """

    def __init__(self):
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.exchange: Optional[Exchange] = None
        self._consumers: Dict[str, asyncio.Task] = {}
        self._is_connected = False
        self._connection_lock = asyncio.Lock()

    @property
    def rabbitmq_url(self) -> str:
        """Constrói URL de conexão do RabbitMQ."""
        user = getattr(settings, "RABBITMQ_USER", "janus")
        password = getattr(settings, "RABBITMQ_PASSWORD", "janus_pass")
        host = getattr(settings, "RABBITMQ_HOST", "rabbitmq")
        port = getattr(settings, "RABBITMQ_PORT", 5672)

        return f"amqp://{user}:{password}@{host}:{port}/"

    @resilient(
        max_attempts=5,
        initial_backoff=2.0,
        max_backoff=30.0,
        circuit_breaker=_publish_cb,
        retry_on=(Exception,),
        operation_name="rabbitmq_connect"
    )
    async def connect(self) -> None:
        """
        Estabelece conexão com RabbitMQ.
        """
        async with self._connection_lock:
            if self._is_connected and self.connection and not self.connection.is_closed:
                logger.debug("Conexão RabbitMQ já estabelecida.")
                return

            try:
                logger.info(f"Conectando ao RabbitMQ em {self.rabbitmq_url}...")

                self.connection = await aio_pika.connect_robust(
                    self.rabbitmq_url,
                    timeout=10.0,
                    heartbeat=60,
                )

                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=10)

                # Cria exchange padrão (direct)
                self.exchange = await self.channel.declare_exchange(
                    "janus.tasks",
                    aio_pika.ExchangeType.DIRECT,
                    durable=True
                )

                self._is_connected = True
                logger.info("✓ Conexão com RabbitMQ estabelecida com sucesso.")

            except Exception as e:
                self._is_connected = False
                logger.error(f"Erro ao conectar ao RabbitMQ: {e}", exc_info=True)
                raise

    async def disconnect(self) -> None:
        """Fecha conexão com RabbitMQ."""
        async with self._connection_lock:
            # Cancela consumidores ativos
            for queue_name, task in self._consumers.items():
                logger.info(f"Cancelando consumidor da fila {queue_name}...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self._consumers.clear()

            # Fecha canal e conexão
            if self.channel and not self.channel.is_closed:
                await self.channel.close()

            if self.connection and not self.connection.is_closed:
                await self.connection.close()

            self._is_connected = False
            logger.info("Conexão com RabbitMQ fechada.")

    async def _ensure_queue(self, queue_name: str) -> Queue:
        """
        Garante que uma fila existe, criando-a se necessário.

        Args:
            queue_name: Nome da fila

        Returns:
            Objeto Queue
        """
        if not self.channel:
            await self.connect()

        queue = await self.channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 horas
                "x-max-length": 10000,  # Limite de mensagens
            }
        )

        # Bind queue ao exchange
        await queue.bind(self.exchange, routing_key=queue_name)

        return queue

    @resilient(
        max_attempts=3,
        initial_backoff=1.0,
        max_backoff=5.0,
        circuit_breaker=_publish_cb,
        retry_on=(Exception,),
        operation_name="rabbitmq_publish"
    )
    async def publish(
            self,
            queue_name: str,
            message: TaskMessage,
            priority: int = 0
    ) -> None:
        """
        Publica uma mensagem em uma fila.

        Args:
            queue_name: Nome da fila
            message: Mensagem a ser publicada
            priority: Prioridade (0-9, maior = mais prioritário)
        """
        start = time.perf_counter()

        try:
            if not self._is_connected:
                await self.connect()

            await self._ensure_queue(queue_name)

            # Cria mensagem AMQP
            amqp_message = Message(
                body=message.to_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                priority=priority,
                correlation_id=message.correlation_id,
                timestamp=int(message.timestamp)
            )

            # Publica no exchange com routing key = queue_name
            await self.exchange.publish(
                amqp_message,
                routing_key=queue_name
            )

            elapsed = time.perf_counter() - start

            MESSAGE_PUBLISHED.labels(queue_name, "success").inc()
            MESSAGE_LATENCY.labels(queue_name, "publish").observe(elapsed)

            logger.info(
                f"Mensagem publicada em {queue_name}: "
                f"task_id={message.task_id}, type={message.task_type}, "
                f"latency={elapsed:.3f}s"
            )

        except Exception as e:
            MESSAGE_PUBLISHED.labels(queue_name, "error").inc()
            logger.error(
                f"Erro ao publicar mensagem em {queue_name}: {e}",
                exc_info=True
            )
            raise

    async def consume(
            self,
            queue_name: str,
            callback: Callable[[TaskMessage], Any],
            prefetch_count: int = 10
    ) -> None:
        """
        Consome mensagens de uma fila de forma contínua.

        Args:
            queue_name: Nome da fila
            callback: Função a ser chamada para cada mensagem
            prefetch_count: Número de mensagens para pré-buscar
        """
        if not self._is_connected:
            await self.connect()

        queue = await self._ensure_queue(queue_name)

        # Configura QoS
        await self.channel.set_qos(prefetch_count=prefetch_count)

        logger.info(f"Iniciando consumidor para fila {queue_name}...")

        async def process_message(message: AbstractIncomingMessage):
            """Processa uma mensagem recebida."""
            start = time.perf_counter()

            async with message.process():
                try:
                    # Deserializa mensagem
                    task_message = TaskMessage.from_json(message.body.decode())

                    logger.debug(
                        f"Processando mensagem de {queue_name}: "
                        f"task_id={task_message.task_id}"
                    )

                    # Chama callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_message)
                    else:
                        await asyncio.to_thread(callback, task_message)

                    elapsed = time.perf_counter() - start

                    MESSAGE_CONSUMED.labels(queue_name, "success").inc()
                    MESSAGE_LATENCY.labels(queue_name, "consume").observe(elapsed)

                    logger.info(
                        f"Mensagem processada com sucesso: "
                        f"queue={queue_name}, task_id={task_message.task_id}, "
                        f"latency={elapsed:.3f}s"
                    )

                except Exception as e:
                    MESSAGE_CONSUMED.labels(queue_name, "error").inc()
                    logger.error(
                        f"Erro ao processar mensagem de {queue_name}: {e}",
                        exc_info=True
                    )
                    # Mensagem será rejeitada automaticamente e pode ir para DLQ

        # Inicia consumidor
        await queue.consume(process_message)

        ACTIVE_CONSUMERS.labels(queue_name).inc()
        logger.info(f"✓ Consumidor ativo para fila {queue_name}")

    def start_consumer(
            self,
            queue_name: str,
            callback: Callable[[TaskMessage], Any],
            prefetch_count: int = 10
    ) -> asyncio.Task:
        """
        Inicia um consumidor em background.

        Args:
            queue_name: Nome da fila
            callback: Função de processamento
            prefetch_count: Mensagens pré-buscadas

        Returns:
            Task do consumidor
        """

        async def consumer_wrapper():
            try:
                await self.consume(queue_name, callback, prefetch_count)
                # Mantém consumidor rodando
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info(f"Consumidor de {queue_name} cancelado.")
                ACTIVE_CONSUMERS.labels(queue_name).dec()
            except Exception as e:
                logger.error(f"Erro fatal no consumidor {queue_name}: {e}")
                ACTIVE_CONSUMERS.labels(queue_name).dec()

        task = asyncio.create_task(consumer_wrapper())
        self._consumers[queue_name] = task

        return task

    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """
        Obtém informações sobre uma fila.

        Args:
            queue_name: Nome da fila

        Returns:
            Dicionário com informações da fila
        """
        if not self._is_connected:
            await self.connect()

        queue = await self._ensure_queue(queue_name)
        declaration = await queue.declare(passive=True)

        info = {
            "name": queue_name,
            "messages": declaration.message_count,
            "consumers": declaration.consumer_count,
        }

        QUEUE_DEPTH.labels(queue_name).set(declaration.message_count)

        return info

    async def health_check(self) -> bool:
        """
        Verifica saúde da conexão com RabbitMQ.

        Returns:
            True se saudável
        """
        try:
            if not self._is_connected:
                await self.connect()

            # Testa com operação simples
            await self.channel.declare_exchange(
                "janus.health_check",
                aio_pika.ExchangeType.DIRECT,
                durable=False,
                auto_delete=True
            )

            return True

        except Exception as e:
            logger.warning(f"Health check RabbitMQ falhou: {e}")
            return False


# Instância global
message_broker = MessageBroker()


@asynccontextmanager
async def get_message_broker():
    """
    Context manager para obter instância do message broker.

    Usage:
        async with get_message_broker() as broker:
            await broker.publish(...)
    """
    if not message_broker._is_connected:
        await message_broker.connect()

    try:
        yield message_broker
    finally:
        pass  # Mantém conexão aberta para reutilização
