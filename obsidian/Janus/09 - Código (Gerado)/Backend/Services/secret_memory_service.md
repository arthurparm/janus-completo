---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/secret_memory_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# secret_memory_service

## Arquivos-fonte
- `backend/app/services/secret_memory_service.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/memory.py`
- `backend/app/services/active_memory_service.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/rag_service.py`

## Símbolos
- function: `_try_int(value: str | None)` -> `int | None`
- class: `SecretMemoryService`
  - Stores user secrets in a separate encrypted namespace with explicit recall only.
- method: `SecretMemoryService.should_inspect_message(self, message: str)` -> `bool`
- method: `SecretMemoryService.should_authorize_prompt_recall(self, message: str)` -> `bool`
- method: `SecretMemoryService.extract_secret(self, message: str)` -> `dict[str, Any] | None`
- method: `SecretMemoryService.maybe_capture_from_message(self, *, user_id: str, message: str, conversation_id: str | None, threshold: float = 0.9)` -> `dict[str, Any] | None`
- method: `SecretMemoryService.store_secret(self, *, user_id: str, label: str, value: str, secret_type: str, secret_scope: str | None = None, conversation_id: str | None = None, source: str = 'memory.secret_api')` -> `dict[str, Any]`
- method: `SecretMemoryService.list_secrets(self, *, user_id: str, query: str | None = None, conversation_id: str | None = None, limit: int = 20, active_only: bool = True, reveal: bool = False)` -> `list[dict[str, Any]]`
- method: `SecretMemoryService.build_authorized_prompt_context(self, *, user_id: str, message: str, conversation_id: str | None = None, limit: int = 3)` -> `str | None`
- method: `SecretMemoryService._point_to_secret_item(self, point: Any, *, reveal: bool)` -> `dict[str, Any]`
- method: `SecretMemoryService._infer_secret_type(self, label: str)` -> `str`
- method: `SecretMemoryService._infer_scope(self, label: str)` -> `str`
- method: `SecretMemoryService._normalize_label(self, label: str)` -> `str`
- method: `SecretMemoryService._normalize_secret_value(self, value: str)` -> `str`
- method: `SecretMemoryService._mask_value(self, value: str)` -> `str`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
