---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/document_semantic_enrichment_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# document_semantic_enrichment_service

## Arquivos-fonte
- `backend/app/services/document_semantic_enrichment_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/document_service.py`

## Símbolos
- class: `DocumentSemanticMetadata`
- method: `DocumentSemanticMetadata.to_dict(self)` -> `dict[str, Any]`
- class: `DocumentSemanticEnrichmentService`
- method: `DocumentSemanticEnrichmentService.enrich(self, *, text: str, filename: str, content_type: str)` -> `DocumentSemanticMetadata`
- method: `DocumentSemanticEnrichmentService._classify_doc_type(self, *, text: str, filename: str, content_type: str)` -> `tuple[str, float]`
- method: `DocumentSemanticEnrichmentService._extract_entities(self, text: str)` -> `dict[str, list[str]]`
- method: `DocumentSemanticEnrichmentService._build_summary(self, text: str)` -> `str`
- method: `DocumentSemanticEnrichmentService._dedupe_take(values: list[str], limit: int)` -> `list[str]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
