---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/data_harvester.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# data_harvester

## Arquivos-fonte
- `backend/app/core/workers/data_harvester.py`

## Símbolos
- function: `_normalize_item(item: BaseModel | dict[str, Any])` -> `dict[str, Any]`
  - Converte um item (Pydantic model ou dict) para dicionário.
- function: `_compute_prompt_hash(prompt: str, completion: str)` -> `str`
  - Calcula hash único para par prompt/completion.
- function: `_save_dataset_updates(new_examples: list[dict[str, Any]])` -> `dict[str, int]`
  - Helper centralizado para salvar novos exemplos no dataset de treino.
Realiza leitura, deduplicação (hash) e escrita (append/merge).
- class: `IHarvesterConnector`
  - Define o contrato para um conector de dados do Harvester.
- method: `IHarvesterConnector.fetch_batch(self, limit: int)` -> `list[dict[str, Any]]`
- class: `MemoryConnector`
  - Conector que extrai dados da memória episódica via repositório.
- method: `MemoryConnector.__init__(self, memory_repo: MemoryRepository)`
- method: `MemoryConnector._next_query(self)` -> `str`
- method: `MemoryConnector.fetch_batch(self, limit: int = 50, query: str | None = None)` -> `list[dict[str, Any]]`
- class: `DataHarvester`
  - Sistema de coleta assíncrona de dados, projetado para injeção de dependência.
- method: `DataHarvester.__init__(self, connectors: list[IHarvesterConnector], batch_size: int = 50)`
- method: `DataHarvester.start(self)`
  - Inicia os loops de coleta para cada conector.
- method: `DataHarvester.stop(self)`
  - Para todos os loops de coleta de forma graciosa.
- method: `DataHarvester._run_connector_loop(self, connector: IHarvesterConnector)`
  - Loop de execução para um conector específico.
- method: `DataHarvester._process_items(self, items: list[dict[str, Any]])`
  - Processa um lote de itens, formata e salva em um arquivo JSONL.
- function: `harvest_data_for_training(limit: int = 50, query: str | None = None, min_score: float | None = None, origin: str | None = None)` -> `dict[str, Any]`
  - Coleta um lote de experiências e salva em JSONL para treino.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
