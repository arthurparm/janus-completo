---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/user_preference_memory_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# user_preference_memory_service

## Arquivos-fonte
- `backend/app/services/user_preference_memory_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/memory.py`
- `backend/app/services/active_memory_service.py`
- `backend/app/services/rag_service.py`

## Símbolos
- class: `UserPreferenceMemoryService`
  - Captures and retrieves persistent user preferences (do/don't).
- method: `UserPreferenceMemoryService.should_inspect_message(self, message: str)` -> `bool`
- method: `UserPreferenceMemoryService.extract_preference(self, message: str)` -> `dict[str, Any] | None`
- method: `UserPreferenceMemoryService.maybe_capture_from_message(self, *, message: str, conversation_id: str | None, user_id: str, threshold: float = 0.75)` -> `dict[str, Any] | None`
- method: `UserPreferenceMemoryService.list_preferences(self, *, conversation_id: str | None = None, limit: int = 20, active_only: bool = True, query: str | None = None)` -> `list[dict[str, Any]]`
- method: `UserPreferenceMemoryService.format_preference_context(self, items: list[dict[str, Any]])` -> `str | None`
- method: `UserPreferenceMemoryService._infer_scope(self, lowered_text: str)` -> `str`
- method: `UserPreferenceMemoryService._infer_stability_score(self, lowered_text: str)` -> `float`
- method: `UserPreferenceMemoryService._normalize_instruction_text(self, text: str)` -> `str`
- method: `UserPreferenceMemoryService._dedupe_key(self, *, preference_kind: str, instruction_text: str)` -> `str`
- method: `UserPreferenceMemoryService._normalize_for_hash(self, text: str)` -> `str`
- method: `UserPreferenceMemoryService._preference_exists(self, *, dedupe_key: str)` -> `bool`
- method: `UserPreferenceMemoryService._deactivate_scope_conflicts(self, *, scope: str, keep_dedupe_key: str)` -> `None`
- method: `UserPreferenceMemoryService._build_preference_content(self, *, preference_kind: str, instruction_text: str)` -> `str`
- method: `UserPreferenceMemoryService._point_to_preference_item(self, point: Any)` -> `dict[str, Any]`
- method: `UserPreferenceMemoryService._coerce_ts_ms(self, value: Any | None)` -> `int | None`
- method: `UserPreferenceMemoryService._preference_rank(self, item: dict[str, Any])` -> `float`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
