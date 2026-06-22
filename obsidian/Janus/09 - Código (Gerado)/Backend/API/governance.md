---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/governance.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# governance

## Arquivos-fonte
- `backend/app/api/v1/endpoints/governance.py`

## Rotas
- `POST /classifications`
- `POST /purge/run`

## Dependências de código
- Serviços
  - `data_governance_service`
  - `data_purge_service`

## Símbolos
- class: `ClassificationUpsertRequest`
- function: `upsert_classification(payload: ClassificationUpsertRequest, request: Request)`
- class: `PurgeRunRequest`
- function: `run_purge(payload: PurgeRunRequest, request: Request)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
