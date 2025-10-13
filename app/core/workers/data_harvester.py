import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from prometheus_client import Counter, Gauge, Histogram

from app.core.infrastructure.filesystem_manager import write_file
from app.core.infrastructure.resilience import resilient, CircuitBreaker, CircuitOpenError
from app.core.memory.memory_core import memory_core

logger = logging.getLogger(__name__)

TRAINING_DATA_FILE = "training_data.jsonl"

# Metrics
_HARV_ITEMS = Counter(
    "harvester_items_total", "Itens coletados pelo harvester", ["source", "outcome"]
)
_HARV_ERRORS = Counter(
    "harvester_errors_total", "Erros por conector", ["source", "exception_type"]
)
_HARV_LAT = Histogram(
    "harvester_fetch_latency_seconds", "Latência por coleta (fetch)", ["source", "outcome"]
)
_HARV_QUEUE_DEPTH = Gauge(
    "harvester_queue_depth", "Profundidade da fila de backpressure"
)
_HARV_DEDUP = Counter(
    "harvester_dedup_total", "Deduplicações (hits/misses)", ["outcome"]  # hit/miss
)
_HARV_PRODUCER_ERRORS = Counter(
    "harvester_producer_errors_consecutive", "Erros consecutivos no producer"
)
_HARV_CONSUMER_ERRORS = Counter(
    "harvester_consumer_errors_consecutive", "Erros consecutivos no consumer"
)

_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

# Constantes
_MAX_CONSECUTIVE_PRODUCER_ERRORS = 10
_MAX_CONSECUTIVE_CONSUMER_ERRORS = 10
_FETCH_TIMEOUT = 30  # segundos


@runtime_checkable
class Connector(Protocol):
    name: str

    def fetch_batch(self, limit: int = 50) -> List[Dict[str, Any]]:  # pragma: no cover - interface
        """
        Fetch a batch of items from the data source.

        Args:
            limit (int): The maximum number of items to fetch in this batch. Defaults to 50.

        Returns:
            List[Dict[str, Any]]: A list of items, each represented as a dictionary.
        """
        ...


@dataclass
class _Schedule:
    next_run: float
    jitter_s: float
    window_s: float


class DedupLRU:
    """Cache LRU para deduplicação de itens."""

    def __init__(self, max_items: int = 5000, ttl_seconds: int = 3600):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, float] = OrderedDict()

    def _prune(self) -> None:
        """Remove itens expirados e aplica limite LRU."""
        now = time.time()
        for k in list(self._store.keys()):
            if now - self._store[k] > self.ttl_seconds:
                self._store.pop(k, None)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def add_if_new(self, key: str) -> bool:
        """
        Adiciona chave se nova.

        Args:
            key: Chave a ser verificada/adicionada

        Returns:
            True se é nova, False se já existe
        """
        self._prune()
        if key in self._store:
            self._store.move_to_end(key)
            _HARV_DEDUP.labels("hit").inc()
            return False
        self._store[key] = time.time()
        _HARV_DEDUP.labels("miss").inc()
        return True


class Harvester:
    """Sistema de coleta assíncrona de dados com resiliência e observabilidade."""

    def __init__(self, queue_maxsize: int = 500, schedule_window_s: int = 60, batch_size: int = 50):
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=queue_maxsize)
        self._connectors: Dict[str, Connector] = {}
        self._schedules: Dict[str, _Schedule] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._stop = asyncio.Event()
        self._producer_task: Optional[asyncio.Task] = None
        self._consumer_task: Optional[asyncio.Task] = None
        self._batch_size = batch_size
        self._window_s = schedule_window_s
        self._dedup = DedupLRU()
        self._producer_consecutive_errors = 0
        self._consumer_consecutive_errors = 0

    def register(self, connector: Connector, *, window_s: Optional[int] = None, jitter_s: float = 5.0):
        """
        Registra um conector de dados.

        Args:
            connector: Conector a ser registrado
            window_s: Janela de tempo entre coletas (segundos)
            jitter_s: Jitter aleatório para evitar sincronização
        """
        if not hasattr(connector, 'name') or not connector.name:
            raise ValueError("Connector deve ter atributo 'name' não vazio")

        if not hasattr(connector, 'fetch_batch') or not callable(connector.fetch_batch):
            raise ValueError("Connector deve implementar método 'fetch_batch'")

        self._connectors[connector.name] = connector
        now = time.time()
        w = float(window_s or self._window_s)
        self._schedules[connector.name] = _Schedule(next_run=now + 1.0, jitter_s=jitter_s, window_s=w)
        self._locks[connector.name] = asyncio.Lock()
        logger.info({"event": "harvester_connector_registered", "name": connector.name, "window_s": w})

    async def start(self):
        """Inicia o harvester (producer e consumer loops)."""
        if self._producer_task:
            logger.warning("Harvester já está rodando.")
            return

        self._stop.clear()
        self._producer_task = asyncio.create_task(self._producer_loop())
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        logger.info("Harvester started")

    async def stop(self):
        """Para o harvester gracefully."""
        logger.info("Harvester stopping...")
        self._stop.set()

        for t in (self._producer_task, self._consumer_task):
            if t and not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass

        self._producer_task = None
        self._consumer_task = None
        logger.info("Harvester stopped")

    async def _producer_loop(self):
        """Loop de produção que coleta dados dos conectores."""
        logger.info("Producer loop iniciado")

        while not self._stop.is_set():
            try:
                _HARV_QUEUE_DEPTH.set(self.queue.qsize())
                now = time.time()

                for name, conn in list(self._connectors.items()):
                    if self._stop.is_set():
                        break

                    sched = self._schedules.get(name)
                    if not sched or now < sched.next_run:
                        continue

                    # rate window: set next_run with jitter
                    import random
                    jitter = random.uniform(0, min(sched.jitter_s, sched.window_s))
                    sched.next_run = now + sched.window_s + jitter

                    lock = self._locks[name]
                    if lock.locked():
                        logger.debug(f"Conector '{name}' ainda processando. Pulando.")
                        continue

                    # Cria task para fetch assíncrono
                    asyncio.create_task(self._fetch_and_enqueue(conn))

                # Reset contador de erros em ciclo bem-sucedido
                self._producer_consecutive_errors = 0
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                logger.info("Producer loop cancelado")
                break

            except Exception as e:
                self._producer_consecutive_errors += 1
                _HARV_PRODUCER_ERRORS.inc()

                logger.error(
                    f"Erro no producer loop ({self._producer_consecutive_errors}/"
                    f"{_MAX_CONSECUTIVE_PRODUCER_ERRORS}): {e}",
                    exc_info=True
                )

                if self._producer_consecutive_errors >= _MAX_CONSECUTIVE_PRODUCER_ERRORS:
                    logger.critical(
                        f"Producer atingiu limite de {_MAX_CONSECUTIVE_PRODUCER_ERRORS} erros consecutivos. "
                        f"Encerrando."
                    )
                    self._stop.set()
                    break

                # Backoff exponencial
                backoff = min(60, 2 ** self._producer_consecutive_errors)
                logger.warning(f"Producer aguardando {backoff}s antes de retry...")
                await asyncio.sleep(backoff)

        logger.info("Producer loop encerrado")

    def _hash_item(self, item: Dict[str, Any]) -> str:
        """
        Gera hash único para um item.

        Args:
            item: Item a ser hasheado

        Returns:
            Hash SHA256 do item
        """
        try:
            raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
        except Exception:
            raw = str(item)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _fetch_and_enqueue(self, connector: Connector):
        """
        Coleta dados de um conector e enfileira itens.

        Args:
            connector: Conector de dados
        """
        name = connector.name
        lock = self._locks.get(name)

        if not lock:
            logger.error(f"Lock não encontrado para conector '{name}'")
            return

        async with lock:
            start = time.perf_counter()

            try:
                # Check if connector has async method
                if hasattr(connector, 'fetch_batch_async'):
                    # Use async method directly
                    wrapped_async = resilient(
                        max_attempts=3,
                        initial_backoff=0.25,
                        max_backoff=2.0,
                        circuit_breaker=_CB,
                        retry_on=(Exception,),
                        operation_name=f"harvest_fetch_{name}",
                    )(connector.fetch_batch_async)

                    items = await asyncio.wait_for(
                        wrapped_async(self._batch_size),
                        timeout=_FETCH_TIMEOUT
                    )
                else:
                    # Fallback to sync method in executor
                    wrapped = resilient(
                        max_attempts=3,
                        initial_backoff=0.25,
                        max_backoff=2.0,
                        circuit_breaker=_CB,
                        retry_on=(Exception,),
                        operation_name=f"harvest_fetch_{name}",
                    )(connector.fetch_batch)

                    items = await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(None, wrapped, self._batch_size),
                        timeout=_FETCH_TIMEOUT
                    )

                if not items:
                    _HARV_LAT.labels(name, "empty").observe(time.perf_counter() - start)
                    logger.debug(f"Conector '{name}' retornou 0 itens")
                    return

                accepted = 0
                for it in items:
                    if self._stop.is_set():
                        break

                    key = self._hash_item(it)
                    if not self._dedup.add_if_new(key):
                        continue

                    if self.queue.full():
                        _HARV_ITEMS.labels(name, "dropped_backpressure").inc()
                        logger.warning(f"Fila cheia. Item de '{name}' descartado (backpressure).")
                        continue

                    await self.queue.put(it)
                    accepted += 1

                outcome = "success" if accepted > 0 else "dedup_all"
                _HARV_ITEMS.labels(name, outcome).inc(accepted or 1)
                _HARV_LAT.labels(name, "success").observe(time.perf_counter() - start)

                logger.info(f"Conector '{name}': {accepted}/{len(items)} itens enfileirados.")

            except asyncio.TimeoutError:
                _HARV_ERRORS.labels(name, "TimeoutError").inc()
                _HARV_LAT.labels(name, "timeout").observe(time.perf_counter() - start)
                logger.error(f"Timeout ao coletar de '{name}' após {_FETCH_TIMEOUT}s")

            except CircuitOpenError as e:
                _HARV_ERRORS.labels(name, "CircuitOpenError").inc()
                _HARV_LAT.labels(name, "circuit_open").observe(time.perf_counter() - start)
                logger.error(f"Circuit breaker aberto para '{name}': {e}")

            except Exception as e:
                _HARV_ERRORS.labels(name, type(e).__name__).inc()
                _HARV_LAT.labels(name, "error").observe(time.perf_counter() - start)
                logger.error(
                    {"event": "harvest_fetch_error", "source": name, "error": str(e)},
                    exc_info=True
                )

    async def _consumer_loop(self):
        """Loop de consumo que processa itens da fila."""
        logger.info("Consumer loop iniciado")

        while not self._stop.is_set():
            try:
                # Timeout para permitir verificação de _stop
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                _HARV_QUEUE_DEPTH.set(self.queue.qsize())

                # Processa item
                try:
                    await self._process_item(item)
                    self._consumer_consecutive_errors = 0  # Reset em sucesso
                except Exception as e:
                    logger.error(f"Erro ao processar item: {e}", exc_info=True)
                    # Não incrementa erro consecutivo pois é erro de item individual

            except asyncio.CancelledError:
                logger.info("Consumer loop cancelado")
                break

            except Exception as e:
                self._consumer_consecutive_errors += 1
                _HARV_CONSUMER_ERRORS.inc()

                logger.error(
                    f"Erro no consumer loop ({self._consumer_consecutive_errors}/"
                    f"{_MAX_CONSECUTIVE_CONSUMER_ERRORS}): {e}",
                    exc_info=True
                )

                if self._consumer_consecutive_errors >= _MAX_CONSECUTIVE_CONSUMER_ERRORS:
                    logger.critical(
                        f"Consumer atingiu limite de {_MAX_CONSECUTIVE_CONSUMER_ERRORS} erros consecutivos. "
                        f"Encerrando."
                    )
                    self._stop.set()
                    break

                # Backoff exponencial
                backoff = min(60, 2 ** self._consumer_consecutive_errors)
                logger.warning(f"Consumer aguardando {backoff}s antes de retry...")
                await asyncio.sleep(backoff)

        logger.info("Consumer loop encerrado")

    async def _process_item(self, item: Dict[str, Any]):
        """
        Processa um item coletado.

        Args:
            item: Item a ser processado
        """
        try:
            prompt = f"Contexto: {json.dumps(item.get('metadata', {}), ensure_ascii=False)}"
            completion = item.get("content") or ""

            if completion:
                jsonl = json.dumps({"prompt": prompt, "completion": completion}, ensure_ascii=False)

                # Em DRY_RUN, write_file apenas loga
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    write_file,
                    TRAINING_DATA_FILE,
                    jsonl + "\n",
                    True  # overwrite
                )
        except Exception as e:
            logger.warning(f"Erro ao processar item para treinamento: {e}")


# Default connector: read from episodic memory as a source of supervised examples
class MemoryConnector:
    """Conector que extrai dados da memória episódica."""
    name = "memory"

    def fetch_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Coleta experiências da memória (versão síncrona - wrapper).

        Args:
            limit: Número máximo de experiências

        Returns:
            Lista de experiências
        """
        try:
            # Cria um event loop se necessário (para compatibilidade sync)
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                # Se já há um loop rodando, agenda a corrotina
                future = asyncio.ensure_future(self.fetch_batch_async(limit))
                return loop.run_until_complete(future)
            except RuntimeError:
                # Não há loop rodando, cria um novo
                return asyncio.run(self.fetch_batch_async(limit))
        except Exception as e:
            logger.error(f"Erro ao coletar de MemoryConnector (sync): {e}")
            return []

    async def fetch_batch_async(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Coleta experiências da memória (versão async).

        Args:
            limit: Número máximo de experiências

        Returns:
            Lista de experiências
        """
        try:
            results = await memory_core.arecall(query="experiência do agente", n_results=limit)
            return results or []
        except Exception as e:
            logger.error(f"Erro ao coletar de MemoryConnector: {e}")
            return []

# Singleton harvester
harvester = Harvester()

# Registro seguro do conector padrão
try:
    harvester.register(MemoryConnector(), window_s=120)
except Exception as e:
    logger.error(f"Falha ao registrar MemoryConnector: {e}")


# Backwards-compatible one-shot export remains available
async def harvest_data_for_training(limit: int = 100) -> dict:
    """
    Coleta experiências da memória episódica e as formata num ficheiro
    JSONL, adequado para o fine-tuning de modelos de linguagem.

    Args:
        limit: Número máximo de experiências a coletar

    Returns:
        Dicionário com resultado da operação
    """
    logger.info(f"Iniciando a coleta de dados de {limit} experiências para treino.")

    try:
        experiences = await memory_core.arecall(query="experiência do agente", n_results=limit)

        if not experiences:
            summary = "Nenhuma experiência encontrada para a coleta."
            logger.warning(summary)
            return {"message": "Coleta de dados concluída.", "summary": summary}

        training_examples = []
        for exp in experiences:
            try:
                if exp.get('content') and exp.get('metadata'):
                    prompt = f"Contexto: {json.dumps(exp['metadata'], ensure_ascii=False)}"
                    completion = exp['content']
                    training_examples.append({"prompt": prompt, "completion": completion})
            except Exception as e:
                logger.warning(f"Erro ao processar experiência {exp.get('id', '?')}: {e}")
                continue

        if not training_examples:
            summary = "Experiências recuperadas não continham dados suficientes para criar exemplos de treino."
            logger.warning(summary)
            return {"message": "Coleta de dados concluída.", "summary": summary}

        jsonl_content = "\n".join(json.dumps(ex, ensure_ascii=False) for ex in training_examples)
        write_status = write_file(TRAINING_DATA_FILE, jsonl_content)

        logger.info(write_status)

        summary = (
            f"Coleta de dados concluída. {len(training_examples)} exemplos de treino "
            f"foram guardados em '{TRAINING_DATA_FILE}'."
        )
        logger.info(summary)

        return {"message": "Coleta de dados bem-sucedida.", "summary": summary}

    except Exception as e:
        logger.error(f"Erro crítico ao coletar dados para treinamento: {e}", exc_info=True)
        return {
            "message": "Erro na coleta de dados.",
            "summary": f"Falha: {str(e)}"
        }
