---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/knowledge_space_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_space_repository

## Arquivos-fonte
- `backend/app/repositories/knowledge_space_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/services/knowledge_space_service.py`

## Símbolos
- class: `KnowledgeSpaceRepositoryError`
- class: `KnowledgeSpaceRepository`
- method: `KnowledgeSpaceRepository.create_space(self, *, knowledge_space_id: str, user_id: str, name: str, source_type: str, source_id: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None, description: str | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceRepository.get_space(self, knowledge_space_id: str, *, user_id: str | None = None)` -> `dict[str, Any] | None`
- method: `KnowledgeSpaceRepository.list_spaces(self, *, user_id: str, statuses: Iterable[str] | None = None, limit: int = 100)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceRepository.update_space(self, knowledge_space_id: str, **fields: Any)` -> `dict[str, Any] | None`
- method: `KnowledgeSpaceRepository.mark_consolidation(self, knowledge_space_id: str, *, status: str, summary: str | None = None, last_consolidated_at: datetime | None = None, sections_total: int | None = None, sections_indexed: int | None = None, sections_skipped_as_noise: int | None = None, canonical_frames_total: int | None = None, consolidation_quality_score: str | float | None = None)` -> `dict[str, Any] | None`
- method: `KnowledgeSpaceRepository._serialize(self, row: KnowledgeSpace)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
