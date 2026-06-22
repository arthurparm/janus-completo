---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/productivity.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# productivity

## Arquivos-fonte
- `backend/app/api/v1/endpoints/productivity.py`

## Rotas
- `GET /calendar/events`
- `GET /limits/status`
- `GET /mail/messages`
- `GET /notes`
- `GET /oauth/google/start`
- `POST /calendar/events/add`
- `POST /mail/messages/send`
- `POST /notes/add`
- `POST /oauth/google/callback`
- `POST /oauth/google/refresh`
- `POST /oauth/google/start`

## Dependências de código
- Serviços
  - `observability_service`
- Repositórios
  - `user_repository`

## Símbolos
- class: `OAuthStartRequest`
- class: `OAuthStartResponse`
- class: `OAuthCallbackRequest`
- class: `OAuthRefreshRequest`
- function: `get_consent_repo(request: Request)` -> `ConsentRepository`
- function: `get_knowledge_facade(request: Request)`
- function: `_is_unlimited_user(user_id: str | None = None)` -> `bool`
- function: `_ensure_consent(repo: ConsentRepository, user_id: str, scope: str)` -> `None`
- class: `CalendarEvent`
- class: `CalendarAddRequest`
- function: `calendar_add_event(payload: CalendarAddRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo), knowledge = Depends(get_knowledge_facade))`
- function: `oauth_google_start(payload: OAuthStartRequest, request: Request)`
- function: `calendar_list_events(request: Request, repo: ConsentRepository = Depends(get_consent_repo))`
- class: `MailMessage`
- class: `MailSendRequest`
- function: `mail_send(payload: MailSendRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo))`
- function: `mail_list(request: Request, repo: ConsentRepository = Depends(get_consent_repo))`
- class: `NoteItem`
- class: `NoteAddRequest`
- function: `notes_add(payload: NoteAddRequest, request: Request, repo: ConsentRepository = Depends(get_consent_repo), knowledge = Depends(get_knowledge_facade))`
- function: `notes_list(request: Request, repo: ConsentRepository = Depends(get_consent_repo))`
- function: `limits_status(request: Request)`
- function: `google_oauth_start(request: Request, scope: str = 'calendar')`
- class: `GoogleOAuthCallbackRequest`
- function: `google_oauth_callback(payload: GoogleOAuthCallbackRequest, request: Request)`
- function: `google_oauth_refresh(request: Request)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
