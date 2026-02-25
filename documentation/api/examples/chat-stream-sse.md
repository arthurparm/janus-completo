# Exemplo SSE (`/api/v1/chat/stream/{conversation_id}`)

```text
event: start

event: protocol
data: {"version":"2025-11.v1","supports_partial":true,"deprecate_partial_at":"2026-03-01"}

event: ack
data: {"conversation_id":"conv-123"}

event: cognitive_status
data: {"state":"thinking","timestamp":1772040806758}

event: partial
data: {"text":"Pedido classificado como alto risco.","timestamp":1772040806780}

event: cognitive_status
data: {"state":"waiting_confirmation","requires_confirmation":true,"reason":"high_risk","timestamp":1772040806890}

event: done
data: {"conversation_id":"conv-123","provider":"janus","model":"agent","citations":[],"citation_status":{"mode":"optional","status":"not_applicable","count":0,"reason":null},"understanding":{"intent":"action_request","summary":"execute deploy","requires_confirmation":true,"confirmation_reason":"high_risk","confirmation":{"required":true,"reason":"high_risk","source":"pending_actions_sql","pending_action_id":123,"approve_endpoint":"/api/v1/pending_actions/action/123/approve","reject_endpoint":"/api/v1/pending_actions/action/123/reject"}},"confirmation":{"required":true,"reason":"high_risk","source":"pending_actions_sql","pending_action_id":123,"approve_endpoint":"/api/v1/pending_actions/action/123/approve","reject_endpoint":"/api/v1/pending_actions/action/123/reject"},"agent_state":{"state":"waiting_confirmation","requires_confirmation":true,"reason":"high_risk"}}
```

## Exemplo `event:error`

```text
event: error
data: {"code":"CHAT_STREAM_TIMEOUT","message":"TTFT timeout","category":"timeout","retryable":true,"http_status":null,"details":{"phase":"ttft"},"error":"TTFT timeout"}
```

