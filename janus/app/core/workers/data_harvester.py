import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Protocol, runtime_checkable, Optional, Union

from pydantic import BaseModel
from app.core.infrastructure.filesystem_manager import write_file, read_file
from app.repositories.memory_repository import MemoryRepository
from app.core.memory.memory_core import get_memory_db

logger = logging.getLogger(__name__)


def _normalize_item(item: Union[BaseModel, Dict[str, Any]]) -> Dict[str, Any]:
    """Converte um item (Pydantic model ou dict) para dicionário."""
    if isinstance(item, BaseModel):
        return item.model_dump()
    return item

TRAINING_DATA_FILE = "training_data.jsonl"

@runtime_checkable
class IHarvesterConnector(Protocol):
    """Define o contrato para um conector de dados do Harvester."""
    name: str

    async def fetch_batch(self, limit: int) -> List[Dict[str, Any]]:
        ...


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

    async def fetch_batch(self, limit: int = 50, query: Optional[str] = None) -> List[Dict[str, Any]]:
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

    def __init__(self, connectors: List[IHarvesterConnector], batch_size: int = 50):
        if not connectors:
            raise ValueError("O DataHarvester requer pelo menos um conector.")
        self.connectors = connectors
        self._batch_size = batch_size
        self._stop_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        logger.info(f"DataHarvester inicializado com {len(connectors)} conector(es).")

    async def start(self):
        """Inicia os loops de coleta para cada conector."""
        if self._tasks:
            logger.warning("Harvester já está em execução.")
            return
        self._stop_event.clear()
        self._tasks = [asyncio.create_task(self._run_connector_loop(conn)) for conn in self.connectors]
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
                # Aguarda um intervalo antes da próxima coleta (pode ser configurável)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop do conector {connector.name}", exc_info=e)
                await asyncio.sleep(30)  # Penalidade em caso de erro
        logger.info(f"Loop do conector {connector.name} encerrado.")

    async def _process_items(self, items: List[Dict[str, Any]]):
        """Processa um lote de itens, formata e salva em um arquivo JSONL."""
        logger.info(f"Processando {len(items)} itens coletados.")
        try:
            # construir exemplos prompt/completion
            training_examples: List[Dict[str, Any]] = []
            for raw_item in items:
                item = _normalize_item(raw_item)
                if item.get('content') and item.get('metadata'):
                    prompt = f"Contexto: {json.dumps(item['metadata'], ensure_ascii=False)}"
                    completion = item['content']
                    training_examples.append({"prompt": prompt, "completion": completion})

            if not training_examples:
                return

            # mesclar com arquivo existente e deduplicar via hash de prompt+completion
            existing = read_file(f"workspace/{TRAINING_DATA_FILE}")
            seen_hashes: set[str] = set()
            existing_lines: List[str] = []
            if isinstance(existing, str) and not existing.startswith("Erro:"):
                for ln in [l for l in existing.strip().split('\n') if l.strip()]:
                    existing_lines.append(ln)
                    try:
                        obj = json.loads(ln)
                        key = (obj.get("prompt", "") + "|||" + obj.get("completion", ""))
                        seen_hashes.add(hashlib.sha256(key.encode("utf-8")).hexdigest())
                    except Exception:
                        continue

            new_lines: List[str] = []
            for ex in training_examples:
                key = (ex["prompt"] + "|||" + ex["completion"])
                h = hashlib.sha256(key.encode("utf-8")).hexdigest()
                if h in seen_hashes:
                    continue
                new_lines.append(json.dumps(ex, ensure_ascii=False))
                seen_hashes.add(h)

            combined_lines = existing_lines + new_lines
            combined_lines = combined_lines[-2000:]
            combined_text = "\n".join(combined_lines) + ("\n" if combined_lines else "")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, write_file, TRAINING_DATA_FILE, combined_text, True)
            logger.info(f"Dataset atualizado com {len(combined_lines)} linhas (novas: {len(new_lines)}).")
        except Exception as e:
            logger.error("Erro ao processar e salvar itens para treinamento", exc_info=e)


# Instância opcional para health check simples
harvester: DataHarvester | None = None


async def harvest_data_for_training(limit: int = 50, query: Optional[str] = None, min_score: Optional[float] = None, origin: Optional[str] = None) -> \
Dict[str, Any]:
    """Coleta um lote de experiências e salva em JSONL para treino.

    Esta função executa um ciclo único de coleta diretamente do repositório
    de memória, formata os dados em pares (prompt, completion) e persiste no
    ficheiro `training_data.jsonl` dentro do workspace.
    """
    start = time.perf_counter()
    try:
        memory_db = await get_memory_db()
        memory_repo = MemoryRepository(memory_db)
        connector = MemoryConnector(memory_repo)
        if origin:
            try:
                filters = {"origin": origin}
                items = await memory_repo.search_filtered(query=query, filters=filters, limit=limit, min_score=min_score)
            except Exception:
                items = await connector.fetch_batch(limit=limit, query=query)
        else:
            items = await connector.fetch_batch(limit=limit, query=query)

        # Filtragem por pontuação mínima, se disponível
        if min_score is not None:
            filtered: List[Dict[str, Any]] = []
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

        training_examples: List[Dict[str, Any]] = []
        for raw_item in items:
            item = _normalize_item(raw_item)
            if item.get("content") and item.get("metadata"):
                prompt = f"Contexto: {json.dumps(item['metadata'], ensure_ascii=False)}"
                completion = item["content"]
                prompt = sanitize_text(prompt)
                completion = sanitize_text(completion)
                training_examples.append({"prompt": prompt, "completion": completion})

        if not training_examples:
            summary = "Sem dados adequados para treino neste lote."
            logger.info(summary)
            return {"message": "Coleta concluída com sucesso (sem exemplos válidos).", "summary": summary}

        # Deduplicação baseada em hash de prompt+completion
        existing = read_file(f"workspace/{TRAINING_DATA_FILE}")
        seen_hashes: set[str] = set()
        existing_lines: List[str] = []
        if not existing.startswith("Erro:"):
            for ln in [l for l in existing.strip().split('\n') if l.strip()]:
                existing_lines.append(ln)
                try:
                    obj = json.loads(ln)
                    key = (obj.get("prompt", "") + "|||" + obj.get("completion", ""))
                    seen_hashes.add(hashlib.sha256(key.encode("utf-8")).hexdigest())
                except Exception:
                    continue

        new_lines: List[str] = []
        saved_count = 0
        for ex in training_examples:
            key = (ex["prompt"] + "|||" + ex["completion"])
            h = hashlib.sha256(key.encode("utf-8")).hexdigest()
            if h in seen_hashes:
                continue
            new_lines.append(json.dumps(ex, ensure_ascii=False))
            seen_hashes.add(h)
            saved_count += 1

        # Combina e aplica política simples de retenção para tamanho
        combined_lines = existing_lines + new_lines
        # Retém no máximo 2000 linhas para evitar exceder limites
        combined_lines = combined_lines[-2000:]
        combined_text = "\n".join(combined_lines) + ("\n" if combined_lines else "")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_file, TRAINING_DATA_FILE, combined_text, True)

        elapsed = time.perf_counter() - start
        logger.info(
            f"{len(training_examples)} exemplos de treino salvos em {TRAINING_DATA_FILE} em {elapsed:.2f}s"
        )
        return {
            "message": "Coleta bem-sucedida.",
            "summary": f"{saved_count} novos exemplos salvos (total {len(combined_lines)}) em {TRAINING_DATA_FILE}.",
        }
    except Exception as e:
        logger.error("Erro no harvesting sob demanda", exc_info=e)
        return {"message": "Falha na coleta de dados.", "summary": str(e)}
