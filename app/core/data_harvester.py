import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from prometheus_client import Counter, Gauge, Histogram

from app.core.filesystem_manager import write_file
from app.core.memory_core import memory_core
from app.core.resilience import resilient, CircuitBreaker

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

_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


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
    def __init__(self, max_items: int = 5000, ttl_seconds: int = 3600):
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._store: OrderedDict[str, float] = OrderedDict()

    def _prune(self) -> None:
        now = time.time()
        for k in list(self._store.keys()):
            if now - self._store[k] > self.ttl_seconds:
                self._store.pop(k, None)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def add_if_new(self, key: str) -> bool:
        self._prune()
        if key in self._store:
            self._store.move_to_end(key)
            _HARV_DEDUP.labels("hit").inc()
            return False
        self._store[key] = time.time()
        _HARV_DEDUP.labels("miss").inc()
        return True


class Harvester:
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

    def register(self, connector: Connector, *, window_s: Optional[int] = None, jitter_s: float = 5.0):
        self._connectors[connector.name] = connector
        now = time.time()
        w = float(window_s or self._window_s)
        self._schedules[connector.name] = _Schedule(next_run=now + 1.0, jitter_s=jitter_s, window_s=w)
        self._locks[connector.name] = asyncio.Lock()
        logger.info({"event": "harvester_connector_registered", "name": connector.name, "window_s": w})

    async def start(self):
        if self._producer_task:
            return
        self._stop.clear()
        self._producer_task = asyncio.create_task(self._producer_loop())
        self._consumer_task = asyncio.create_task(self._consumer_loop())
        logger.info("Harvester started")

    async def stop(self):
        self._stop.set()
        for t in (self._producer_task, self._consumer_task):
            if t:
                t.cancel()
        logger.info("Harvester stopping...")

    async def _producer_loop(self):
        while not self._stop.is_set():
            _HARV_QUEUE_DEPTH.set(self.queue.qsize())
            now = time.time()
            for name, conn in list(self._connectors.items()):
                sched = self._schedules.get(name)
                if not sched or now < sched.next_run:
                    continue
                # rate window: set next_run with jitter
                sched.next_run = now + sched.window_s + min(sched.jitter_s, sched.window_s)
                lock = self._locks[name]
                if lock.locked():
                    continue
                asyncio.create_task(self._fetch_and_enqueue(conn))
            await asyncio.sleep(0.5)

    def _hash_item(self, item: Dict[str, Any]) -> str:
        try:
            raw = json.dumps(item, sort_keys=True, ensure_ascii=False)
        except Exception:
            raw = str(item)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _fetch_and_enqueue(self, connector: Connector):
        name = connector.name
        start = time.perf_counter()
        try:
            # Apply resilience wrapper
            wrapped = resilient(
                max_attempts=3,
                initial_backoff=0.25,
                max_backoff=2.0,
                circuit_breaker=_CB,
                retry_on=(Exception,),
                operation_name=f"harvest_fetch_{name}",
            )(connector.fetch_batch)
            items = await asyncio.get_running_loop().run_in_executor(None, wrapped, self._batch_size)
            if not items:
                _HARV_LAT.labels(name, "empty").observe(time.perf_counter() - start)
                return
            accepted = 0
            for it in items:
                key = self._hash_item(it)
                if not self._dedup.add_if_new(key):
                    continue
                if self.queue.full():
                    _HARV_ITEMS.labels(name, "dropped_backpressure").inc()
                    continue
                await self.queue.put(it)
                accepted += 1
            outcome = "success" if accepted > 0 else "dedup_all"
            _HARV_ITEMS.labels(name, outcome).inc(accepted or 1)
            _HARV_LAT.labels(name, "success").observe(time.perf_counter() - start)
        except Exception as e:
            _HARV_ERRORS.labels(name, type(e).__name__).inc()
            _HARV_LAT.labels(name, "error").observe(time.perf_counter() - start)
            logger.error({"event": "harvest_fetch_error", "source": name, "error": str(e)}, exc_info=True)

    async def _consumer_loop(self):
        while not self._stop.is_set():
            try:
                item = await self.queue.get()
                _HARV_QUEUE_DEPTH.set(self.queue.qsize())
                # For demo, if item resembles an Experience, prepare a JSONL example and append to file (overwrite=True writes current only).
                try:
                    prompt = f"Contexto: {json.dumps(item.get('metadata', {}), ensure_ascii=False)}"
                    completion = item.get("content") or ""
                    if completion:
                        jsonl = json.dumps({"prompt": prompt, "completion": completion}, ensure_ascii=False)
                        # In DRY_RUN, write_file will log intent and not write.
                        write_file(TRAINING_DATA_FILE, jsonl + "\n", overwrite=True)
                except Exception:
                    pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error({"event": "harvest_consume_error", "error": str(e)}, exc_info=True)


# Default connector: read from episodic memory as a source of supervised examples
class MemoryConnector:
    name = "memory"

    def fetch_batch(self, limit: int = 50) -> List[Dict[str, Any]]:
        # Pull most recent experiences; the dedup layer avoids repeats.
        results = memory_core.recall(query="experiência do agente", n_results=limit)
        return results or []


# Singleton harvester and default connector registration (non-invasive)
harvester = Harvester()
try:
    harvester.register(MemoryConnector(), window_s=120)
except Exception:
    pass


# Backwards-compatible one-shot export remains available

def harvest_data_for_training(limit: int = 100) -> dict:
    """
    Coleta experiências da memória episódica e as formata num ficheiro
    JSONL, adequado para o fine-tuning de modelos de linguagem.
    """
    logger.info(f"Iniciando a coleta de dados de {limit} experiências para treino.")

    experiences = memory_core.recall(query="experiência do agente", n_results=limit)

    if not experiences:
        summary = "Nenhuma experiência encontrada para a coleta."
        logger.warning(summary)
        return {"message": "Coleta de dados concluída.", "summary": summary}

    training_examples = []
    for exp in experiences:
        if exp.get('content') and exp.get('metadata'):
            prompt = f"Contexto: {json.dumps(exp['metadata'], ensure_ascii=False)}"
            completion = exp['content']
            training_examples.append({"prompt": prompt, "completion": completion})

    if not training_examples:
        summary = "Experiências recuperadas não continham dados suficientes para criar exemplos de treino."
        logger.warning(summary)
        return {"message": "Coleta de dados concluída.", "summary": summary}

    jsonl_content = "\n".join(json.dumps(ex, ensure_ascii=False) for ex in training_examples)
    write_status = write_file(TRAINING_DATA_FILE, jsonl_content)

    logger.info(write_status)

    summary = f"Coleta de dados concluída. {len(training_examples)} exemplos de treino foram guardados em '{TRAINING_DATA_FILE}'."
    logger.info(summary)

    return {"message": "Coleta de dados bem-sucedida.", "summary": summary}
