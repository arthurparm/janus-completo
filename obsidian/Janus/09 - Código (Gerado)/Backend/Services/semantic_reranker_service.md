---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/semantic_reranker_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# semantic_reranker_service

## Arquivos-fonte
- `backend/app/services/semantic_reranker_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/rag_service.py`

## Símbolos
- class: `SemanticRerankResult`
- class: `SemanticRerankerService`
- method: `SemanticRerankerService.__init__(self)` -> `None`
- method: `SemanticRerankerService.rerank(self, *, query: str, items: list[dict[str, Any]], top_k: int)` -> `SemanticRerankResult`
- method: `SemanticRerankerService._rerank_cross_encoder(self, *, query: str, items: list[dict[str, Any]], top_k: int)` -> `list[dict[str, Any]] | None`
- method: `SemanticRerankerService._rerank_heuristic(self, *, query: str, items: list[dict[str, Any]], top_k: int)` -> `list[dict[str, Any]]`
- method: `SemanticRerankerService._get_cross_encoder(self)`
- method: `SemanticRerankerService._extract_content(self, item: dict[str, Any])` -> `str`
- method: `SemanticRerankerService._tokenize(self, text: str)` -> `set[str]`
- method: `SemanticRerankerService._infer_query_profile(self, query: str)` -> `dict[str, Any]`
- method: `SemanticRerankerService._metadata_alignment_score(self, item: dict[str, Any], profile: dict[str, Any])` -> `float`
- method: `SemanticRerankerService._extract_metadata(self, item: dict[str, Any])` -> `dict[str, Any]`
- method: `SemanticRerankerService._item_timestamp(self, item: dict[str, Any])` -> `float`
- method: `SemanticRerankerService._as_float(self, value: Any)` -> `float`
- method: `SemanticRerankerService._normalize(self, values: list[float])` -> `list[float]`
- function: `get_semantic_reranker()` -> `SemanticRerankerService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
