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
from app.models.schemas import TaskMessage

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
                logger.error(f"Falha ao conectar ao RabbitMQ em host '{settings.RABBITMQ_HOST}': {e}", exc_info=True)
                # Fallback: tentar localhost para execução fora do Docker
                try:
                    fallback_url = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@localhost:{settings.RABBITMQ_PORT}/"
                    logger.info("Tentando fallback de conexão com RabbitMQ em localhost...")
                    self._connection = await aio_pika.connect_robust(
                        fallback_url,
                        client_properties={"connection_name": "janus_system_local"}
                    )
                    logger.info("Conexão com RabbitMQ (localhost) estabelecida com sucesso.")
                except Exception as e2:
                    logger.warning("RabbitMQ indisponível; seguindo em modo offline sem conexão.", exc_info=e2)
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
        message: str,
        *,
        priority: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
        expiration: Optional[int] = None,
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
        async with self._connection.channel() as channel:
            arguments = self._get_queue_arguments(queue_name)
            await channel.declare_queue(queue_name, durable=True, arguments=arguments)
            msg = aio_pika.Message(
                body=message.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                priority=priority,
                headers=headers,
                expiration=expiration,
            )
            await channel.default_exchange.publish(msg, routing_key=queue_name)
            _MESSAGES_PUBLISHED.labels(queue_name).inc()

    def _get_queue_arguments(self, queue_name: str) -> Dict[str, Any]:
        """Obtém argumentos esperados para a fila (TTL, max-length, DLX, prioridade)."""
        cfg = settings.RABBITMQ_QUEUE_CONFIG.get(queue_name, {})
        args: Dict[str, Any] = {}
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

    async def get_queue_info(self, queue_name: str) -> Optional[dict]:
        """
        Obtém informações sobre uma fila.
        """
        await self.connect()
        if self._connection is None:
            return None
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
                payload = json.loads(message.body.decode("utf-8"))
                # Converte para TaskMessage e processa
                task = TaskMessage(**payload)  # type: ignore[name-defined]
                await callback(task)
            except Exception as e:
                logger.error("Erro ao processar mensagem; reenfileirando", exc_info=e)
                try:
                    ch = getattr(message, "channel", None)
                    if ch is not None and not ch.is_closed:
                        message.nack(requeue=True)
                    else:
                        logger.warning("Canal do RabbitMQ fechado; nack ignorado e mensagem será reentregue pelo broker.")
                except Exception as nack_err:
                    logger.error("Falha ao enviar NACK; possivelmente canal inválido", exc_info=nack_err)
                return

            # Confirma a mensagem somente se o canal estiver válido
            try:
                ch = getattr(message, "channel", None)
                if ch is not None and not ch.is_closed:
                    message.ack()
                else:
                    logger.warning("Canal do RabbitMQ fechado antes do ACK; mensagem provavelmente será reentregue.")
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
                        arguments = self._get_queue_arguments(queue_name)
                        queue = await channel.declare_queue(
                            queue_name,
                            durable=True,
                            arguments=arguments,
                        )
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

    async def delete_queue(self, queue_name: str, if_unused: bool = False, if_empty: bool = False) -> bool:
        """
        Deleta uma fila via Management API do RabbitMQ.
        Atenção: isto remove todas as mensagens dessa fila.
        """
        host = settings.RABBITMQ_HOST
        port = settings.RABBITMQ_MANAGEMENT_PORT
        user = settings.RABBITMQ_USER
        password = settings.RABBITMQ_PASSWORD
        url = (
            f"http://{host}:{port}/api/queues/%2F/{quote(queue_name)}"
            f"?if-unused={str(if_unused).lower()}&if-empty={str(if_empty).lower()}"
        )

        def _delete() -> bool:
            try:
                req = Request(url, method="DELETE")
                token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
                req.add_header("Authorization", f"Basic {token}")
                with urlopen(req, timeout=5) as resp:
                    status = getattr(resp, "status", 200)
                    return 200 <= status < 300
            except Exception as e:
                logger.error(f"Erro ao deletar fila via Management API: {e}")
                return False

        return await asyncio.to_thread(_delete)

    async def reconcile_queue_policy(self, queue_name: str, force_delete: bool = True) -> Dict[str, Any]:
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

        return {
            "status": validation.get("status", "unknown"),
            "message": validation.get("message", ""),
            "details": {
                **validation.get("details", {}),
                "actions": actions
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
