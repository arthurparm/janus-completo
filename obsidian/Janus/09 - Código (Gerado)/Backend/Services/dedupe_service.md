---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/dedupe_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# dedupe_service

## Arquivos-fonte
- `backend/app/services/dedupe_service.py`

## Dependências de código
- Repositórios
  - `knowledge_repository`

## Símbolos
- class: `DedupeError`
  - Erro base para falhas no serviço de deduplicação.
- class: `DedupeService`
- method: `DedupeService.__init__(self, db_session: Session | None = None, graph_db: GraphDatabase | None = None)`
- method: `DedupeService._get_session(self)` -> `Session`
- method: `DedupeService._get_graph(self)` -> `GraphDatabase`
- method: `DedupeService.detect_db_duplicates(self)` -> `dict[str, Any]`
- method: `DedupeService.fix_db_duplicates(self)` -> `dict[str, Any]`
- method: `DedupeService.dedupe_graph(self)` -> `dict[str, Any]`
- method: `DedupeService.detect_qdrant_duplicates(self)` -> `dict[str, Any]`
- method: `DedupeService._write_report(self, data: dict[str, Any])` -> `str`
- method: `DedupeService.run(self, dry_run: bool = True)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
