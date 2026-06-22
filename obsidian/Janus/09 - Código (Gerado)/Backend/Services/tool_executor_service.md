---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/tool_executor_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# tool_executor_service

## Arquivos-fonte
- `backend/app/services/tool_executor_service.py`

## Dependências de código
- Repositórios
  - `observability_repository`
  - `pending_action_repository`
  - `tool_usage_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/core/workers/codex_worker.py`
- `backend/app/services/chat_service.py`

## Símbolos
- class: `ToolExecutorError`
  - Erro base para execuÃ§Ã£o de ferramentas.
- class: `ToolExecutorService`
  - Service responsible for parsing tool calls from LLM output and executing them.
- method: `ToolExecutorService.__init__(self, max_concurrency: int | None = None, timeout_seconds: float | None = None)`
- method: `ToolExecutorService._parse_max_concurrency(self, max_concurrency: int | None)` -> `int`
- method: `ToolExecutorService._parse_timeout_seconds(self, timeout_seconds: float | None)` -> `float | None`
- method: `ToolExecutorService._build_default_policy(self)` -> `PolicyEngine`
- method: `ToolExecutorService._extract_json_envelope_payload(self, text: str)` -> `str | None`
- method: `ToolExecutorService.parse_tool_calls(self, text: str)` -> `list[dict[str, Any]]`
  - Extract tool calls using strict JSON envelope.
- method: `ToolExecutorService._validate_tool_args(self, *, tool: Any, args: Any)` -> `tuple[bool, dict[str, Any] | Any, str | None]`
  - Validate tool arguments using its Pydantic args_schema when available.
- method: `ToolExecutorService._audit_pre_execution_event(self, *, tool_name: str, status: str, reason: str, user_id: str | None = None, detail: dict[str, Any] | None = None)` -> `None`
- method: `ToolExecutorService._simulation_to_storage(self, simulation: SimulationResult | None)` -> `tuple[str | None, str | None]`
- method: `ToolExecutorService._build_scope_metadata(self, args: dict[str, Any] | Any)` -> `tuple[str | None, list[str]]`
- method: `ToolExecutorService._create_pending_action(self, *, user_id: str | None, tool_name: str, safe_args: dict[str, Any] | Any, simulation: SimulationResult | None = None)` -> `int | None`
- method: `ToolExecutorService.execute_tool_calls(self, calls: list[dict[str, Any]], strict: bool = True, policy: PolicyEngine | None = None, user_id: str | None = None, project_id: str | None = None, timeout_seconds: float | None = None)` -> `list[dict[str, str]]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
