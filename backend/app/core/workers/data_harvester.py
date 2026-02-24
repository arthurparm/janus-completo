import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from app.core.infrastructure.filesystem_manager import read_file, write_file
from app.core.infrastructure.prompt_loader import get_formatted_prompt
from app.core.memory.memory_core import get_memory_db
from app.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


TRAINING_DATA_FILE = "training_data.jsonl"


def _normalize_item(item: BaseModel | dict[str, Any]) -> dict[str, Any]:
    """Converte um item (Pydantic model ou dict) para dicionário."""
    if isinstance(item, BaseModel):
        return item.model_dump()
    return item


def _compute_prompt_hash(prompt: str, completion: str) -> str:
    """Calcula hash único para par prompt/completion."""
    key = prompt + "|||" + completion
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


async def _save_dataset_updates(new_examples: list[dict[str, Any]]) -> dict[str, int]:
    """
    Helper centralizado para salvar novos exemplos no dataset de treino.
    Realiza leitura, deduplicação (hash) e escrita (append/merge).
    """
    if not new_examples:
        return {"added": 0, "total": 0}

    # 1. Carregar existente
    existing_content = await asyncio.to_thread(read_file, f"workspace/{TRAINING_DATA_FILE}")
    seen_hashes: set[str] = set()
    existing_lines: list[str] = []

    if isinstance(existing_content, str) and not existing_content.startswith("Erro:"):
        for ln in [line for line in existing_content.strip().split("\n") if line.strip()]:
            existing_lines.append(ln)
            try:
                obj = json.loads(ln)
                h = _compute_prompt_hash(obj.get("prompt", ""), obj.get("completion", ""))
                seen_hashes.add(h)
            except json.JSONDecodeError:
                continue

    # 2. Filtrar novos
    new_lines: list[str] = []
    added_count = 0
    for ex in new_examples:
        h = _compute_prompt_hash(ex["prompt"], ex["completion"])
        if h in seen_hashes:
            continue
        new_lines.append(json.dumps(ex, ensure_ascii=False))
        seen_hashes.add(h)
        added_count += 1

    # 3. Combinar e Salvar
    combined_lines = existing_lines + new_lines
    # Retém no máximo 5000 linhas (aumento de limite, era 2000)
    combined_lines = combined_lines[-5000:]
    combined_text = "\n".join(combined_lines) + ("\n" if combined_lines else "")

    await asyncio.to_thread(write_file, TRAINING_DATA_FILE, combined_text, True)

    return {"added": added_count, "total": len(combined_lines)}


@runtime_checkable
class IHarvesterConnector(Protocol):
    """Define o contrato para um conector de dados do Harvester."""

    name: str

    async def fetch_batch(self, limit: int) -> list[dict[str, Any]]: ...


class MemoryConnector(IHarvesterConnector):
    """Conector que extrai dados da memória episódica via repositório."""

    name = "episodic_memory_connector"

    def __init__(self, memory_repo: MemoryRepository):
        self._repo = memory_repo
        # ciclo de consultas para diversificar quando nenhuma query explícita for fornecida
        self._query_cycle = [
            "action_success",
            "action_failure",
            "lessons_learned",
            "reflexion_iteration",
            "neural_training",
            "reasoning",
            "log",
            "experiência do agente",
        ]
        self._q_idx = 0

    def _next_query(self) -> str:
        q = self._query_cycle[self._q_idx % len(self._query_cycle)]
        self._q_idx += 1
        return q

    async def fetch_batch(self, limit: int = 50, query: str | None = None) -> list[dict[str, Any]]:
        logger.debug(f"Coletando experiências via {self.name}")
        try:
            effective_query = query or self._next_query()
            return await self._repo.search_experiences(query=effective_query, limit=limit)
        except Exception as e:
            logger.error(f"Erro ao coletar dados de {self.name}", exc_info=e)
            return []


class DataHarvester:
    """
    Sistema de coleta assíncrona de dados, projetado para injeção de dependência.
    """

    def __init__(self, connectors: list[IHarvesterConnector], batch_size: int = 50):
        if not connectors:
            raise ValueError("O DataHarvester requer pelo menos um conector.")
        self.connectors = connectors
        self._batch_size = batch_size
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        logger.info(f"DataHarvester inicializado com {len(connectors)} conector(es).")

    async def start(self):
        """Inicia os loops de coleta para cada conector."""
        if self._tasks:
            logger.warning("Harvester já está em execução.")
            return
        self._stop_event.clear()
        self._tasks = [
            asyncio.create_task(self._run_connector_loop(conn)) for conn in self.connectors
        ]
        logger.info("DataHarvester iniciado.")

    async def stop(self):
        """Para todos os loops de coleta de forma graciosa."""
        if not self._tasks:
            return
        logger.info("Parando o DataHarvester...")
        self._stop_event.set()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("DataHarvester parado.")

    async def _run_connector_loop(self, connector: IHarvesterConnector):
        """Loop de execução para um conector específico."""
        logger.info(f"Iniciando loop para o conector: {connector.name}")
        while not self._stop_event.is_set():
            try:
                items = await connector.fetch_batch(self._batch_size)
                if items:
                    await self._process_items(items)
                # Aguarda um intervalo antes da próxima coleta (60s)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop do conector {connector.name}", exc_info=e)
                await asyncio.sleep(30)  # Penalidade em caso de erro
        logger.info(f"Loop do conector {connector.name} encerrado.")

    async def _process_items(self, items: list[dict[str, Any]]):
        """Processa um lote de itens, formata e salva em um arquivo JSONL."""
        logger.info(f"Processando {len(items)} itens coletados.")
        try:
            training_examples: list[dict[str, Any]] = []
            for raw_item in items:
                item = _normalize_item(raw_item)
                if item.get("content") and item.get("metadata"):
                    prompt = await get_formatted_prompt(
                        "training_metadata_context_prompt",
                        metadata=json.dumps(item["metadata"], ensure_ascii=False),
                    )
                    completion = item["content"]
                    training_examples.append({"prompt": prompt, "completion": completion})

            if not training_examples:
                return

            stats = await _save_dataset_updates(training_examples)
            logger.info(
                f"Dataset atualizado: {stats['added']} novos exemplos (Total: {stats['total']})."
            )

        except Exception as e:
            logger.error("Erro ao processar e salvar itens para treinamento", exc_info=e)


# Instância opcional para health check simples
harvester: DataHarvester | None = None


async def harvest_data_for_training(
    limit: int = 50,
    query: str | None = None,
    min_score: float | None = None,
    origin: str | None = None,
) -> dict[str, Any]:
    """Coleta um lote de experiências e salva em JSONL para treino."""
    start = time.perf_counter()
    try:
        memory_db = await get_memory_db()
        memory_repo = MemoryRepository(memory_db)
        connector = MemoryConnector(memory_repo)

        # Logica de fetch com ou sem filtro de origem
        items = []
        if origin:
            try:
                filters = {"origin": origin}
                # Tenta busca filtrada específica se o repositório suportar
                if hasattr(memory_repo, "search_filtered"):
                    items = await memory_repo.search_filtered(
                        query=query, filters=filters, limit=limit, min_score=min_score
                    )
                else:
                    # Fallback
                    items = await connector.fetch_batch(limit=limit, query=query)
            except Exception as e:
                logger.warning(f"Erro na busca filtrada, fallback para fetch normal: {e}")
                items = await connector.fetch_batch(limit=limit, query=query)
        else:
            items = await connector.fetch_batch(limit=limit, query=query)

        # Filtragem por pontuação mínima (client-side filter se repo não filtrou)
        if min_score is not None:
            # Nota: Se search_filtered já filtrou, isso é redundante mas seguro
            filtered: list[dict[str, Any]] = []
            for raw_it in items:
                it = _normalize_item(raw_it)
                score = it.get("score")
                if score is None:
                    score = (it.get("metadata") or {}).get("score")
                if score is None or float(score) >= float(min_score):
                    filtered.append(it)
            items = filtered

        def sanitize_text(text: str, max_len: int = 4096) -> str:
            # Remove quebras excessivas e limita tamanho
            s = " ".join(str(text).split())
            return s[:max_len]

        training_examples: list[dict[str, Any]] = []
        for raw_item in items:
            item = _normalize_item(raw_item)
            if item.get("content") and item.get("metadata"):
                prompt = await get_formatted_prompt(
                    "training_metadata_context_prompt",
                    metadata=json.dumps(item["metadata"], ensure_ascii=False),
                )
                completion = item["content"]
                prompt = sanitize_text(prompt)
                completion = sanitize_text(completion)
                training_examples.append({"prompt": prompt, "completion": completion})

        if not training_examples:
            return {
                "message": "Coleta concluída com sucesso (sem exemplos válidos).",
                "summary": "Nenhum exemplo gerado.",
            }

        # Usa o helper centralizado
        stats = await _save_dataset_updates(training_examples)

        elapsed = time.perf_counter() - start
        return {
            "message": "Coleta bem-sucedida.",
            "summary": f"{stats['added']} novos exemplos salvos (total {stats['total']}). Tempo: {elapsed:.2f}s",
        }

    except Exception as e:
        logger.error("Erro no harvesting sob demanda", exc_info=e)
        return {"message": "Falha na coleta de dados.", "summary": str(e)}
