# Chat Error Matrix (REST + SSE)

## Objetivo
Definir códigos estáveis para erros/estados do chat de forma renderizável no frontend.

## Convenções
- REST: `HTTPException.detail` inclui objeto canônico com `code`, `message`, `category`, `retryable`, `http_status`
- SSE (`event:error`): payload canônico com os mesmos campos e compat legado `error`

## Matriz
| Código | Transporte | HTTP | Categoria | Retryable | Cenário |
|---|---|---:|---|---|---|
| `CHAT_AUTH_REQUIRED` | REST | 401 | `auth` | Não | Usuário não autenticado |
| `CHAT_ACCESS_DENIED` | REST/SSE | 403 | `authz` | Não | Conversa/ação sem permissão |
| `CHAT_CONVERSATION_NOT_FOUND` | REST/SSE | 404 | `not_found` | Não | Conversa inexistente |
| `CHAT_MESSAGE_TOO_LARGE` | REST/SSE | 413 | `validation` | Não | Mensagem acima do limite |
| `CHAT_INVALID_ROLE_OR_PRIORITY` | REST | 422 | `validation` | Não | Role/prioridade inválidos |
| `CHAT_STREAM_TIMEOUT` | SSE | - | `timeout` | Sim | Timeout de TTFT/stream |
| `CHAT_CIRCUIT_OPEN` | SSE | - | `availability` | Sim | Circuit breaker aberto |
| `CHAT_INVOCATION_ERROR` | REST/SSE | 500/- | `internal` | Sim | Falha interna na invocação |
| `CHAT_EVENT_STREAM_START_FAILED` | REST | 500 | `internal` | Sim | Falha ao iniciar stream de eventos |

## Estado não-erro (documentado)
### `pending_confirmation_required`
- Não deve ser modelado como erro
- Deve aparecer em `understanding.confirmation.required = true`
- Pode incluir `pending_action_id` e endpoints de aprovar/rejeitar

## Ação recomendada no frontend por categoria
- `auth`: redirecionar login / renovar sessão
- `authz`: mostrar acesso negado sem retry automático
- `not_found`: sugerir recriar conversa
- `validation`: destacar input inválido
- `timeout`/`availability`/`internal`: permitir retry

