---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/consents.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# consents

## Arquivos-fonte
- `backend/app/api/v1/endpoints/consents.py`

## Rotas
- `GET /`
- `POST /`
- `POST /{consent_id}/revoke`

## Dependências de código
- Repositórios
  - `user_repository`

## Símbolos
- function: `_get_session()` -> `Session`
- class: `ConsentRequest`
- class: `ConsentResponse`
- function: `grant_consent(payload: ConsentRequest, request: Request)`
- function: `list_consents(user_id: str | None = None, scope: str | None = None, request: Request = None)`
- function: `revoke_consent(consent_id: int, request: Request)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
