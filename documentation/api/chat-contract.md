# Chat Contract (REST + SSE) — Demo Agentic Flow

## Endpoints cobertos
- `POST /api/v1/chat/start`
- `POST /api/v1/chat/message`
- `GET /api/v1/chat/stream/{conversation_id}` (SSE)
- `GET /api/v1/chat/{conversation_id}/events` (eventos de agentes / observabilidade)

## Compatibilidade
- Contrato **aditivo** (retrocompatível com frontend atual)
- Campos legados permanecem
- Novos campos recomendados:
  - `citation_status`
  - `understanding.confirmation`
  - `understanding.risk`
  - `agent_state`
  - `confirmation`

## `POST /api/v1/chat/start`
### Request
- `persona?`
- `user_id?`
- `project_id?`
- `title?`

### Response
- `conversation_id` (obrigatório)
- `created_at?`
- `updated_at?`

## `POST /api/v1/chat/message`
### Request
- `conversation_id` (obrigatório)
- `message` (obrigatório)
- `role?`
- `priority?`
- `timeout_seconds?`
- `user_id?`
- `project_id?`

### Response (campos principais)
- `response`
- `provider`
- `model`
- `role`
- `conversation_id`
- `citations` (lista)
- `citation_status` (novo)
- `understanding` (objeto tipado, compatível com legado)
- `confirmation?` (novo; espelho simplificado)
- `agent_state?` (novo; resumo visual)
- `ui?`

### `citation_status`
```json
{
  "mode": "required|optional",
  "status": "present|missing_required|not_applicable|retrieval_failed",
  "count": 0,
  "reason": "no_retrievable_sources"
}
```

### `understanding` (shape estável)
Campos esperados:
- `intent`
- `summary`
- `confidence?`
- `confidence_band?`
- `low_confidence?`
- `requires_confirmation?`
- `confirmation_reason?`
- `signals?`
- `routing?`
- `risk?`
- `confirmation?`

### `understanding.confirmation` (preferido)
```json
{
  "required": true,
  "reason": "high_risk|low_confidence|requires_confirmation",
  "source": "pending_actions_sql",
  "pending_action_id": 123,
  "approve_endpoint": "/api/v1/pending_actions/action/123/approve",
  "reject_endpoint": "/api/v1/pending_actions/action/123/reject"
}
```

## `GET /api/v1/chat/stream/{conversation_id}` (SSE)
### Query params
- `message` (obrigatório)
- `role?`
- `priority?`
- `timeout_seconds?`
- `user_id?`
- `project_id?`

### Eventos suportados
- `start`
- `protocol`
- `heartbeat`
- `ack`
- `token`
- `partial`
- `tool_status` (opcional)
- `cognitive_status` (opcional)
- `done`
- `error`

### Payloads
#### `protocol`
```json
{
  "version": "2025-11.v1",
  "supports_partial": true,
  "deprecate_partial_at": "2026-03-01"
}
```

#### `ack`
```json
{
  "conversation_id": "10"
}
```

#### `token` / `partial`
```json
{
  "text": "chunk",
  "timestamp": 1772040806758
}
```

#### `cognitive_status` (opcional)
```json
{
  "state": "thinking|streaming_response|waiting_confirmation|completed|error",
  "confidence_band": "low|medium|high",
  "requires_confirmation": true,
  "reason": "high_risk",
  "timestamp": 1772040806758
}
```

#### `tool_status` (opcional)
```json
{
  "phase": "planning|calling|done|blocked",
  "tool_name": "exec_command",
  "status": "pending_confirmation",
  "pending_action_id": 123,
  "risk_level": "high",
  "message": "Tool requires confirmation before execution."
}
```

#### `done`
Contém os mesmos campos de interesse do REST:
- `conversation_id`
- `provider`
- `model`
- `citations`
- `citation_status`
- `understanding?`
- `confirmation?`
- `agent_state?`
- `ui?`

#### `error`
Payload canônico com compat legado:
```json
{
  "code": "CHAT_INVOCATION_ERROR",
  "message": "Internal server error",
  "category": "internal",
  "retryable": true,
  "http_status": null,
  "details": {},
  "error": "Internal server error"
}
```

## `GET /api/v1/chat/{conversation_id}/events`
- Fluxo de eventos de observabilidade do agente (tool calls, thinking, etc.)
- Mantido como canal complementar para UX/observabilidade

