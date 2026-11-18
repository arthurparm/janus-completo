"""
Poison Pill Handler para gestão robusta de mensagens/tarefas problemáticas (Sprint 12).

Implementa detecção e isolamento de "poison pills" - mensagens que causam
falhas repetidas e podem travar o sistema.
"""
import structlog
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from prometheus_client import Counter, Gauge

logger = structlog.get_logger(__name__)

# --- Métricas ---
POISON_PILL_DETECTED = Counter(
    "poison_pill_detected_total", "Total de poison pills detectadas", ["queue", "reason"]
)

POISON_PILL_QUARANTINED = Counter(
    "poison_pill_quarantined_total", "Total de poison pills colocadas em quarentena", ["queue"]
)

POISON_PILL_IN_QUARANTINE = Gauge(
    "poison_pill_in_quarantine", "Número de poison pills atualmente em quarentena", ["queue"]
)


@dataclass
class FailureRecord:
    """Registro de falha de uma mensagem/tarefa."""

    message_id: str
    queue: str
    failure_count: int = 0
    first_failure: datetime = field(default_factory=datetime.now)
    last_failure: datetime = field(default_factory=datetime.now)
    error_types: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)

    def add_failure(self, error_type: str, error_message: str):
        """Adiciona uma nova falha ao registro."""
        self.failure_count += 1
        self.last_failure = datetime.now()
        self.error_types.append(error_type)
        self.error_messages.append(error_message)


@dataclass
class QuarantinedMessage:
    """Mensagem em quarentena."""

    message_id: str
    queue: str
    content: Any
    reason: str
    failure_record: FailureRecord
    quarantined_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class PoisonPillHandler:
    """
    Gerenciador de poison pills para detecção e isolamento de mensagens problemáticas.

    Estratégias de detecção:
    1. Falhas repetidas (threshold configurável)
    2. Falhas consecutivas sem sucesso
    3. Tipos de erro persistentes
    4. Timeout patterns
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        consecutive_failure_threshold: int = 5,
        quarantine_duration_hours: int = 24,
        enable_auto_retry: bool = False,
    ):
        """
        Inicializa o PoisonPillHandler.

        Args:
            failure_threshold: Número de falhas antes de considerar poison pill
            consecutive_failure_threshold: Falhas consecutivas sem sucesso
            quarantine_duration_hours: Tempo em horas que mensagem fica em quarentena
            enable_auto_retry: Se True, tenta reprocessar após quarentena
        """
        self.failure_threshold = failure_threshold
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.quarantine_duration = timedelta(hours=quarantine_duration_hours)
        self.enable_auto_retry = enable_auto_retry

        # Rastreamento de falhas
        self.failure_records: dict[str, FailureRecord] = {}

        # Quarentena
        self.quarantined: dict[str, QuarantinedMessage] = {}

        # Contadores por fila
        self.queue_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total_failures": 0, "total_quarantined": 0, "consecutive_failures": 0}
        )

        logger.info("log_info", message=f"PoisonPillHandler inicializado: "
            f"threshold={failure_threshold}, "
            f"consecutive_threshold={consecutive_failure_threshold}"
        )

    def record_failure(
        self, message_id: str, queue: str, error: Exception, content: Any | None = None
    ) -> bool:
        """
        Registra uma falha de processamento.

        Args:
            message_id: ID único da mensagem
            queue: Nome da fila/queue
            error: Exceção que ocorreu
            content: Conteúdo da mensagem (opcional)

        Returns:
            True se a mensagem foi identificada como poison pill
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Criar ou atualizar registro
        if message_id not in self.failure_records:
            self.failure_records[message_id] = FailureRecord(message_id=message_id, queue=queue)

        record = self.failure_records[message_id]
        record.add_failure(error_type, error_message)

        # Atualizar stats da fila
        self.queue_stats[queue]["total_failures"] += 1
        self.queue_stats[queue]["consecutive_failures"] += 1

        logger.warning("log_warning", message=f"Falha registrada para mensagem {message_id} na fila {queue}: "
            f"count={record.failure_count}, error={error_type}"
        )

        # Verificar se é poison pill
        is_poison = self._check_poison_pill(record)

        if is_poison:
            self._quarantine_message(
                record, content, f"Threshold atingido: {record.failure_count} falhas"
            )
            POISON_PILL_DETECTED.labels(queue=queue, reason="failure_threshold").inc()

        return is_poison

    def record_success(self, message_id: str, queue: str):
        """
        Registra um processamento bem-sucedido.

        Reseta contadores de falhas consecutivas.
        """
        # Remover registro de falha se existir
        if message_id in self.failure_records:
            del self.failure_records[message_id]

        # Resetar falhas consecutivas
        self.queue_stats[queue]["consecutive_failures"] = 0

        logger.debug("log_debug", message=f"Sucesso registrado para mensagem {message_id} na fila {queue}")

    def _check_poison_pill(self, record: FailureRecord) -> bool:
        """
        Verifica se uma mensagem deve ser considerada poison pill.

        Critérios:
        1. Atingiu o threshold de falhas
        2. Tem o mesmo tipo de erro repetidamente
        3. Falhas estão espaçadas (não é problema temporário)
        """
        # Critério 1: Threshold simples
        if record.failure_count >= self.failure_threshold:
            return True

        # Critério 2: Mesmo tipo de erro persistente
        if len(record.error_types) >= 3:
            unique_errors = set(record.error_types[-3:])
            if len(unique_errors) == 1:  # Mesmo erro 3 vezes seguidas
                return True

        # Critério 3: Falhas persistentes ao longo do tempo
        time_span = record.last_failure - record.first_failure
        if record.failure_count >= 2 and time_span.total_seconds() > 300:  # 5 minutos
            return True

        return False

    def _quarantine_message(self, record: FailureRecord, content: Any | None, reason: str):
        """
        Coloca uma mensagem em quarentena.
        """
        quarantined_msg = QuarantinedMessage(
            message_id=record.message_id,
            queue=record.queue,
            content=content,
            reason=reason,
            failure_record=record,
        )

        self.quarantined[record.message_id] = quarantined_msg
        self.queue_stats[record.queue]["total_quarantined"] += 1

        POISON_PILL_QUARANTINED.labels(queue=record.queue).inc()
        POISON_PILL_IN_QUARANTINE.labels(queue=record.queue).inc()

        logger.error("log_error", message=f"Mensagem {record.message_id} colocada em QUARENTENA: "
            f"queue={record.queue}, reason={reason}, failures={record.failure_count}"
        )

    def is_quarantined(self, message_id: str) -> bool:
        """Verifica se uma mensagem está em quarentena."""
        return message_id in self.quarantined

    def get_quarantined_messages(self, queue: str | None = None) -> list[QuarantinedMessage]:
        """
        Retorna mensagens em quarentena.

        Args:
            queue: Filtrar por fila específica (opcional)
        """
        messages = list(self.quarantined.values())

        if queue:
            messages = [msg for msg in messages if msg.queue == queue]

        return messages

    def release_from_quarantine(
        self, message_id: str, allow_retry: bool = False
    ) -> QuarantinedMessage | None:
        """
        Remove uma mensagem da quarentena.

        Args:
            message_id: ID da mensagem
            allow_retry: Se True, permite reprocessamento

        Returns:
            A mensagem removida ou None se não encontrada
        """
        if message_id not in self.quarantined:
            return None

        msg = self.quarantined.pop(message_id)

        # Remover registro de falha se não for para reprocessar
        if not allow_retry and message_id in self.failure_records:
            del self.failure_records[message_id]

        POISON_PILL_IN_QUARANTINE.labels(queue=msg.queue).dec()

        logger.info("log_info", message=f"Mensagem {message_id} LIBERADA da quarentena: "
            f"queue={msg.queue}, allow_retry={allow_retry}"
        )

        return msg

    def cleanup_expired_quarantine(self) -> int:
        """
        Remove mensagens expiradas da quarentena.

        Returns:
            Número de mensagens removidas
        """
        now = datetime.now()
        expired_ids = []

        for msg_id, msg in self.quarantined.items():
            if now - msg.quarantined_at > self.quarantine_duration:
                expired_ids.append(msg_id)

        for msg_id in expired_ids:
            msg = self.release_from_quarantine(msg_id, allow_retry=self.enable_auto_retry)
            if msg:
                logger.info("log_info", message=f"Quarentena expirada para {msg_id}: "
                    f"duration={(now - msg.quarantined_at).total_seconds():.0f}s"
                )

        return len(expired_ids)

    def get_failure_stats(self, queue: str | None = None) -> dict[str, Any]:
        """
        Retorna estatísticas de falhas.

        Args:
            queue: Filtrar por fila específica (opcional)
        """
        if queue:
            return {
                "queue": queue,
                **self.queue_stats[queue],
                "quarantined_count": len(
                    [m for m in self.quarantined.values() if m.queue == queue]
                ),
            }

        return {
            "total_tracked_messages": len(self.failure_records),
            "total_quarantined": len(self.quarantined),
            "by_queue": dict(self.queue_stats),
            "quarantine_duration_hours": self.quarantine_duration.total_seconds() / 3600,
        }

    def get_health_status(self) -> dict[str, Any]:
        """
        Retorna o status de saúde do sistema de poison pill handling.
        """
        total_quarantined = len(self.quarantined)
        total_tracked = len(self.failure_records)

        # Determinar status
        if total_quarantined == 0:
            status = "healthy"
        elif total_quarantined < 5:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "total_quarantined": total_quarantined,
            "total_tracked_failures": total_tracked,
            "queues_affected": len(self.queue_stats),
            "failure_threshold": self.failure_threshold,
            "consecutive_threshold": self.consecutive_failure_threshold,
        }


# --- Instância Global ---
_poison_pill_handler: PoisonPillHandler | None = None


def get_poison_pill_handler() -> PoisonPillHandler:
    """Obtém a instância global do PoisonPillHandler."""
    global _poison_pill_handler
    if _poison_pill_handler is None:
        _poison_pill_handler = PoisonPillHandler()
    return _poison_pill_handler


# --- Decorador para Proteção Automática ---


def protect_against_poison_pills(queue_name: str, extract_message_id: Callable[[Any], str]):
    """
    Decorador para proteger funções de processamento contra poison pills.

    Args:
        queue_name: Nome da fila/queue
        extract_message_id: Função para extrair message_id dos argumentos

    Usage:
        @protect_against_poison_pills(
            queue_name="tasks",
            extract_message_id=lambda task: task.id
        )
        async def process_task(task: Task):
            # processar task
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            handler = get_poison_pill_handler()

            # Extrair message_id
            try:
                message_id = extract_message_id(args[0] if args else kwargs)
            except Exception as e:
                logger.error("log_error", message=f"Erro ao extrair message_id: {e}")
                return await func(*args, **kwargs)

            # Verificar se está em quarentena
            if handler.is_quarantined(message_id):
                logger.warning("log_warning", message=f"Mensagem {message_id} está em QUARENTENA, pulando processamento")
                return None

            # Tentar processar
            try:
                result = await func(*args, **kwargs)
                handler.record_success(message_id, queue_name)
                return result
            except Exception as e:
                # Registrar falha
                content = args[0] if args else kwargs
                handler.record_failure(message_id, queue_name, e, content)
                raise

        return wrapper

    return decorator
