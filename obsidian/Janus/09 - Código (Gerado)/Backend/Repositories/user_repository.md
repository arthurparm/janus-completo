---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/user_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# user_repository

## Arquivos-fonte
- `backend/app/repositories/user_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/consents.py`
- `backend/app/api/v1/endpoints/productivity.py`
- `backend/app/api/v1/endpoints/profiles.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/core/security/chat_unlimited.py`
- `backend/app/core/security/request_guard.py`
- `backend/app/core/workers/google_productivity_worker.py`
- `backend/app/repositories/chat_repository_sql.py`
- `backend/app/services/system_user_service.py`

## Símbolos
- class: `UserRepository`
- method: `UserRepository.__init__(self, session: Session | None = None)`
- method: `UserRepository._get_session(self)` -> `Session`
- method: `UserRepository.get_user(self, user_id: int)` -> `User | None`
- method: `UserRepository.get_by_email(self, email: str)` -> `User | None`
- method: `UserRepository.get_by_external_id(self, external_id: str)` -> `User | None`
- method: `UserRepository.create_user(self, email: str | None, display_name: str | None, external_id: str | None = None, username: str | None = None, password_hash: str | None = None, cpf_hash: str | None = None)` -> `User`
- method: `UserRepository.get_by_username(self, username: str)` -> `User | None`
- method: `UserRepository.get_by_cpf_hash(self, cpf_hash: str)` -> `User | None`
- method: `UserRepository.set_external_id(self, user_id: int, external_id: str)` -> `bool`
- method: `UserRepository.set_password_hash(self, user_id: int, password_hash: str | None)` -> `bool`
- method: `UserRepository.set_cpf_hash(self, user_id: int, cpf_hash: str | None)` -> `bool`
- method: `UserRepository.set_reset_token(self, user_id: int, token_hash: str | None, expires_at: Any | None = None)` -> `bool`
- method: `UserRepository.get_by_reset_token(self, token_hash: str)` -> `User | None`
- method: `UserRepository.assign_role(self, user_id: int, role_name: str)` -> `bool`
- method: `UserRepository.is_admin(self, user_id: int)` -> `bool`
- method: `UserRepository.has_role(self, user_id: int, role_name: str)` -> `bool`
- method: `UserRepository.has_any_admin(self)` -> `bool`
- method: `UserRepository.list_roles(self, user_id: int)` -> `list[str]`
- class: `ProfileRepository`
- method: `ProfileRepository.__init__(self, session: Session | None = None)`
- method: `ProfileRepository._get_session(self)` -> `Session`
- method: `ProfileRepository.get_by_user(self, user_id: int)` -> `Profile | None`
- method: `ProfileRepository.upsert(self, user_id: int, timezone: str | None, language: str | None, style_prefs: str | None)` -> `Profile`
- class: `ConsentRepository`
- method: `ConsentRepository.__init__(self, session: Session | None = None)`
- method: `ConsentRepository._get_session(self)` -> `Session`
- method: `ConsentRepository.add_consent(self, user_id: int, scope: str, granted: bool = True, expires_at: Any | None = None)` -> `Consent`
- method: `ConsentRepository.list_consents(self, user_id: int)` -> `list[Consent]`
- method: `ConsentRepository.list_user_ids_by_scope(self, scope: str)` -> `list[int]`
- method: `ConsentRepository.revoke_consent(self, user_id: int, scope: str)` -> `bool`
- method: `ConsentRepository.has_consent(self, user_id: int, scope: str)` -> `bool`
- class: `OAuthTokenRepository`
- method: `OAuthTokenRepository.__init__(self, session: Session | None = None)`
- method: `OAuthTokenRepository._get_session(self)` -> `Session`
- method: `OAuthTokenRepository.upsert(self, user_id: int, provider: str, access_token: str, refresh_token: str | None, expires_at: Any | None)` -> `OAuthToken`
- method: `OAuthTokenRepository.get(self, user_id: int, provider: str)` -> `OAuthToken | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
