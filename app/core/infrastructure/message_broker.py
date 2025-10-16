import asyncio
import logging
import json
import base64
from typing import Optional, Callable, Awaitable, Any, Dict
from urllib.parse import quote
from urllib.request import Request, urlopen

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
            arguments = self._get_queue_arguments(queue_name)
            await channel.declare_queue(queue_name, durable=True, arguments=arguments)
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
            arguments = self._get_queue_arguments(queue_name)
            queue = await channel.declare_queue(queue_name, durable=True, arguments=arguments)
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
                        arguments = self._get_queue_arguments(queue_name)
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

    # --- Utilitários / Management API ---

    def _get_queue_arguments(self, queue_name: str) -> Optional[Dict[str, int]]:
        """
        Obtém os argumentos esperados para a fila a partir da configuração.
        Retorna None se não houver configuração específica.
        """
        try:
            args = settings.RABBITMQ_QUEUE_CONFIG.get(queue_name)
            return args or None
        except Exception:
            return None

    async def get_queue_policy(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        Consulta a Management API do RabbitMQ para obter a política/argumentos atuais da fila.
        Retorna dict com informações importantes ou None em caso de erro.
        """
        host = settings.RABBITMQ_HOST
        port = settings.RABBITMQ_MANAGEMENT_PORT
        user = settings.RABBITMQ_USER
        password = settings.RABBITMQ_PASSWORD
        url = f"http://{host}:{port}/api/queues/%2F/{quote(queue_name)}"

        def _fetch() -> Optional[Dict[str, Any]]:
            try:
                req = Request(url)
                token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
                req.add_header("Authorization", f"Basic {token}")
                with urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "name": data.get("name"),
                        "durable": data.get("durable", True),
                        "auto_delete": data.get("auto_delete", False),
                        "messages": data.get("messages", 0),
                        "consumers": data.get("consumers", 0),
                        "arguments": data.get("arguments", {}) or {},
                    }
            except Exception as e:
                logger.error(f"Erro ao consultar Management API do RabbitMQ: {e}")
                return None

        return await asyncio.to_thread(_fetch)

    async def validate_queue_policy(self, queue_name: str) -> Dict[str, Any]:
        """
        Valida os argumentos atuais da fila contra os esperados na configuração.
        Retorna um dict com status (healthy/degraded/unhealthy), mensagem e detalhes.
        """
        actual = await self.get_queue_policy(queue_name)
        expected = self._get_queue_arguments(queue_name) or {}

        if actual is None:
            return {
                "status": "unhealthy",
                "message": "Não foi possível obter política da fila",
                "details": {"queue": queue_name}
            }

        actual_args = actual.get("arguments", {}) or {}
        mismatches: Dict[str, Dict[str, Any]] = {}
        for key, expected_val in expected.items():
            actual_val = actual_args.get(key)
            if actual_val != expected_val:
                mismatches[key] = {"expected": expected_val, "actual": actual_val}

        status = "healthy" if not mismatches else "degraded"
        msg = "Argumentos da fila conferem" if not mismatches else "Argumentos da fila divergem do esperado"

        return {
            "status": status,
            "message": msg,
            "details": {
                "queue": queue_name,
                "expected": expected,
                "actual": actual_args,
                "mismatches": mismatches,
                "durable": actual.get("durable", True),
                "messages": actual.get("messages", 0),
                "consumers": actual.get("consumers", 0)
            }
        }

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
