---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/pending_actions.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# pending_actions

## Arquivos-fonte
- `backend/app/api/v1/endpoints/pending_actions.py`

## Rotas
- `GET /`
- `POST /action/{action_id}/approve`
- `POST /action/{action_id}/reject`
- `POST /{thread_id}/approve`
- `POST /{thread_id}/reject`

## Dependências de código
- Repositórios
  - `chat_repository_sql`
  - `pending_action_repository`

## Símbolos
- class: `PendingActionDTO`
- function: `_summarize_action_risk(tool_name: str | None, args_json: str | None)` -> `tuple[str, str]`
- function: `_sanitize_pending_args_json(args_json: str | None)` -> `str | None`
- function: `_extract_pending_scope(args_json: str | None)` -> `tuple[str | None, list[str] | None]`
- function: `_build_simulation_payload(item: Any)` -> `dict[str, Any] | None`
- function: `_is_backend_unavailable_error(error: Exception)` -> `bool`
- function: `_is_waiting_for_human_approval(next_value: object)` -> `bool`
- function: `_load_pending_action_context(args_json: str | None)` -> `dict[str, Any]`
- function: `_build_resolved_confirmation_payload(confirmation: dict[str, Any] | None, *, status_value: str)` -> `dict[str, Any]`
- function: `_build_resolved_understanding_payload(understanding: dict[str, Any] | None, *, status_value: str)` -> `dict[str, Any] | None`
- function: `_build_resolved_agent_state_payload(agent_state: dict[str, Any] | None, *, status_value: str)` -> `dict[str, Any]`
- function: `_build_resolved_chat_message_patch(message: dict[str, Any], *, status_value: str)` -> `dict[str, Any]`
- function: `_sync_chat_confirmation_for_action(action: Any, *, status_value: str)` -> `None`
- function: `_get_session_context_manager(postgres_db)`
- function: `_get_state(graph, config: dict)`
- function: `_update_state(graph, config: dict, values: dict)`
- function: `_invoke_resume(graph, thread_id: str, resume_value: str)`
- function: `_thread_exists_in_checkpoints(thread_id: str)` -> `bool | None`
  - Returns True when a checkpoint row exists, False when definitely absent,
and None when the environment/test-double cannot determine safely.
- function: `_resume_graph_execution(thread_id: str, resume_value: str)`
  - Background task to resume graph execution.
- function: `list_pending(include_graph: bool = True, include_sql: bool = False, pending_status: str | None = 'pending', limit: int = 50)`
  - List all threads that are currently interrupted and waiting for approval.
Uses LangGraph state to determine if a thread is currently stopped at
the human_approval interruption point.
- function: `approve(thread_id: str, background_tasks: BackgroundTasks)`
- function: `approve_sql_action(action_id: int)`
- function: `reject_sql_action(action_id: int)`
- function: `reject(thread_id: str, background_tasks: BackgroundTasks)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
