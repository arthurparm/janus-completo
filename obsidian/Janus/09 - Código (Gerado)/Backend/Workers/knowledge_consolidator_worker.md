---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/knowledge_consolidator_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_consolidator_worker

## Objetivo
Knowledge Consolidator Worker - Refactored Sprint 13

## Arquivos-fonte
- `backend/app/core/workers/knowledge_consolidator_worker.py`

## Símbolos
- class: `KnowledgeConsolidator`
  - Worker orquestrador que consolida memória episódica em memória semântica.
- method: `KnowledgeConsolidator.__init__(self)`
- method: `KnowledgeConsolidator._chunk_text(self, text: Any, chunk_size: int = 1000, overlap: int = 200)` -> `list[str]`
  - Divide texto em chunks com sobreposição. Retorna lista vazia para inputs inválidos.
- method: `KnowledgeConsolidator._normalize_point_id(self, experience_id: str | int)` -> `str | int`
  - Aplica o mesmo mapeamento usado na ingestão do MemoryCore:
- mantém int quando possível;
- mantém UUID válido sem alterar;
- caso contrário, UUID5 determinístico baseado na string do ID.
- method: `KnowledgeConsolidator._initialize(self)`
  - Inicializa componentes (lazy).
- method: `KnowledgeConsolidator.start(self, *, limit: int = 10, min_score: float = 0.0)` -> `None`
  - Inicia o ciclo periódico de consolidação em background.
- method: `KnowledgeConsolidator.stop(self)` -> `None`
  - Interrompe o ciclo periódico de consolidação.
- method: `KnowledgeConsolidator._consolidation_cycle(self, *, limit: int, min_score: float)` -> `None`
  - Loop periódico de consolidação em lote.
- method: `KnowledgeConsolidator.consolidate_batch(self, limit: int = 10, min_score: float = 0.0)` -> `dict[str, Any]`
  - Consolida um lote de experiências da memória episódica.
Entry point principal do worker.
- method: `KnowledgeConsolidator.consolidate_experience(self, experience_id: str, experience_content: str, metadata: dict[str, Any])`
  - Consolida uma única experiência.
- method: `KnowledgeConsolidator._build_consolidation_hash(self, content: str, metadata: dict[str, Any] | None = None)` -> `str`
- method: `KnowledgeConsolidator._mark_as_consolidated(self, experience_id: str, metadata: dict[str, Any] | None = None, *, entities_created: int = 0, relationships_created: int = 0)`
  - Atualiza flag no Qdrant para evitar reprocessamento.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
