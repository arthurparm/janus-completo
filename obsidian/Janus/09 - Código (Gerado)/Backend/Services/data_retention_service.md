---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/data_retention_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# data_retention_service

## Arquivos-fonte
- `backend/app/services/data_retention_service.py`

## Dependências de código
- Repositórios
  - `knowledge_repository`

## Fluxos de uso (chamadores)
- `backend/app/db/sync_events.py`

## Símbolos
- class: `DataRetentionService`
  - Service responsible for cleaning up artifacts (Vectors, Graph Nodes)
when a primary entity (User, Project) is deleted from SQL.
- method: `DataRetentionService.cleanup_user_artifacts(user_id: str | int)` -> `None`
  - Removes all data associated with a user from Qdrant and Neo4j.
This is a 'best effort' background operation or full reset for Single-User.
- method: `DataRetentionService._async_graph_cleanup(user_id: str)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
