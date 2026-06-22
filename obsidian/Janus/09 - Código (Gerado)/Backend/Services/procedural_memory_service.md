---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/procedural_memory_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# procedural_memory_service

## Arquivos-fonte
- `backend/app/services/procedural_memory_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/active_memory_service.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/rag_service.py`

## Símbolos
- class: `ProceduralMemoryService`
  - Stores recurring work instructions as durable user procedures.
- method: `ProceduralMemoryService.should_inspect_message(self, message: str)` -> `bool`
- method: `ProceduralMemoryService.extract_rule(self, message: str)` -> `dict[str, Any] | None`
- method: `ProceduralMemoryService.maybe_capture_from_message(self, *, message: str, conversation_id: str | None, user_id: str, threshold: float = 0.8)` -> `dict[str, Any] | None`
- method: `ProceduralMemoryService.list_rules(self, *, conversation_id: str | None = None, limit: int = 10, active_only: bool = True, query: str | None = None)` -> `list[dict[str, Any]]`
- method: `ProceduralMemoryService.format_procedural_context(self, items: list[dict[str, Any]])` -> `str | None`
- method: `ProceduralMemoryService._rule_exists(self, *, dedupe_key: str)` -> `bool`
- method: `ProceduralMemoryService._deactivate_scope_conflicts(self, *, scope: str, keep_dedupe_key: str)` -> `None`
- method: `ProceduralMemoryService._normalize_instruction_text(self, text: str)` -> `str`
- method: `ProceduralMemoryService._infer_scope(self, lowered_text: str)` -> `str`
- method: `ProceduralMemoryService._infer_procedure_kind(self, lowered_text: str)` -> `str`
- method: `ProceduralMemoryService._normalize_for_hash(self, text: str)` -> `str`
- method: `ProceduralMemoryService._dedupe_key(self, *, scope: str, instruction_text: str)` -> `str`
- method: `ProceduralMemoryService._point_to_rule_item(self, point: Any)` -> `dict[str, Any]`
- method: `ProceduralMemoryService._coerce_ts_ms(self, value: Any | None)` -> `int | None`
- method: `ProceduralMemoryService._rule_rank(self, item: dict[str, Any])` -> `float`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
