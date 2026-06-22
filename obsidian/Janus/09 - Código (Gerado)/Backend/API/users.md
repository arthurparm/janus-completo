---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/users.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# users

## Arquivos-fonte
- `backend/app/api/v1/endpoints/users.py`

## Rotas
- `DELETE /{user_id}/consents/{scope}`
- `GET /{user_id}`
- `GET /{user_id}/consents`
- `POST /`
- `POST /{user_id}/consents`
- `POST /{user_id}/roles`

## Dependências de código
- Repositórios
  - `user_repository`

## Símbolos
- class: `CreateUserRequest`
- class: `UserResponse`
- class: `AssignRoleRequest`
- function: `get_user_repo(request: Request)` -> `UserRepository`
- function: `create_user(payload: CreateUserRequest, repo: UserRepository = Depends(get_user_repo))`
- function: `get_user(user_id: int, repo: UserRepository = Depends(get_user_repo))`
- function: `assign_role(user_id: int, payload: AssignRoleRequest, request: Request, repo: UserRepository = Depends(get_user_repo))`
- class: `ConsentRequest`
- class: `ConsentResponse`
- function: `get_consent_repo(request: Request)` -> `ConsentRepository`
- function: `add_consent(user_id: int, payload: ConsentRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo))`
- function: `list_consents(user_id: int, request: Request, repo: ConsentRepository = Depends(get_consent_repo))`
- function: `revoke_consent(user_id: int, scope: str, request: Request, repo: ConsentRepository = Depends(get_consent_repo))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
