import asyncio
import logging
import json
from typing import Optional, Callable, Awaitable, Any

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from prometheus_client import Counter

from app.config import settings

logger = logging.getLogger(__name__)

# --- Métricas ---
_MESSAGES_PUBLISHED = Counter("broker_messages_published_total", "Total de mensagens publicadas", ["queue"])
_CONNECTION_ERRORS = Counter("broker_connection_errors_total", "Total de erros de conexão com o broker")

class MessageBroker:
    """
    Gerencia a conexão e as operações com o message broker (RabbitMQ).
    """
    _connection: Optional[AbstractRobustConnection] = None
    _connection_lock = asyncio.Lock()

    async def connect(self):
        """Estabelece a conexão com o RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return
        async with self._connection_lock:
            if self._connection and not self._connection.is_closed:
                return
            logger.info("Conectando ao RabbitMQ...")
            try:
                rabbitmq_url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
                self._connection = await aio_pika.connect_robust(
                    rabbitmq_url,
                    client_properties={"connection_name": "janus_system"}
                )
                logger.info("Conexão com RabbitMQ estabelecida com sucesso.")
            except Exception as e:
                _CONNECTION_ERRORS.inc()
                logger.critical(f"FATAL: Não foi possível conectar ao RabbitMQ: {e}", exc_info=True)
                raise ConnectionError(f"Falha ao conectar ao RabbitMQ: {e}") from e

    async def close(self):
        """Fecha a conexão com o RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            logger.info("Conexão com RabbitMQ fechada.")

    async def publish(self, queue_name: str, message: str):
        """
        Publica uma mensagem em uma fila.
        """
        await self.connect()
        async with self._connection.channel() as channel:
            arguments = {}
            if queue_name in ["janus.knowledge.consolidation", "default"]:
                arguments["x-message-ttl"] = 86400000
                arguments["x-max-length"] = 10000
            await channel.declare_queue(queue_name, durable=True, arguments=arguments or None)
            await channel.default_exchange.publish(
                aio_pika.Message(body=message.encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=queue_name,
            )
            _MESSAGES_PUBLISHED.labels(queue_name).inc()

    async def get_queue_info(self, queue_name: str) -> Optional[dict]:
        """
        Obtém informações sobre uma fila.
        """
        await self.connect()
        async with self._connection.channel() as channel:
            arguments = {}
            if queue_name in ["janus.knowledge.consolidation", "default"]:
                arguments["x-message-ttl"] = 86400000
                arguments["x-max-length"] = 10000
            queue = await channel.declare_queue(queue_name, durable=True, arguments=arguments or None)
            return {
                "name": queue.name,
                "messages": queue.declaration_result.message_count,
                "consumers": queue.declaration_result.consumer_count,
            }

    async def health_check(self) -> bool:
        """
        Verifica a saúde da conexão.
        """
        try:
            await self.connect()
            return not self._connection.is_closed
        except Exception:
            return False

    def start_consumer(
        self,
        queue_name: str,
        callback: Callable[[Any], Awaitable[Any]],
        prefetch_count: int = 10,
    ) -> asyncio.Task:
        """
        Inicia um consumidor robusto com suporte a prefetch e reconexão.

        - Usa conexão robusta (connect_robust) para reconectar automaticamente.
        - Configura QoS (prefetch_count) para controlar a vazão de mensagens.
        - Reenfileira mensagens em caso de exceção; quando a lógica de poison pill
          evitar exceções (mensagem já quarentenada), a mensagem é confirmada (ack).

        Retorna um asyncio.Task para controle externo (cancelamento, tracking).
        """

        async def _consume_loop() -> None:
            while True:
                try:
                    await self.connect()
                    assert self._connection is not None

                    async with self._connection.channel() as channel:
                        await channel.set_qos(prefetch_count=prefetch_count)

                        arguments = None
                        if queue_name in ["janus.knowledge.consolidation", "default"]:
                            arguments = {
                                "x-message-ttl": 24 * 60 * 60 * 1000,  # 24h em ms
                                "x-max-length": 10000,
                            }

                        queue = await channel.declare_queue(
                            queue_name,
                            durable=True,
                            arguments=arguments,
                        )

                        async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
                            async with message.process(requeue=True):
                                try:
                                    body_text = message.body.decode("utf-8")
                                    try:
                                        payload = json.loads(body_text)
                                        # Import interno para evitar ciclos em import
                                        from app.models.schemas import TaskMessage  # noqa

                                        task = TaskMessage(**payload)
                                        await callback(task)
                                    except Exception:
                                        # Se não for JSON válido para TaskMessage, entrega o texto bruto
                                        await callback(body_text)
                                except Exception as e:
                                    logger.error(
                                        "Erro ao processar mensagem",
                                        extra={"queue": queue_name},
                                        exc_info=e,
                                    )
                                    raise

                        await queue.consume(on_message, no_ack=False)
                        logger.info(
                            "Consumidor iniciado",
                            extra={"queue": queue_name, "prefetch": prefetch_count},
                        )

                        # Mantém o consumidor ativo até cancelamento
                        await asyncio.Future()

                except asyncio.CancelledError:
                    logger.info("Consumidor cancelado", extra={"queue": queue_name})
                    break
                except Exception as e:
                    logger.error(
                        "Falha no consumidor; reconectando em 5s",
                        extra={"queue": queue_name},
                        exc_info=e,
                    )
                    await asyncio.sleep(5)

        return asyncio.create_task(_consume_loop())

# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_broker_instance: Optional[MessageBroker] = None

async def initialize_broker():
    """
    Inicializa a instância singleton do MessageBroker.
    """
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = MessageBroker()
        await _broker_instance.connect()

async def close_broker():
    """
    Fecha a conexão da instância singleton.
    """
    if _broker_instance:
        await _broker_instance.close()

async def get_broker() -> MessageBroker:
    """
    Função getter para injeção de dependência.
    """
    if _broker_instance is None:
        await initialize_broker()
    return _broker_instance


# --- Compatibilidade com código legado ---
# Exportar uma referência para a instância singleton (para imports legados)
# NOTA: Esta é uma referência que será None até initialize_broker() ser chamada
message_broker = _broker_instance
