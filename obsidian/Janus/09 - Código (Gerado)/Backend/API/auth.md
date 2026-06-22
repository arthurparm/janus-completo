---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/auth.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# auth

## Arquivos-fonte
- `backend/app/api/v1/endpoints/auth.py`

## Rotas
- `GET /local/me`
- `POST /firebase/exchange`
- `POST /local/login`
- `POST /local/refresh`
- `POST /local/register`
- `POST /local/request-reset`
- `POST /local/reset`
- `POST /supabase/exchange`
- `POST /token`

## Dependências de código
- Repositórios
  - `observability_repository`
  - `user_repository`

## Símbolos
- class: `TokenRequest`
- class: `TokenResponse`
- function: `get_user_repo(request: Request)` -> `UserRepository`
- function: `issue_token(payload: TokenRequest, request: Request, repo: UserRepository = Depends(get_user_repo))`
- class: `SupabaseExchangeRequest`
- function: `supabase_exchange(payload: SupabaseExchangeRequest, repo: UserRepository = Depends(get_user_repo))`
- class: `FirebaseExchangeRequest`
- class: `AuthUserResponse`
- class: `AuthExchangeResponse`
- class: `LocalRegisterRequest`
- class: `LocalLoginRequest`
- class: `LocalResetRequest`
- class: `LocalResetConfirmRequest`
- class: `LocalAuthUserResponse`
- class: `LocalAuthResponse`
- class: `LocalRefreshRequest`
- class: `LocalResetResponse`
- function: `_can_return_reset_token()` -> `bool`
- function: `_normalize_cpf(value: str | None)` -> `str`
- function: `_validate_cpf_or_raise(value: str | None)` -> `str`
- function: `_cpf_hash_scope(value: str | None)` -> `str`
- function: `_is_allowlisted_admin_cpf(value: str | None)` -> `bool`
- function: `_ensure_admin_role_for_user(repo: UserRepository, user_id: int)` -> `None`
- function: `_should_promote_user_to_admin_by_cpf(user_id: int)` -> `bool`
- function: `_is_cpf_already_registered(repo: UserRepository, cpf_value: str | None)` -> `bool`
- function: `_ensure_firebase_initialized()` -> `None`
- function: `firebase_exchange(payload: FirebaseExchangeRequest, repo: UserRepository = Depends(get_user_repo))`
- function: `local_register(payload: LocalRegisterRequest, repo: UserRepository = Depends(get_user_repo))`
- function: `local_login(payload: LocalLoginRequest, request: Request, repo: UserRepository = Depends(get_user_repo))`
- function: `local_refresh(payload: LocalRefreshRequest, request: Request, repo: UserRepository = Depends(get_user_repo))`
- function: `local_me(request: Request, repo: UserRepository = Depends(get_user_repo))`
- function: `local_request_reset(payload: LocalResetRequest, request: Request, repo: UserRepository = Depends(get_user_repo))`
- function: `local_reset_password(payload: LocalResetConfirmRequest, request: Request, repo: UserRepository = Depends(get_user_repo))`
- function: `_build_local_user(repo: UserRepository, user)` -> `LocalAuthUserResponse`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
