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

## Ciclo 3 - `project_id` do cliente sobrescrevia escopo autenticado

### Problema

- Categoria: segurança e isolamento multi-projeto.
- Fato observado: endpoints de start, message, rename, delete, list, stream e events aceitavam `project_id` do payload/query mesmo quando `request.state.actor_project_id` estava disponível.
- Impacto antes: um usuário autenticado no projeto A podia induzir a camada de chat a executar validação ou operação usando projeto B fornecido pelo cliente. O risco é maior em contas com acesso a múltiplos projetos e em conversas legadas com escopo incompleto.

### Hipótese

Acredito que dar precedência ao `actor_project_id` autenticado reduz bypass de escopo de projeto, porque o cliente deixa de controlar o parâmetro usado em validação e delegação para service/repository quando o middleware já resolveu o projeto do ator.

### Implementação

- `chat_message.py`: start e message passam a usar `actor_project_id(http) or payload.project_id`.
- `chat_admin.py`: rename e delete passam a usar `actor_project_id(http) or project_id_do_cliente`.
- `chat_history.py`: listagem passa a filtrar por `actor_project_id(http) or project_id`.
- `chat_stream.py`: stream passa a sobrescrever query `project_id` com `actor_project_id(http)` quando disponível; events passa a validar histórico com projeto autenticado.
- Adicionado `backend/tests/unit/test_chat_project_scope.py` cobrindo start, message, rename, delete, list, stream e events.

### Métricas

- Baseline observado: código usava `payload.project_id`/query diretamente em vários endpoints.
- Depois: `backend/tests/unit/test_chat_project_scope.py` passou 2/2; validação acumulada de chat passou 18/18.
- Cobertura de regressão: sete caminhos de endpoint provam que `project-from-auth` prevalece sobre `client-supplied-project`.

### Riscos e limitações

- Mantido fallback para `project_id` do cliente quando não existe `actor_project_id` no request, para preservar modo de transição/local.
- Não foi validado com middleware real de autenticação em ambiente PC1/PC2.

## Ciclo 4 - `/chat/message` rejeitava fallback anônimo exigido pelos contratos

### Problema

- Categoria: disponibilidade funcional e experiência central do usuário.
- Fato observado: a suíte `qa/test_chat_endpoint_contract.py` falhava em 5 testes porque `/api/v1/chat/message` retornava `401` quando não havia ator nem usuário explícito, mesmo com modo de transição sem `CHAT_AUTH_ENFORCE_REQUIRED`.
- Impacto antes: fluxos compatíveis de chat em modo transição deixavam de responder no endpoint central de mensagem.

### Hipótese

Acredito que habilitar `allow_anonymous_fallback=True` apenas em `/chat/message` restaura a compatibilidade contratual sem enfraquecer o modo estrito, porque `resolve_authenticated_user_context` continua retornando usuário ausente quando `CHAT_AUTH_ENFORCE_REQUIRED` está ativo.

### Implementação

- `chat_message.py`: `send_message` passou a chamar `resolve_authenticated_user_context(..., allow_anonymous_fallback=True, ...)`.
- O endpoint continua retornando `401` se a política estrita exigir autenticação e nenhum ator autenticado estiver presente.

### Métricas

- Baseline medido: `qa/test_chat_endpoint_contract.py qa/test_chat_history_contract.py qa/test_chat_stream_sse_contract.py` resultou em 5 failed, 18 passed.
- Depois: a mesma suíte resultou em 23 passed.
- Cobertura de regressão: fallback anônimo, citações obrigatórias, confirmação de baixa confiança e prevenção de pending study voltaram a passar.

### Riscos e limitações

- O fallback anônimo permanece uma decisão de compatibilidade de transição; a decisão operacional de exigir autenticação continua centralizada em `CHAT_AUTH_ENFORCE_REQUIRED`.
- Não foi alterado `/chat/start`, que segue exigindo identidade resolvida.

## Ciclo 5 - Orquestrador de mensagem quebrava em validação de acesso e contratos de confirmação

### Problema

- Categoria: disponibilidade funcional, segurança e experiência central do usuário.
- Fato observado: a bateria ampla de chat unitário resultou em 18 failed, 35 passed.
- Fato observado: 15 falhas vinham de `MessageOrchestrationService.send_message` chamando `validate_conversation_access` com o novo contrato posicional, quebrando implementações/fakes que ainda aceitavam apenas `project_id`.
- Fato observado: contratos de confirmação também divergiam: `high_risk` podia gerar payload de confirmação sem `pending_action_id` real, enquanto baixa confiança precisava continuar exibindo confirmação heurística.
- Fato observado: `generate_secret_recall_reply` ignorava `user_id` da chamada quando a conversa não tinha `user_id` persistido, quebrando recall autorizado em conversas legadas.

### Hipótese

Acredito que encapsular a validação de acesso em helper compatível por keyword, exigir escopo explícito de usuário em pending action/secret recall e separar confirmação heurística de baixa confiança da confirmação de alto risco elimina falhas centrais de envio sem abrir bypass de autorização.

### Implementação

- `MessageOrchestrationService` ganhou `_validate_conversation_access(...)` com chamada keyword e fallback para contrato legado.
- Secret recall passa a usar `user_id` efetivo da requisição ou dono persistido da conversa.
- `maybe_create_fallback_pending_action(...)` passou a aceitar `user_id` e propagá-lo no payload/kwargs quando disponível, com fallback para o repositório atual que ainda não possui coluna de usuário.
- `build_confirmation_payload(...)` não cria confirmação acionável para `high_risk` sem `pending_action_id`; baixa confiança continua permitindo confirmação heurística.
- `build_understanding_payload(...)` passou a classificar perguntas iniciadas por `consegue`/`pode` como `question`.
- Testes de contrato foram ajustados para explicitar `user_id` quando há pending action ou recall de segredo.

### Métricas

- Baseline medido: bateria ampla unitária de chat resultou em 18 failed, 35 passed.
- Depois: a mesma bateria resultou em 53 passed, 15 warnings.
- Contratos QA HTTP/SSE depois: 24 passed, 2 warnings.
- Gates estáticos do ciclo: `ruff check` passou; `py_compile` passou.

### Riscos e limitações

- O fallback de `PendingActionRepository.create(...)` sem `user_id` preserva compatibilidade com o modelo atual, mas o `user_id` ainda não é coluna persistida em `pending_actions`.
- Warnings de `datetime.utcnow()` e depreciação FastAPI `HTTP_413_REQUEST_ENTITY_TOO_LARGE` permanecem fora do defeito selecionado.
- Não foi executado full-stack PC2/PC1.

## Ciclo 6 - Gate estático de chat falhava em arquivos de backend

### Problema

- Categoria: qualidade de entrega e prontidão de CI.
- Fato observado: `ruff check` amplo sobre arquivos de chat falhava em 28 ocorrências.
- Fato observado: os erros eram todos auto-corrigíveis por ordenação de imports e remoção de whitespace em branco.
- Impacto antes: mesmo com testes verdes, a linha de desenvolvimento do módulo de chat não satisfazia o contrato operacional de quality gates do projeto.

### Hipótese

Acredito que aplicar `ruff --fix` apenas nos arquivos reportados elimina uma falha bloqueadora de CI sem alterar comportamento de runtime, porque os diagnósticos são mecânicos e classificados pelo próprio ruff como auto-corrigíveis.

### Implementação

- Aplicado `ruff --fix` em `backend/app/api/v1/endpoints/chat/__init__.py`, `backend/app/services/chat/chat_citation_service.py`, testes unitários de chat e contratos QA de chat reportados.
- Nenhuma lógica funcional foi alterada neste ciclo.

### Métricas

- Baseline medido: 28 erros de `ruff`.
- Depois: `ruff check` amplo de chat resultou em `All checks passed`.
- Regressão comportamental: testes backend afetados resultaram em 20 passed, 2 warnings.

### Riscos e limitações

- A mudança é mecânica, mas toca arquivos de teste/contrato; por isso os testes afetados foram executados.
- Não substitui validação full-stack.

## Ciclo 7 - Frontend ocultava confirmação de baixa confiança sem pending action

### Problema

- Categoria: experiência central do usuário e segurança operacional.
- Fato observado: os testes frontend existentes passavam 17/17, mas não cobriam confirmação heurística de baixa confiança.
- Fato observado: o backend retorna confirmação `low_confidence` sem `pending_action_id`, mas `ConversationsComponent.messageConfirmation(...)` descartava toda confirmação sem pending action ou endpoints.
- Impacto antes: o usuário podia receber uma resposta pedindo confirmação, mas o cartão de confirmação da UI não aparecia; isso torna o fluxo de baixa confiança inconsistente e menos auditável.

### Hipótese

Acredito que permitir a exibição de confirmação heurística apenas para `low_confidence`, mantendo `high_risk` dependente de ação pendente estruturada, corrige a UX sem criar botões de aprovação falsos para ações perigosas.

### Implementação

- `conversations.ts`: `messageConfirmation(...)` agora aceita confirmação sem `pending_action_id` quando `reason === "low_confidence"` ou `understanding.low_confidence === true`.
- `conversations.spec.ts`: adicionados testes que provam que baixa confiança heurística fica visível e alto risco sem pending action continua oculto.

### Métricas

- Baseline inferido por leitura: `messageConfirmation(...)` retornava `null` para qualquer confirmação sem pending action/endpoints.
- Depois: `conversations.spec.ts` passou 4/4.
- Bateria frontend focada de chat: 5 arquivos, 19 testes, todos passaram.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.

### Riscos e limitações

- Validação foi por teste de componente e build; não houve browser renderizado com screenshot neste ciclo.
- Os testes frontend ainda são majoritariamente unitários e não substituem um e2e real do fluxo completo de chat.

## Ciclo 8 - Loop agente reexecutava lote de tools apos excecao do executor

### Problema

- Categoria: seguranca operacional e disponibilidade.
- Fato observado: `_execute_tools_with_fallback(...)` tentava o mesmo lote de tool calls uma segunda vez com `strict=False` quando `execute_tool_calls(...)` levantava excecao.
- Baseline medido: o teste de regressao novo falhou com `len(tool_executor.calls) == 2`; a segunda chamada incluia `strict=False`.
- Impacto antes: se o executor falhasse depois de uma acao parcial, uma tool com efeito colateral poderia ser chamada novamente, duplicando mutacoes ou efeitos externos.

### Hipotese

Acredito que remover o retry permissivo do mesmo lote reduz risco de duplicacao de efeitos colaterais, porque falhas internas passam a degradar para resposta minima sem reexecutar tool calls.

### Implementacao

- `chat_agent_loop.py`: removido o strategy `fallback_permissive`; a cadeia agora usa apenas execucao primaria e `minimal_fallback`.
- `qa/test_chat_agent_loop_content_safety.py`: adicionado teste que injeta falha no executor e comprova que o lote de tools e chamado uma unica vez.

### Metricas

- Baseline medido antes da correcao: `qa/test_chat_agent_loop_content_safety.py` resultou em 1 failed, 2 passed; o executor foi chamado 2 vezes.
- Depois: suite focada de loop/politica/tools resultou em 22 passed.
- Gate estatico: `ruff check` dos arquivos tocados e contratos de politica resultou em `All checks passed`.
- Compilacao Python dos arquivos tocados passou.

### Riscos e limitacoes

- Trade-off: erros transitorios do executor nao sao mais retentados automaticamente no nivel do chat agent loop.
- Decisao de engenharia: esse trade-off e aceitavel porque retries de operacoes potencialmente mutaveis precisam ser idempotentes ou controlados por politica explicita, nao por fallback generico.
- Nao foi executado teste com tools reais e infraestrutura externa.

## Ciclo 9 - Study job podia ser consultado sem identidade em modo de transicao

### Problema

- Categoria: seguranca e privacidade da resposta de chat.
- Fato observado: `/api/v1/chat/study-jobs/{job_id}` resolvia identidade com `allow_anonymous_fallback=False`; em modo de transicao sem ator autenticado, `user_id` ficava `None`.
- Baseline medido: o teste novo retornou HTTP 200 para um job com `user_id="victim-user"` acessado sem identidade autenticada.
- Impacto antes: qualquer cliente que conhecesse ou adivinhasse um `job_id` poderia consultar `final_response`, erro, progresso e metadados de conversa de outro usuario quando a autenticacao estrita nao estivesse habilitada.

### Hipotese

Acredito que resolver identidade anonima tambem no endpoint de polling e negar acesso quando o job pertence a outro usuario elimina o vazamento sem quebrar o fluxo de transicao, porque o mesmo cliente anonimo ainda recebe um identificador estavel por IP e user-agent.

### Implementacao

- `chat_study_jobs.py`: o endpoint passou a chamar `resolve_authenticated_user_context(..., allow_anonymous_fallback=True)`.
- `chat_study_jobs.py`: se a identidade continuar ausente, o endpoint retorna `401` independentemente de `CHAT_AUTH_ENFORCE_REQUIRED`.
- `chat_study_jobs.py`: a verificacao de propriedade deixou de depender de `user_id is not None`; jobs de outro usuario exigem historico acessivel para o usuario resolvido.
- `qa/test_chat_endpoint_contract.py`: adicionado teste que prova que acesso anonimo a job de outro usuario retorna `403` e aciona validacao de historico.

### Metricas

- Baseline antes da correcao: `test_chat_study_job_denies_anonymous_access_to_other_user_job` falhou porque recebeu HTTP 200.
- Depois: o teste isolado passou.
- Contratos HTTP/SSE de chat depois: 25 passed, 2 warnings.
- Gate estatico: `ruff check` passou.
- Compilacao Python dos arquivos tocados passou.

### Riscos e limitacoes

- Trade-off: clientes sem IP/user-agent resolvivel recebem `401` no polling de study job mesmo em transicao.
- Decisao de engenharia: esse trade-off e aceitavel porque `final_response` pode conter conteudo privado da conversa.
- Nao foi validado em browser real com polling de study job anonimo.

## Ciclo 10 - Endpoints de conversa existente podiam atravessar autorizacao com `user_id=None`

### Problema

- Categoria: seguranca, privacidade e isolamento de conversas.
- Fato observado: `ConversationService.validate_conversation_access(...)` so bloqueia mismatch quando `user_id` esta preenchido.
- Fato observado: endpoints de history, paginated history, list, rename, delete, stream, trace e events resolviam `user_id=None` em modo de transicao quando nao havia ator autenticado.
- Baseline medido: `test_chat_stream_denies_anonymous_access_to_other_user_conversation` falhou porque `/api/v1/chat/stream/conv-victim` retornou HTTP 200 para conversa de outro usuario.
- Impacto antes: endpoints que operam sobre conversas existentes podiam ler, streamar ou mutar conversas com dono persistido quando a requisicao chegava sem identidade resolvida.

### Hipotese

Acredito que resolver fallback anonimo estavel para endpoints de conversa existente elimina o bypass por `None`, porque a autorizacao passa a comparar um usuario concreto contra o dono persistido da conversa.

### Implementacao

- `chat_history.py`: history, history paginated e listagem de conversas passaram a usar `allow_anonymous_fallback=True` e retornar `401` se nenhuma identidade for resolvida.
- `chat_admin.py`: rename e delete passaram a usar `allow_anonymous_fallback=True` e retornar `401` se nenhuma identidade for resolvida.
- `chat_stream.py`: stream, trace e events passaram a usar `allow_anonymous_fallback=True` e retornar `401` se nenhuma identidade for resolvida.
- `qa/test_chat_endpoint_contract.py`: adicionado teste que simula a semantica real de `validate_conversation_access`, onde `None` nao bloqueia e um anonimo divergente bloqueia.

### Metricas

- Baseline antes da correcao: teste novo de stream retornou HTTP 200 em vez de 403.
- Depois: teste isolado passou.
- Bateria focada de endpoints de chat: 29 passed, 2 warnings.
- Gate estatico: `ruff check` passou.
- Compilacao Python dos arquivos tocados passou.

### Riscos e limitacoes

- Trade-off: clientes sem IP/user-agent resolvivel passam a receber `401` em endpoints de conversa existente mesmo em transicao.
- Decisao de engenharia: esse trade-off e aceitavel porque endpoints sobre conversas existentes nao devem operar sem identidade comparavel.
- O endpoint `/chat/start` nao foi alterado neste ciclo; conversas novas sem dono continuam sendo uma compatibilidade legada separada.

## Validação executada

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/chat/chat_stream.py backend/app/services/chat_service.py backend/app/services/chat/conversation_service.py backend/app/services/chat/message_orchestration_service.py backend/app/services/chat/streaming_service.py backend/app/services/active_memory_service.py backend/app/repositories/chat_repository.py backend/app/repositories/chat_repository_sql.py backend/tests/unit/test_chat_trace_access.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_chat_streaming_service.py backend/tests/unit/test_chat_service_stream.py backend/tests/unit/test_chat_service_utf8_heartbeat.py backend/tests/unit/test_conversation_service.py backend/tests/unit/test_chat_repository_sql_metadata.py backend/tests/unit/test_chat_trace_access.py
```

Resultado: 16 passed, 15 warnings.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/chat/chat_admin.py backend/app/api/v1/endpoints/chat/chat_history.py backend/app/api/v1/endpoints/chat/chat_message.py backend/app/api/v1/endpoints/chat/chat_stream.py backend/tests/unit/test_chat_project_scope.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/chat/chat_admin.py backend/app/api/v1/endpoints/chat/chat_history.py backend/app/api/v1/endpoints/chat/chat_message.py backend/app/api/v1/endpoints/chat/chat_stream.py backend/tests/unit/test_chat_project_scope.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_chat_streaming_service.py backend/tests/unit/test_chat_service_stream.py backend/tests/unit/test_chat_service_utf8_heartbeat.py backend/tests/unit/test_conversation_service.py backend/tests/unit/test_chat_repository_sql_metadata.py backend/tests/unit/test_chat_trace_access.py backend/tests/unit/test_chat_project_scope.py
```

Resultado: 18 passed, 15 warnings.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py qa/test_chat_history_contract.py qa/test_chat_stream_sse_contract.py
```

Resultado: 23 passed.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_chat_about_identity.py backend/tests/unit/test_chat_contracts_confirmation.py backend/tests/unit/test_chat_deps_identity.py backend/tests/unit/test_chat_endpoints_subrouters.py backend/tests/unit/test_chat_project_scope.py backend/tests/unit/test_chat_repository_sql_metadata.py backend/tests/unit/test_chat_service_event_publisher_wiring.py backend/tests/unit/test_chat_service_stream.py backend/tests/unit/test_chat_service_utf8_heartbeat.py backend/tests/unit/test_chat_streaming_service.py backend/tests/unit/test_chat_trace_access.py backend/tests/unit/test_chat_ui_split.py backend/tests/unit/test_services_chat_citation_service.py backend/tests/unit/test_services_chat_message_helpers.py backend/tests/unit/test_message_orchestration_service.py
```

Resultado: 53 passed, 15 warnings.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py qa/test_chat_history_contract.py qa/test_chat_stream_sse_contract.py qa/test_chat_error_matrix.py
```

Resultado: 24 passed, 2 warnings.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/chat backend/app/services/chat backend/app/services/chat_service.py backend/tests/unit/test_chat_about_identity.py backend/tests/unit/test_chat_contracts_confirmation.py backend/tests/unit/test_chat_deps_identity.py backend/tests/unit/test_chat_endpoints_subrouters.py backend/tests/unit/test_chat_project_scope.py backend/tests/unit/test_chat_repository_sql_metadata.py backend/tests/unit/test_chat_service_event_publisher_wiring.py backend/tests/unit/test_chat_service_stream.py backend/tests/unit/test_chat_service_utf8_heartbeat.py backend/tests/unit/test_chat_streaming_service.py backend/tests/unit/test_chat_trace_access.py backend/tests/unit/test_chat_ui_split.py backend/tests/unit/test_services_chat_citation_service.py backend/tests/unit/test_services_chat_message_helpers.py backend/tests/unit/test_message_orchestration_service.py qa/test_chat_agent_loop_content_safety.py qa/test_chat_agent_loop_policy_settings.py qa/test_chat_endpoint_contract.py qa/test_chat_error_matrix.py qa/test_chat_history_contract.py qa/test_chat_history_line_coverage.py qa/test_chat_stream_sse_contract.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_chat_about_identity.py backend/tests/unit/test_services_chat_citation_service.py qa/test_chat_history_contract.py qa/test_chat_history_line_coverage.py qa/test_chat_stream_sse_contract.py qa/test_chat_error_matrix.py
```

Resultado: 20 passed, 2 warnings.

```powershell
npm run test -- src/app/services/domain/chat-api-service.contract.spec.ts src/app/services/chat-auth-headers.util.spec.ts src/app/features/conversations/conversations.spec.ts src/app/features/conversations/conversations-flows.spec.ts src/app/features/conversations/admin-code-qa.util.spec.ts
```

Resultado: 19 passed.

```powershell
npm run lint
```

Resultado: passou.

```powershell
npx ng build --configuration development
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_agent_loop_content_safety.py
```

Resultado baseline antes da correcao: 1 failed, 2 passed. Falha esperada: o executor era chamado 2 vezes apos excecao.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_agent_loop_content_safety.py qa/test_chat_agent_loop_policy_settings.py backend/tests/unit/test_chat_service_event_publisher_wiring.py qa/test_tool_executor_policy_guards.py
```

Resultado depois da correcao: 22 passed.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/services/chat_agent_loop.py qa/test_chat_agent_loop_content_safety.py qa/test_chat_agent_loop_policy_settings.py qa/test_tool_executor_policy_guards.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/services/chat_agent_loop.py qa/test_chat_agent_loop_content_safety.py qa/test_chat_agent_loop_policy_settings.py qa/test_tool_executor_policy_guards.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py::test_chat_study_job_denies_anonymous_access_to_other_user_job
```

Resultado baseline antes da correcao: 1 failed. Falha esperada: o endpoint retornava HTTP 200 para job de outro usuario.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py qa/test_chat_history_contract.py qa/test_chat_stream_sse_contract.py qa/test_chat_error_matrix.py
```

Resultado depois da correcao: 25 passed, 2 warnings.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/chat/chat_study_jobs.py qa/test_chat_endpoint_contract.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/chat/chat_study_jobs.py qa/test_chat_endpoint_contract.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py::test_chat_stream_denies_anonymous_access_to_other_user_conversation
```

Resultado baseline antes da correcao: 1 failed. Falha esperada: o endpoint retornava HTTP 200 para stream de conversa de outro usuario sem identidade resolvida.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py qa/test_chat_history_contract.py qa/test_chat_stream_sse_contract.py qa/test_chat_error_matrix.py backend/tests/unit/test_chat_project_scope.py backend/tests/unit/test_chat_trace_access.py
```

Resultado depois da correcao: 29 passed, 2 warnings.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/chat/chat_history.py backend/app/api/v1/endpoints/chat/chat_admin.py backend/app/api/v1/endpoints/chat/chat_stream.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_project_scope.py backend/tests/unit/test_chat_trace_access.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/chat/chat_history.py backend/app/api/v1/endpoints/chat/chat_admin.py backend/app/api/v1/endpoints/chat/chat_stream.py qa/test_chat_endpoint_contract.py
```

Resultado: passou.

## Decisão

Recomendação: manter as correções. Confiança: média-alta para os contratos corrigidos, limitada por ausência de validação full-stack com infraestrutura PC2 ativa.
