---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/profiles.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# profiles

## Arquivos-fonte
- `backend/app/api/v1/endpoints/profiles.py`

## Rotas
- `GET /{user_id}`
- `POST /`

## Dependências de código
- Repositórios
  - `user_repository`

## Símbolos
- class: `UpsertProfileRequest`
- class: `ProfileResponse`
- function: `get_profile_repo(request: Request)` -> `ProfileRepository`
- function: `get_profile(user_id: int, repo: ProfileRepository = Depends(get_profile_repo))`
- function: `upsert_profile(payload: UpsertProfileRequest, repo: ProfileRepository = Depends(get_profile_repo))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
