---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/reasoning_rag_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# reasoning_rag_service

## Objetivo
Reasoning RAG Service (HyDE & Re-Ranking).

## Arquivos-fonte
- `backend/app/services/reasoning_rag_service.py`

## Fluxos de uso (chamadores)
- `backend/app/core/memory/graph_rag_core.py`

## Símbolos
- function: `generate_hypothetical_answer(question: str)` -> `str`
  - Generate a hypothetical ideal answer for semantic search (HyDE).
- function: `rerank_chunks(question: str, chunks: list[dict[str, Any]], top_k: int | None = None)` -> `list[dict[str, Any]]`
  - Re-rank retrieved chunks using LLM.
- function: `enhanced_rag_search(question: str, search_fn, top_k: int = 5)` -> `list[dict[str, Any]]`
  - Perform enhanced RAG search with HyDE and Re-Ranking.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
