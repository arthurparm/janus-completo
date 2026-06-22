# Chat Critical Audit Log

Data: 2026-06-22

## Escopo

Auditoria focada na funcionalidade de chat backend: endpoints REST/SSE, facade `ChatService`, serviços de conversa/orquestração/streaming, repositórios de chat e testes unitários de contrato.

## Ciclo 1 - Contrato de `user_id` quebrado no fluxo central de chat

### Problema

- Categoria: segurança, disponibilidade e experiência central do usuário.
- Fato observado: endpoints de chat passavam `user_id` para `ChatService`, mas o facade e `ConversationService` não aceitavam esse parâmetro em vários métodos centrais.
- Fato observado: `ConversationService.validate_conversation_access` validava apenas `project_id`, não `user_id`.
- Impacto antes: chamadas reais poderiam falhar com `TypeError` ou permitir leitura/operação quando apenas o `project_id` não distinguia usuários.

### Hipótese

Acredito que propagar e validar `user_id` em toda a cadeia endpoint -> facade -> service -> repository reduz falhas 500 por incompatibilidade de assinatura e fecha uma classe de acesso cruzado entre conversas, porque o dono da conversa passa a ser parte explícita do contrato.

### Implementação

- `ChatService` passou a aceitar e repassar `user_id` nos métodos de envio, histórico, listagem, CRUD, streaming e eventos.
- `ConversationService` passou a validar mismatch de `user_id` quando conversa e requisição têm usuário resolvido.
- Repositórios fallback/file passaram a armazenar, filtrar e validar `user_id`.
- `MessageOrchestrationService`, `StreamingService` e `ActiveMemoryService` foram alinhados ao mesmo contrato.
- Chamadas síncronas de LLM em streaming passaram a usar keywords e fallback compatível para implementações antigas sem `user_id`.

### Métricas

- Baseline medido: `backend/tests/unit/test_conversation_service.py` falhava 2/4 testes por ausência de validação/delegação de `user_id`.
- Depois: conjunto focado de chat passou 16/16 testes.
- Regressão coberta: mismatch de `user_id`, delegação CRUD com `user_id`, SSE token/done, erro de mensagem grande, UTF-8/heartbeat e metadados de repositório.

### Riscos e limitações

- O repositório SQL já continha alterações locais de governança/retenção antes desta auditoria; elas foram preservadas.
- Warnings de `datetime.utcnow()` permanecem no fallback SQL; não foram corrigidos por estarem fora do defeito crítico selecionado.
- Alguns testes unitários ainda logam falhas de infraestrutura externa quando não totalmente mockados; o conjunto final isola os caminhos críticos usados.

## Ciclo 2 - Trace de conversa retornava antes de autorização

### Problema

- Categoria: segurança.
- Fato observado: `GET /api/v1/chat/{conversation_id}/trace` executava `return service.get_trace(conversation_id)` antes de resolver identidade e validar acesso à conversa.
- Impacto antes: o trace poderia ser retornado sem chamar `chat_service.get_history`, bypassando autorização por conversa.

### Hipótese

Acredito que mover o retorno do trace para depois da validação de acesso elimina vazamento de trace entre conversas, porque o endpoint só consulta `TraceService` após `get_history` confirmar autorização.

### Implementação

- Removido retorno prematuro em `chat_stream.py`.
- O endpoint agora resolve identidade, valida acesso à conversa via `chat_service.get_history(...)` e só então retorna `service.get_trace(conversation_id)`.
- Adicionado teste que força `ChatServiceError("Access denied")` e verifica `403` sem chamada ao `TraceService`.

### Métricas

- Baseline observado: caminho de autorização era inalcançável no código.
- Depois: teste `test_trace_endpoint_checks_chat_access_before_returning_trace` passa, confirmando 1 chamada de histórico e 0 chamadas ao trace em acesso negado.

### Riscos e limitações

- Em modo de transição, a política global de autenticação ainda depende de `CHAT_AUTH_ENFORCE_REQUIRED`; esta correção garante autorização quando o serviço de chat nega acesso.
- Não foi executado teste full-stack com PC2/PC1 por escopo e custo operacional.

## Validação executada

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/chat/chat_stream.py backend/app/services/chat_service.py backend/app/services/chat/conversation_service.py backend/app/services/chat/message_orchestration_service.py backend/app/services/chat/streaming_service.py backend/app/services/active_memory_service.py backend/app/repositories/chat_repository.py backend/app/repositories/chat_repository_sql.py backend/tests/unit/test_chat_trace_access.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_chat_streaming_service.py backend/tests/unit/test_chat_service_stream.py backend/tests/unit/test_chat_service_utf8_heartbeat.py backend/tests/unit/test_conversation_service.py backend/tests/unit/test_chat_repository_sql_metadata.py backend/tests/unit/test_chat_trace_access.py
```

Resultado: 16 passed, 15 warnings.

## Decisão

Recomendação: manter as correções. Confiança: média-alta para os contratos corrigidos, limitada por ausência de validação full-stack com infraestrutura PC2 ativa.
