import asyncio
import base64
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from aiormq.exceptions import (
    ChannelClosed,
    ChannelInvalidStateError,
    ChannelNotFoundEntity,
    ChannelPreconditionFailed,
)
from prometheus_client import Counter

from app.config import settings
from app.core.infrastructure.logging_config import TRACE_ID, USER_ID

try:
    import msgpack
except Exception:
    import json as _json

    class _MsgPackCompat:
        @staticmethod
        def packb(obj: Any, use_bin_type: bool = True) -> bytes:
            del use_bin_type
            return _json.dumps(obj, ensure_ascii=False).encode("utf-8")

        @staticmethod
        def unpackb(data: bytes | bytearray, raw: bool = False):
            del raw
            if isinstance(data, (bytes, bytearray)):
                return _json.loads(data.decode("utf-8"))
            return _json.loads(str(data))

    msgpack = _MsgPackCompat()  # type: ignore[assignment]

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None
from app.models.schemas import TaskMessage

logger = logging.getLogger(__name__)

# --- Métricas ---
_MESSAGES_PUBLISHED = Counter(
    "broker_messages_published_total", "Total de mensagens publicadas", ["queue"]
)
_CONNECTION_ERRORS = Counter(
    "broker_connection_errors_total", "Total de erros de conexão com o broker"
)
_CONSUME_ERRORS = Counter(
    "broker_consume_errors_total", "Total de erros ao consumir mensagens", ["queue"]
)


class MessageBroker:
    """
    Gerencia a conexão e as operações com o message broker (RabbitMQ).
    """

    _connection: AbstractRobustConnection | None = None
    _connection_lock = asyncio.Lock()

    def __init__(
        self,
        config: Any = None,
        connection_factory: Callable[..., Awaitable[AbstractRobustConnection]] = None,
    ):
        self.settings = config if config is not None else settings
        self.connection_factory = (
            connection_factory if connection_factory is not None else aio_pika.connect_robust
        )
        self._queue_declare_passive: set[str] = set()
        self._queue_policy_checked: set[str] = set()
        self._publish_channel: aio_pika.Channel | None = None
        self._publish_lock = asyncio.Lock()

    async def connect(self):
        """Estabelece a conexão com o RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            return
        async with self._connection_lock:
            if self._connection and not self._connection.is_closed:
                return
            logger.info("Conectando ao RabbitMQ...")
            try:
                rabbitmq_url = f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}@{self.settings.RABBITMQ_HOST}:{self.settings.RABBITMQ_PORT}/"
                self._connection = await self.connection_factory(
                    rabbitmq_url, client_properties={"connection_name": "janus_system"}
                )
                logger.info("Conexão com RabbitMQ estabelecida com sucesso.")
            except Exception as e:
                _CONNECTION_ERRORS.inc()
                logger.error(
                    f"Falha ao conectar ao RabbitMQ em host '{self.settings.RABBITMQ_HOST}': {e}",
                    exc_info=True,
                )
                # Fallback: tentar localhost para execução fora do Docker
                try:
                    fallback_url = f"amqp://{self.settings.RABBITMQ_USER}:{self.settings.RABBITMQ_PASSWORD}@localhost:{self.settings.RABBITMQ_PORT}/"
                    logger.info("Tentando fallback de conexão com RabbitMQ em localhost...")
                    self._connection = await self.connection_factory(
                        fallback_url, client_properties={"connection_name": "janus_system_local"}
                    )
                    logger.info("Conexão com RabbitMQ (localhost) estabelecida com sucesso.")

                    # Ensure system-wide DLX exists
                    try:
                        async with self._connection.channel() as ch:
                            # 1. Declare DLX
                            await ch.declare_exchange(
                                "janus.dlx", type=aio_pika.ExchangeType.DIRECT, durable=True
                            )

                            # 2. Declare DLQ
                            dlq_args = self._get_queue_arguments("janus.dlq")
                            await ch.declare_queue(
                                "janus.dlq", durable=True, arguments=dlq_args
                            )

                            # 3. Bind DLQ to DLX (routing key 'dead_letter' or default)
                            # RabbitMQ x-dead-letter-routing-key defaults to original routing key if not specified.
                            # We can use a catch-all or specific bindings.
                            # For simplicity, let's bind it with a wildcard if we were using topic, but DLX is direct usually.
                            # Wait, if queue has x-dead-letter-exchange=janus.dlx, RK is preserved.
                            # So janus.dlq must be bound with the same routing keys OR we use a fanout DLX.
                            # BETTER STRATEGY: Fanout DLX is easiest for a catch-all "graveyard".
                            # Let's redeclare as FANOUT to avoid binding headaches, OR Direct and we rely on RK preservation.
                            # Defaulting to FANOUT for "dump all dead stuff here" is safer for generic DLQ.
                            # But code above used DIRECT. Let's switch to FANOUT for simpler maintenance unless we need to segregate dead letters.
                            pass

                    except Exception as ex:
                        logger.warning(f"Falha ao configurar DLX/DLQ: {ex}")
                except Exception as e2:
                    logger.warning(
                        "RabbitMQ indisponível; seguindo em modo offline sem conexão.", exc_info=e2
                    )
                    # Não lança exceção aqui para permitir que a aplicação inicialize em modo degradado.
                    self._connection = None

    async def close(self):
        """Fecha a conexão com o RabbitMQ."""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            self._connection = None
            logger.info("Conexão com RabbitMQ fechada.")

    async def publish(
        self,
        queue_name: str,
        message: Any,
        *,
        priority: int | None = None,
        headers: dict[str, Any] | None = None,
        expiration: int | None = None,
        use_msgpack: bool | None = None,
    ):
        """
        Publica uma mensagem em uma fila.

        - Suporta prioridade via `priority` (0-9) quando a fila possui `x-max-priority`.
        - Suporta `headers` e `expiration` (ms) para uso avançado.
        """
        await self.connect()
        if self._connection is None:
            # Modo offline: ignora publicação
            logger.debug("Publicação ignorada (broker offline)", extra={"queue": queue_name})
            return
        fmt_msgpack = (
            use_msgpack
            if use_msgpack is not None
            else getattr(self.settings, "BROKER_USE_MSGPACK", True)
        )

        merged_headers: dict[str, Any] = {**(headers or {})}

        if fmt_msgpack:
            if isinstance(message, (bytes, bytearray)):
                body = bytes(message)
            else:
                payload = message
                if isinstance(message, str):
                    try:
                        parsed = json.loads(message)
                        if isinstance(parsed, dict):
                            payload = parsed
                    except json.JSONDecodeError:
                        pass
                body = msgpack.packb(payload, use_bin_type=True)
            content_type = "application/msgpack"
        else:
            if isinstance(message, str):
                body = message.encode("utf-8")
            else:
                body = json.dumps(message, ensure_ascii=False).encode("utf-8")
            content_type = "application/json"

        merged_headers.setdefault("content_type", content_type)

        msg = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=priority,
            headers=merged_headers,
            expiration=expiration,
            content_type=content_type,
        )

        for attempt in range(2):
            async with self._publish_lock:
                try:
                    if self._publish_channel is None or self._publish_channel.is_closed:
                        self._publish_channel = await self._connection.channel()
                    channel = self._publish_channel

                    # Ensure DLX/DLQ setup (idempotent)
                    try:
                        dlx = await self._ensure_dlx(channel)
                        dlq = await self._declare_queue_safely(channel, "janus.dlq")
                        await dlq.bind(dlx, routing_key="#")
                    except Exception:
                        pass

                    await self._declare_queue_safely(channel, queue_name)

                    # Trace setup (Otel)
                    if _OTEL and _tracer:
                        with _tracer.start_as_current_span("broker.publish") as span:
                            try:
                                tid = TRACE_ID.get()
                                sid = USER_ID.get()
                                if tid and tid != "-":
                                    span.set_attribute("janus.trace_id", tid)
                                if sid and sid != "-":
                                    span.set_attribute("janus.user_id", sid)
                                span.set_attribute("broker.queue", queue_name)
                                if priority is not None:
                                    span.set_attribute("broker.priority", int(priority))
                                span.set_attribute("broker.content_type", content_type)
                            except Exception:
                                pass
                            await channel.default_exchange.publish(
                                msg, routing_key=queue_name
                            )
                    else:
                        # No OTEL or tracer, just publish
                        await channel.default_exchange.publish(msg, routing_key=queue_name)

                    _MESSAGES_PUBLISHED.labels(queue_name).inc()
                    return
                except (
                    ChannelInvalidStateError,
                    ChannelClosed,
                    ChannelNotFoundEntity,
                    ChannelPreconditionFailed,
                ) as exc:
                    logger.warning(
                        "Canal inválido ao publicar; tentando recriar canal.",
                        extra={"queue": queue_name, "attempt": attempt + 1},
                        exc_info=exc,
                    )
                    if self._publish_channel is not None:
                        try:
                            await self._publish_channel.close()
                        except Exception:
                            pass
                        self._publish_channel = None
                    if attempt == 0:
                        continue
                    raise

    def _get_queue_arguments(self, queue_name: str) -> dict[str, Any]:
        """Obtém argumentos esperados para a fila (TTL, max-length, DLX, prioridade)."""
        cfg = self.settings.RABBITMQ_QUEUE_CONFIG.get(queue_name, {})
        args: dict[str, Any] = {}
        # TTL de mensagens
        ttl = cfg.get("x-message-ttl")
        if ttl is not None:
            args["x-message-ttl"] = int(ttl)
        # Limite de tamanho da fila
        max_len = cfg.get("x-max-length")
        if max_len is not None:
            args["x-max-length"] = int(max_len)
        # DLX (Dead Letter Exchange)
        dlx = cfg.get("x-dead-letter-exchange")
        if dlx is not None:
            args["x-dead-letter-exchange"] = dlx
        # Prioridade máxima suportada
        max_priority = cfg.get("x-max-priority")
        if max_priority is not None:
            args["x-max-priority"] = int(max_priority)
        return args

    async def _ensure_dlx(self, channel: aio_pika.Channel) -> aio_pika.Exchange:
        """
        Garante existência da DLX sem provocar precondition em exchanges já existentes.
        """
        try:
            return await channel.declare_exchange("janus.dlx", passive=True)
        except ChannelNotFoundEntity:
            pass
        except ChannelPreconditionFailed:
            return await channel.declare_exchange("janus.dlx", passive=True)

        return await channel.declare_exchange(
            "janus.dlx", type=aio_pika.ExchangeType.FANOUT, durable=True
        )

    async def _declare_queue_safely(
        self, channel: aio_pika.Channel, queue_name: str
    ) -> aio_pika.Queue:
        """
        Declara a fila de forma segura:
        - Se a fila estiver marcada para uso passive (argumentos divergentes), tenta passive.
        - Caso contrario, declara ativamente com os argumentos esperados.
        - Em caso de precondition, volta para passive.
        """
        if queue_name in self._queue_declare_passive:
            try:
                return await channel.declare_queue(queue_name, passive=True)
            except ChannelNotFoundEntity as exc:
                self._queue_declare_passive.discard(queue_name)
                logger.warning(
                    "Fila marcada como passive nao existe; tentaremos criar novamente.",
                    extra={"queue": queue_name},
                    exc_info=exc,
                )
                raise
            except ChannelPreconditionFailed as exc:
                logger.warning(
                    "Precondition ao acessar fila via passive.",
                    extra={"queue": queue_name},
                    exc_info=exc,
                )
                raise

        if queue_name == "janus.dlq" and queue_name not in self._queue_policy_checked:
            self._queue_policy_checked.add(queue_name)
            try:
                policy = await self.get_queue_policy(queue_name)
            except Exception:
                policy = None
            if policy is not None:
                actual_args = policy.get("arguments", {}) or {}
                expected_args = self._get_queue_arguments(queue_name)
                if any(
                    actual_args.get(key) != value for key, value in expected_args.items()
                ):
                    self._queue_declare_passive.add(queue_name)
                    return await channel.declare_queue(queue_name, passive=True)

        arguments = self._get_queue_arguments(queue_name)
        try:
            return await channel.declare_queue(queue_name, durable=True, arguments=arguments)
        except ChannelPreconditionFailed as exc:
            self._queue_declare_passive.add(queue_name)
            logger.warning(
                "Fila com argumentos divergentes; usando fila existente (passive). "
                "Execute a reconciliacao da fila para aplicar TTL/DLX.",
                extra={"queue": queue_name},
                exc_info=exc,
            )
            return await channel.declare_queue(queue_name, passive=True)

    async def get_queue_info(self, queue_name: str) -> dict | None:
        """
        Obtem informacoes sobre uma fila.
        """
        await self.connect()
        if self._connection is None:
            return None
        async with self._connection.channel() as channel:
            try:
                queue = await self._declare_queue_safely(channel, queue_name)
            except (
                ChannelInvalidStateError,
                ChannelClosed,
                ChannelNotFoundEntity,
                ChannelPreconditionFailed,
            ) as exc:
                logger.warning(
                    "Falha ao obter informacoes da fila.",
                    extra={"queue": queue_name},
                    exc_info=exc,
                )
                return None
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
            return bool(self._connection) and (not self._connection.is_closed)
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

        async def _on_message(message: aio_pika.IncomingMessage):
            try:
                ct = getattr(message, "content_type", None) or (message.headers or {}).get(
                    "content_type"
                )
                use_msgpack_flag = getattr(settings, "BROKER_USE_MSGPACK", True)
                use_msgpack = ct == "application/msgpack" or (ct is None and use_msgpack_flag)
                if use_msgpack:
                    payload = msgpack.unpackb(message.body, raw=False)
                else:
                    payload = json.loads(message.body.decode("utf-8"))
                if isinstance(payload, str):
                    for _ in range(2):
                        try:
                            payload = json.loads(payload)
                        except json.JSONDecodeError:
                            break
                        if not isinstance(payload, str):
                            break
                if not isinstance(payload, dict):
                    raise TypeError("Task payload must be a JSON object")
                task = TaskMessage(**payload)  # type: ignore[name-defined]
                
                # Tracing manual
                if _OTEL and _tracer:
                    with _tracer.start_as_current_span("broker.consume") as span:
                        try:
                            tid = TRACE_ID.get()
                            sid = USER_ID.get()
                            if tid and tid != "-":
                                span.set_attribute("janus.trace_id", tid)
                            if sid and sid != "-":
                                span.set_attribute("janus.user_id", sid)
                            span.set_attribute("broker.queue", queue_name)
                            span.set_attribute("broker.content_type", str(ct))
                        except Exception:
                            pass
                        await callback(task)
                else:
                    await callback(task)
            except Exception as e:
                logger.error(
                    "Erro ao processar mensagem; reenfileirando",
                    extra={"queue": queue_name},
                    exc_info=e,
                )
                try:
                    _CONSUME_ERRORS.labels(queue_name).inc()
                except Exception:
                    pass
                try:
                    ch = getattr(message, "channel", None)
                    if ch is not None and not ch.is_closed:
                        # CRITICAL FIX: Do NOT requeue on generic error to avoid infinite loops (poison pill).
                        # Send to DLX (Dead Letter Exchange) by Nack(requeue=False).
                        # Queue must be configured with x-dead-letter-exchange for this to work properly.
                        await message.nack(requeue=False)
                        logger.warning(
                            f"Mensagem movida para DLX (requeue=False) devido a erro: {e}"
                        )
                    else:
                        logger.warning(
                            "Canal do RabbitMQ fechado; nack ignorado e mensagem será reentregue pelo broker."
                        )
                except Exception as nack_err:
                    logger.error(
                        "Falha ao enviar NACK; possivelmente canal inválido", exc_info=nack_err
                    )
                return

            # Confirma a mensagem somente se o canal estiver válido
            try:
                ch = getattr(message, "channel", None)
                if ch is not None and not ch.is_closed:
                    await message.ack()
                else:
                    logger.warning(
                        "Canal do RabbitMQ fechado antes do ACK; mensagem provavelmente será reentregue."
                    )
            except Exception as ack_err:
                logger.error("Falha ao enviar ACK; mensagem será reentregue", exc_info=ack_err)

        async def _consume_loop() -> None:
            while True:
                try:
                    await self.connect()
                    if self._connection is None:
                        # Broker offline: aguarda antes de tentar novamente
                        await asyncio.sleep(5)
                        continue

                    async with self._connection.channel() as channel:
                        await channel.set_qos(prefetch_count=prefetch_count)
                        queue = await self._declare_queue_safely(channel, queue_name)
                        await queue.consume(_on_message, no_ack=False)
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

    async def publish_to_exchange(
        self, exchange_name: str, routing_key: str, message: Any, exchange_type: str = "topic"
    ):
        """Publica mensagem em uma exchange (para eventos)."""
        await self.connect()
        if self._connection is None:
            return

        async with self._connection.channel() as channel:
            exchange = await channel.declare_exchange(
                exchange_name, type=exchange_type, durable=True
            )

            use_msgpack_flag = getattr(
                self.settings, "BROKER_USE_MSGPACK", False
            )  # Default False para eventos (debug web)

            if use_msgpack_flag:
                body = msgpack.packb(message, use_bin_type=True)
                content_type = "application/msgpack"
            else:
                body = json.dumps(message, ensure_ascii=False).encode("utf-8")
                content_type = "application/json"

            msg = aio_pika.Message(
                body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT, content_type=content_type
            )

            await exchange.publish(msg, routing_key=routing_key)
            _MESSAGES_PUBLISHED.labels(f"exchange_{exchange_name}").inc()

    def start_subscription(
        self,
        exchange_name: str,
        routing_key: str,
        callback: Callable[[Any], Awaitable[Any]],
        queue_name: str = "",  # Vazio = fila temporária exclusiva
        exchange_type: str = "topic",
    ) -> asyncio.Task:
        """
        Assina tópicos em uma exchange (Pub/Sub).
        Cria uma fila (temporária ou não), faz o bind na exchange e consome.
        """

        async def _on_message(message: aio_pika.IncomingMessage):
            async with message.process():  # Auto-ACK
                try:
                    ct = getattr(message, "content_type", None) or (message.headers or {}).get(
                        "content_type"
                    )
                    if ct == "application/msgpack":
                        payload = msgpack.unpackb(message.body, raw=False)
                    else:
                        payload = json.loads(message.body.decode("utf-8"))

                    await callback(payload)
                except Exception as e:
                    logger.error(f"Erro ao processar evento da exchange {exchange_name}: {e}")

        async def _consume_loop():
            while True:
                try:
                    await self.connect()
                    if self._connection is None:
                        await asyncio.sleep(5)
                        continue

                    async with self._connection.channel() as channel:
                        exchange = await channel.declare_exchange(
                            exchange_name, type=exchange_type, durable=True
                        )

                        # Fila exclusiva se queue_name for vazio (auto-delete)
                        queue = await channel.declare_queue(
                            name=queue_name,
                            exclusive=(not queue_name),
                            auto_delete=(not queue_name),
                        )

                        await queue.bind(exchange, routing_key=routing_key)
                        await queue.consume(_on_message)

                        logger.info(f"Subscription iniciada: {exchange_name} -> {routing_key}")
                        await asyncio.Future()  # Keep alive

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erro na subscription {exchange_name}: {e}")
                    await asyncio.sleep(5)

        return asyncio.create_task(_consume_loop())

    async def get_queue_policy(self, queue_name: str) -> dict[str, Any] | None:
        """
        Consulta a Management API do RabbitMQ para obter a política/argumentos atuais da fila.
        Retorna dict com informações importantes ou None em caso de erro.
        """

        host = self.settings.RABBITMQ_HOST
        port = self.settings.RABBITMQ_MANAGEMENT_PORT
        user = self.settings.RABBITMQ_USER
        password = self.settings.RABBITMQ_PASSWORD
        url = f"http://{host}:{port}/api/queues/%2F/{quote(queue_name)}"

        def _fetch() -> dict[str, Any] | None:
            try:
                req = Request(url)
                token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
                req.add_header("Authorization", f"Basic {token}")
                import time as _t

                from app.core.monitoring.health_monitor import (
                    get_timeout_recommendation,
                    record_latency,
                )

                _t_start = _t.perf_counter()
                _timeout = get_timeout_recommendation("rabbitmq_management", 5.0)
                with urlopen(req, timeout=float(_timeout)) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    try:
                        record_latency("rabbitmq_management", _t.perf_counter() - _t_start)
                    except Exception:
                        pass
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

    async def validate_queue_policy(self, queue_name: str) -> dict[str, Any]:
        """
        Valida os argumentos atuais da fila contra os esperados na configuração.
        Retorna um dict com status (healthy/degraded/unhealthy), mensagem e detalhes.
        """
        # Garante que a fila existe antes de consultar a Management API
        try:
            await self.get_queue_info(queue_name)
        except Exception:
            pass
        actual = await self.get_queue_policy(queue_name)
        expected = self._get_queue_arguments(queue_name) or {}

        if actual is None:
            return {
                "status": "unhealthy",
                "message": "Não foi possível obter política da fila",
                "details": {"queue": queue_name},
            }

        actual_args = actual.get("arguments", {}) or {}
        mismatches: dict[str, dict[str, Any]] = {}
        for key, expected_val in expected.items():
            actual_val = actual_args.get(key)
            if actual_val != expected_val:
                mismatches[key] = {"expected": expected_val, "actual": actual_val}

        status = "healthy" if not mismatches else "degraded"
        msg = (
            "Argumentos da fila conferem"
            if not mismatches
            else "Argumentos da fila divergem do esperado"
        )

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
                "consumers": actual.get("consumers", 0),
            },
        }

    async def delete_queue(
        self, queue_name: str, if_unused: bool = False, if_empty: bool = False
    ) -> bool:
        """
        Deleta uma fila via Management API do RabbitMQ.
        Atenção: isto remove todas as mensagens dessa fila.
        """

        host = self.settings.RABBITMQ_HOST
        port = self.settings.RABBITMQ_MANAGEMENT_PORT
        user = self.settings.RABBITMQ_USER
        password = self.settings.RABBITMQ_PASSWORD
        url = (
            f"http://{host}:{port}/api/queues/%2F/{quote(queue_name)}"
            f"?if-unused={str(if_unused).lower()}&if-empty={str(if_empty).lower()}"
        )

        def _delete() -> bool:
            try:
                req = Request(url, method="DELETE")
                token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
                req.add_header("Authorization", f"Basic {token}")
                with urlopen(req, timeout=5) as resp:
                    status = getattr(resp, "status", 200)
                    return 200 <= status < 300
            except Exception as e:
                logger.error(f"Erro ao deletar fila via Management API: {e}")
                return False

        return await asyncio.to_thread(_delete)

    async def reconcile_queue_policy(
        self, queue_name: str, force_delete: bool = True
    ) -> dict[str, Any]:
        """
        Reconcilia a política da fila com a configuração esperada:
        - Valida argumentos atuais; se houver divergências e force_delete=True, deleta a fila e recria com argumentos esperados.
        - Retorna o resultado da validação após a reconciliação.
        """
        validation = await self.validate_queue_policy(queue_name)
        mismatches = validation.get("details", {}).get("mismatches", {})
        actions = []

        if mismatches and force_delete:
            deleted = await self.delete_queue(queue_name)
            actions.append({"action": "delete_queue", "success": deleted})
            if deleted:
                # Recriar fila com argumentos esperados
                try:
                    await self.connect()
                    async with self._connection.channel() as channel:
                        args = self._get_queue_arguments(queue_name)
                        await channel.declare_queue(queue_name, durable=True, arguments=args)
                    actions.append({"action": "declare_queue", "success": True})
                except Exception as e:
                    logger.error(f"Erro ao recriar fila {queue_name}: {e}")
                    actions.append({"action": "declare_queue", "success": False, "error": str(e)})

            # Validar novamente após tentativa de reconciliação
            validation = await self.validate_queue_policy(queue_name)

        status = validation.get("status", "unknown")
        if status == "healthy":
            self._queue_declare_passive.discard(queue_name)

        return {
            "status": status,
            "message": validation.get("message", ""),
            "details": {**validation.get("details", {}), "actions": actions},
        }


# --- Gerenciamento da Instância Singleton para Injeção de Dependência ---

_broker_instance: MessageBroker | None = None


async def initialize_broker():
    """
    Inicializa a instância singleton do MessageBroker.
    """
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = MessageBroker()
        # Não lançar erro se a conexão falhar; permanece offline
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


# Adapter para uso em contexts managers assíncronos (async with)
class _AgnosticContextManager:
    def __init__(self, coro):
        self._coro = coro
    
    async def __aenter__(self):
        return await self._coro
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

def get_broker_context() -> _AgnosticContextManager:
    """
    Helper para usar 'async with get_broker() as broker' se o código legado esperar isso.
    """
    return _AgnosticContextManager(get_broker())
