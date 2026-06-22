---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/pending_action_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# pending_action_repository

## Arquivos-fonte
- `backend/app/repositories/pending_action_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/pending_actions.py`
- `backend/app/services/chat/chat_contracts.py`
- `backend/app/services/chat/conversation_service.py`
- `backend/app/services/tool_executor_service.py`

## Símbolos
- class: `PendingActionRepository`
- method: `PendingActionRepository.__init__(self, session: Session | None = None)`
- method: `PendingActionRepository._get_session(self)` -> `Session`
- method: `PendingActionRepository.create(self, tool_name: str, args_json: str, run_id: int | None, cycle: int | None, simulation_summary_json: str | None = None, simulation_generated_at: datetime | None = None, simulation_version: str | None = None)` -> `PendingAction`
- method: `PendingActionRepository.list(self, status: str | None = 'pending', limit: int = 50)` -> `list[PendingAction]`
- method: `PendingActionRepository.get(self, action_id: int)` -> `PendingAction | None`
- method: `PendingActionRepository.set_status(self, action_id: int, status: str)` -> `PendingAction | None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
