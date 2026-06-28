# Chat Critical Audit Log

Data: 2026-06-22

## Escopo

Auditoria focada na funcionalidade de chat backend: endpoints REST/SSE, facade `ChatService`, serviços de conversa/orquestração/streaming, repositórios de chat e testes unitários de contrato.

## Status atual

- Estado geral: 17 ciclos críticos concluídos com foco em authz, isolamento por `user_id`, remoção de legado operacional, contratos de confirmação, segurança operacional de tools e extinção progressiva do legado estrutural em `pending_actions` SQL/LangGraph.
- Backend já endurecido em caminhos centrais: envio de mensagem, histórico, trace, stream, CRUD de conversa, study jobs, validação de escopo por projeto/usuário e promoção defensiva de `pending_actions.user_id` para contrato estrutural `NOT NULL` quando o saneamento permitir.
- Frontend já alinhado em áreas críticas: render de confirmação heurística de baixa confiança, contrato de `pending_actions` sem `user_id` cliente-controlado, roteamento seguro de approve/reject entre SQL e LangGraph, trilha crítica de auditoria visível na tela `tools` e distinção explícita entre passivo histórico bloqueado e fluxo operacional ativo.
- Qualidade já demonstrada por evidências do documento: suites unitárias/QA verdes nos fluxos focados, `ruff check`, `py_compile`, Vitest completo, lint e build Angular passando nos ciclos documentados.
- Risco residual consolidado: ainda faltam validações full-stack/browser com backend real e medição do resíduo histórico real de `pending_actions` em uma infraestrutura PC1/PC2 disponível.
- Nível atual de confiança: alto para contratos, endurecimento estrutural localizado e integração backend/frontend validada por testes; médio para comportamento ponta a ponta sob infraestrutura PC1/PC2 e fluxos operacionais reais.

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

## Ciclo 11 - `pending_actions` SQL podiam ser listadas e resolvidas sem ownership persistido

### Problema

- Categoria: seguranca operacional, privacidade e isolamento entre usuarios.
- Fato observado: `GET /api/v1/pending_actions/?include_sql=true` listava acoes SQL sem resolver identidade nem filtrar por dono.
- Fato observado: `POST /api/v1/pending_actions/action/{action_id}/approve|reject` mudavam status apenas por `action_id`.
- Fato observado: `PendingAction` e `PendingActionRepository` ainda nao persistiam nem consultavam `user_id`.
- Fato observado: o frontend expunha `listPendingActions({ user_id })`, mas o backend nao implementava esse escopo; approve/reject eram chamados diretamente por chat e tools.
- Impacto antes: qualquer cliente com acesso ao endpoint podia enumerar acoes pendentes SQL e aprovar/rejeitar acoes de outro usuario se soubesse o `action_id`.

### Hipotese

Acredito que persistir `user_id` em `pending_actions` SQL e exigir identidade resolvida nos endpoints de listagem/approve/reject elimina a aprovacao cruzada entre usuarios, porque o owner passa a fazer parte do modelo, do repositorio e do contrato HTTP. Para registros legados sem `user_id`, um fallback por `conversation_id` mantem compatibilidade apenas quando o acesso a conversa puder ser provado.

### Implementacao

- `pending_action_models.py`: adicionado campo nullable `user_id` e indice `idx_pending_actions_status_user`.
- `db_migration_service.py`: adicionada migracao idempotente para `pending_actions.user_id` e para o indice composto por `status,user_id`.
- `pending_action_repository.py`: `create`, `list`, `get` e `set_status` passaram a aceitar/filtrar `user_id`.
- `chat_contracts.py`: fallback pending action de chat agora persiste `user_id` no caminho principal, sem depender de assinatura legada do repositorio.
- `pending_actions.py`: `PendingActionDTO` passou a expor `user_id`; listagem SQL agora resolve identidade via semantica do chat e filtra por owner.
- `pending_actions.py`: approve/reject SQL agora exigem identidade resolvida e retornam `403` quando a acao pertence a outro usuario.
- `pending_actions.py`: para registros legados sem `user_id`, approve/reject usam `conversation_id` em `args_json` e validam acesso via `chat_service.get_history(...)`; sem prova de ownership, negam acesso.
- `chat_service.py`: reexportadas excecoes usadas pelos endpoints para restaurar compatibilidade de import do facade.
- `observability-api-service.ts`: removido `user_id` cliente-controlado de `listPendingActions(...)`.
- `observability-api-service.contract.spec.ts`: adicionado contrato garantindo que a querystring de pending actions nao expoe `user_id`.
- `qa/test_pending_actions_contract.py`: atualizada fixture e adicionados testes para owner correto, bloqueio de outro usuario e fallback legado por conversa.

### Metricas

- Baseline inferido por leitura: os endpoints SQL de pending actions nao resolviam ator nem cruzavam owner persistido antes de alterar status.
- Depois: `qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py` resultou em 15 passed.
- Gate estatico: `ruff check` dos arquivos tocados passou.
- Compilacao Python dos arquivos tocados passou.
- Validacao frontend: a execucao de `npm run test` que incluiu o novo contrato de `ObservabilityApiService` resultou em 27 arquivos de teste passados, 120 testes passados.

### Riscos e limitacoes

- A trilha `thread_id`/LangGraph em `pending_actions.py` continua fora do endurecimento principal deste ciclo; o codigo explorado nao expunha owner persistido equivalente para checkpoints.
- Registros SQL legados sem `user_id` dependem de `conversation_id` em `args_json` para autorizacao de fallback; se esse vinculo nao existir, o endpoint passa a negar acesso.
- A validacao frontend foi por contrato de servico e suite Vitest focada/ampla; nao houve e2e real em browser para approve/reject.

## Ciclo 18 - Testes e2e/integracao de chat estavam desalinhados com autenticacao Bearer obrigatoria

### Problema

- Categoria: qualidade de entrega, regressao de CI e disponibilidade da validacao de chat.
- Fato observado: o contrato atual de chat exige ator autenticado derivado de Bearer; `resolve_authenticated_user_context(...)` ignora `explicit_user_id`, ignora `allow_anonymous_fallback` e retorna `unknown` sem `Authorization`.
- Fato observado: `backend/tests/integration/test_chat_sse.py` chamava `/api/v1/chat/start` e `/api/v1/chat/stream/{id}` sem Bearer.
- Fato observado: `backend/tests/e2e/conftest.py` usava `http://janus-api:8000` como default, host valido em container mas nao em execucao local direta.
- Baseline medido: `backend/tests/e2e/test_api_endpoints.py --maxfail=1` falhou localmente antes da correcao com `NameResolutionError` para `janus-api`.
- Impacto antes: os testes de validacao de chat podiam falhar por ambiente local ou por contrato antigo de auth, reduzindo a capacidade de detectar regressao real no fluxo central.

### Hipotese

Acredito que autenticar as fixtures e2e/integracao com Bearer valido e usar `localhost` como default local melhora a confiabilidade da validacao, porque os testes passam a exercitar o contrato de seguranca atual em vez de uma compatibilidade anonima removida.

### Implementacao

- `backend/tests/e2e/conftest.py`: default local alterado para `http://localhost:8000`; jobs Docker ainda podem sobrescrever `BASE_URL` e `HEALTH_URL`.
- `backend/tests/e2e/conftest.py`: wrapper `api_client` passou a anexar `Authorization: Bearer <token>` por default e timeout configuravel por `E2E_REQUEST_TIMEOUT_SECONDS`.
- `backend/tests/e2e/test_api_endpoints.py`: teste de memoria anonima foi renomeado para fluxo autenticado, sem `user_id` cliente-controlado.
- `backend/tests/integration/test_chat_sse.py`: chamadas de start e stream passaram a enviar Bearer valido.

### Metricas

- Baseline antes da correcao: e2e local falhou em `test_health_check` por `janus-api` nao resolvido.
- Depois: `ruff check` dos testes tocados passou.
- Depois: `py_compile` dos testes tocados passou.
- Validacao contratual de auth/chat: `backend/tests/unit/test_chat_deps_identity.py` e dois contratos HTTP de auth em chat resultaram em 5 passed.

### Riscos e limitacoes

- O e2e externo completo nao foi executado apos a mudanca porque depende de API local/servico PC1 ativo.
- O teste de integracao SSE com `app.main` nao foi usado como gate final neste ciclo por custo/timeout observado; a mudanca foi validada estaticamente e por contratos de auth mais focados.
- Os tokens gerados pela fixture usam a configuracao local do teste; ambientes que sobrescrevem segredo/auth devem manter `create_token(...)` alinhado ao servidor.

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

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py
```

Resultado: 15 passed.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/models/pending_action_models.py backend/app/repositories/pending_action_repository.py backend/app/services/chat/chat_contracts.py backend/app/services/chat_service.py backend/app/api/v1/endpoints/pending_actions.py backend/app/services/db_migration_service.py qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m py_compile backend/app/models/pending_action_models.py backend/app/repositories/pending_action_repository.py backend/app/services/chat/chat_contracts.py backend/app/services/chat_service.py backend/app/api/v1/endpoints/pending_actions.py backend/app/services/db_migration_service.py qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py
```

Resultado: passou.

```powershell
npm run test -- --watch=false --include src/app/services/domain/observability-api-service.contract.spec.ts
```

Resultado: a suite Vitest executada nesta rodada resultou em 27 arquivos passados, 120 testes passados, incluindo `observability-api-service.contract.spec.ts`.

## Ciclo 12 - Modulo de chat ainda aceitava identidade fraca e legado cliente-controlado

### Problema

- Categoria: seguranca, privacidade e disponibilidade funcional do chat.
- Fato observado: `backend/app/api/v1/endpoints/chat/deps.py` ainda aceitava `explicit_user_id`, `X-User-Id`, fallback anonimo `anon:*` e bifurcacao por `CHAT_AUTH_ENFORCE_REQUIRED` para fluxos de chat.
- Fato observado: endpoints centrais de chat (`message`, `history`, `history/paginated`, `conversations`, `stream`, `trace`, `events`, `rename`, `delete`, `study-jobs`) ainda operavam com `allow_anonymous_fallback=True` em diferentes pontos.
- Fato observado: o frontend ainda enviava `user_id` em chamadas de chat, ainda anexava `X-User-Id` derivado do token e o canal `AgentEventsService` usava `EventSource` com `?user_id=...`, sem bearer.
- Impacto antes: o modulo de chat ainda dependia de identidade fraca em 8 caminhos principais de backend e 4 superficies centrais de frontend, mantendo risco de impersonation, autorizacao inconsistente, auditoria fragil e quebra futura quando a autenticacao forte fosse exigida em todos os fluxos.

### Hipotese

Acredito que remover toda resolucao legada de identidade no modulo de chat e alinhar o frontend para bearer-only elimina a superficie de autenticacao fraca sem quebrar o app Angular atual, porque o frontend ja possui trilha de `Authorization` e apenas o stream complementar de eventos precisava sair de `EventSource` para `fetch` autenticado.

### Implementacao

- `backend/app/api/v1/endpoints/chat/deps.py`: simplificada a resolucao de identidade para aceitar apenas ator autenticado por bearer; removidos caminhos legados de `explicit_user_id`, `X-User-Id`, fallback anonimo e modo de transicao do chat.
- `backend/app/api/v1/endpoints/chat/chat_message.py`, `chat_history.py`, `chat_stream.py`, `chat_admin.py` e `chat_study_jobs.py`: todos os endpoints centrais passaram a usar `allow_anonymous_fallback=False`; `stream` e `events` deixaram de aceitar `user_id` funcional.
- `frontend/src/app/services/domain/chat-api-service.ts` e `frontend/src/app/models/chat.models.ts`: removido `user_id` das assinaturas/contratos de `startChat`, `sendChatMessage` e `listConversations`.
- `frontend/src/app/features/conversations/conversations.ts` e `frontend/src/app/features/home/home.ts`: removido envio de `user_id` do cliente para criacao/listagem/envio no chat.
- `frontend/src/app/services/chat-auth-headers.util.ts` e `frontend/src/app/core/interceptors/auth.interceptor.ts`: removida a emissao de `X-User-Id`; mantido apenas `Authorization` e headers de correlacao.
- `frontend/src/app/core/services/agent-events.service.ts`: substituido `EventSource` com query string por consumo SSE autenticado via `fetch` + `ReadableStream`.
- `backend/tests/unit/test_chat_deps_identity.py`, `backend/tests/unit/test_chat_project_scope.py`, `backend/tests/unit/test_chat_trace_access.py`, `qa/test_chat_endpoint_contract.py`, `qa/test_chat_history_contract.py`, `qa/test_chat_stream_sse_contract.py`, `frontend/src/app/services/domain/chat-api-service.contract.spec.ts`, `frontend/src/app/services/chat-auth-headers.util.spec.ts` e `frontend/src/app/core/services/agent-events.service.spec.ts`: atualizados para o contrato bearer-only.
- `documentation/api/chat-contract.md`: removidos campos legados de identidade cliente-controlada e documentada autenticacao obrigatoria por bearer.
- Commit correspondente da implementacao: [f80d24e8](https://github.com/arthurparm/janus-completo/commit/f80d24e863e6c1ace71362f2eb32f363d6e0b91c)

### Metricas

- Baseline inferido por leitura e auditoria do estado atual:
  - 8 caminhos principais de backend ainda aceitavam identidade fraca ou fallback anonimo.
  - 4 superficies centrais de frontend ainda dependiam de `user_id` cliente-controlado, `X-User-Id` ou `EventSource` sem bearer.
- Depois da correcao:
  - 0 endpoints centrais de chat aceitam `anon:*`, `X-User-Id` ou `user_id` do cliente como mecanismo de autenticacao.
  - 100% dos fluxos centrais cobertos nesta iteracao dependem de ator autenticado por bearer.
- Testes executados nesta iteracao:
  - `backend/tests/unit/test_chat_deps_identity.py qa/test_chat_endpoint_contract.py qa/test_chat_history_contract.py qa/test_chat_stream_sse_contract.py`: 29 passed.
  - `backend/tests/unit/test_chat_project_scope.py backend/tests/unit/test_chat_trace_access.py`: 3 passed.
  - `src/app/services/domain/chat-api-service.contract.spec.ts src/app/services/chat-auth-headers.util.spec.ts src/app/core/services/agent-events.service.spec.ts src/app/features/conversations/conversations.spec.ts`: 11 passed.
  - `ruff check` dos arquivos Python tocados: passou.
  - `py_compile` dos arquivos Python tocados: passou.
  - `npm run lint`: passou.
  - `npx ng build --configuration development`: passou.

### Riscos e limitacoes

- O stream principal de chat ainda transporta `message` por query string; esse risco permanece fora do escopo desta iteracao.
- O endpoint `/trace` continua com limitacoes contratuais separadas; esta iteracao endureceu autenticacao, mas nao redesenhou o contrato de trace.
- Nao houve validacao manual em browser real nem ciclo full-stack PC1/PC2; a confianca desta iteracao vem de contratos, unitarios, lint e build.
- O arquivo de audit log ja continha um ciclo 11 previo no workspace; esta entrada foi adicionada como novo ciclo consolidado para o endurecimento bearer-only do modulo de chat.

## Ciclo 13 - Stream SSE principal expunha o prompt do usuario em query string

### Problema

- Categoria: seguranca, privacidade e experiencia central do usuario.
- Fato observado: `backend/app/api/v1/endpoints/chat/chat_stream.py` ainda expunha o fluxo principal em `GET /api/v1/chat/stream/{conversation_id}` e recebia `message` via query param.
- Fato observado: `frontend/src/app/services/chat-stream.service.ts` montava a URL do stream com `message`, `role` e `priority` em `URLSearchParams` e ainda retinha a URL completa em `lastUrl` para retry.
- Fato observado: `documentation/api/chat-contract.md`, `qa/test_chat_endpoint_contract.py`, `qa/test_chat_stream_sse_contract.py`, `qa/test_chat_error_matrix.py` e `backend/tests/integration/test_chat_sse.py` ainda refletiam o contrato legado por query string.
- Impacto antes: 100% das requisicoes do fluxo principal de streaming podiam expor o prompt do usuario em logs HTTP, proxies, historico de navegador, telemetria e memoria local do cliente, inclusive em retries automaticos.

### Hipotese

Acredito que migrar o stream principal para `POST` com payload JSON autenticado por bearer e eliminar a persistencia de `lastUrl` remove a superficie critica de exposicao do prompt sem alterar o contrato funcional dos eventos SSE, porque o backend e o frontend podem preservar os mesmos campos de negocio e o mesmo parser de stream trocando apenas o canal de transporte.

### Implementacao

- `backend/app/api/v1/endpoints/chat/models.py`: adicionado `ChatStreamRequest` para validar `message`, `role`, `priority`, `timeout_seconds`, `project_id` e `knowledge_space_id` em corpo JSON.
- `backend/app/api/v1/endpoints/chat/chat_stream.py`: o stream principal passou de `GET` para `POST`, consumindo `ChatStreamRequest` e preservando auth bearer, escopo por projeto, limite de tamanho de mensagem, knowledge space e emissao SSE.
- `frontend/src/app/services/chat-stream.service.ts`: removida a montagem da URL com query string; o servico agora usa `fetch` com `method: 'POST'`, `Content-Type: application/json` e retry baseado em request estruturado, sem reter prompt em URL.
- `frontend/src/app/services/chat-stream.service.spec.ts`: criada cobertura nova para provar envio por `POST`, ausencia de query string com prompt e retry reutilizando payload estruturado.
- `qa/test_chat_endpoint_contract.py`, `qa/test_chat_stream_sse_contract.py`, `qa/test_chat_error_matrix.py`, `backend/tests/unit/test_chat_project_scope.py` e `backend/tests/integration/test_chat_sse.py`: atualizados para o novo contrato `POST`.
- `frontend/e2e/demo-agentic-flow.spec.ts`: ajustado o mock do stream para ler `message` do corpo do request `POST`.
- `documentation/api/chat-contract.md`: documentado o stream principal como `POST /api/v1/chat/stream/{conversation_id}` com body JSON e sem prompt na query string.
- Commit correspondente da implementacao: [996c707c](https://github.com/arthurparm/janus-completo/commit/996c707c55bbad51148776adc14c048501f65320)

### Metricas

- Baseline inferido por leitura e reproducao local:
  - 1 endpoint central do chat expunha o prompt do usuario por query string.
  - 1 servico central de frontend persistia a URL completa do stream em memoria para retry.
  - 100% dos envios no modo streaming carregavam o prompt na URL.
- Depois da correcao:
  - 0 endpoints centrais de streaming do chat transmitem `message` em query string.
  - 0 retries do `ChatStreamService` dependem de URL completa contendo prompt.
  - 100% dos fluxos centrais de streaming cobertos nesta iteracao passam a enviar o prompt no corpo JSON autenticado.
- Testes e validacoes executados nesta iteracao:
  - `backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_endpoint_contract.py qa/test_chat_stream_sse_contract.py qa/test_chat_error_matrix.py backend/tests/unit/test_chat_project_scope.py`: 19 passed, 2 warnings conhecidas de deprecacao `HTTP_413_REQUEST_ENTITY_TOO_LARGE`.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/chat/chat_stream.py backend/app/api/v1/endpoints/chat/models.py qa/test_chat_endpoint_contract.py qa/test_chat_stream_sse_contract.py qa/test_chat_error_matrix.py backend/tests/unit/test_chat_project_scope.py backend/tests/integration/test_chat_sse.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/chat/chat_stream.py backend/app/api/v1/endpoints/chat/models.py`: passou.
  - `npm run test -- --watch=false --include src/app/services/chat-stream.service.spec.ts --include src/app/features/conversations/conversations.spec.ts --include src/app/core/services/agent-events.service.spec.ts`: o `npm` nao encaminhou os filtros como esperado e executou a suite Vitest completa; resultado efetivo: 29 arquivos, 124 testes passados.
  - `npm run lint`: passou.
  - `npm run build -- --configuration development`: passou.
  - Spot-check manual com `TestClient` e `POST /api/v1/chat/stream/conv-1`: HTTP 200, `content-type: text/event-stream; charset=utf-8`, eventos `protocol` e `token` presentes no corpo.

### Riscos e limitacoes

- `backend/tests/integration/test_chat_sse.py` foi atualizado para o novo contrato, mas a execucao agregada com o arquivo de integracao nao concluiu nesta sessao; a cobertura runtime desta iteracao ficou sustentada pelos contratos QA, pelo spot-check manual e pelos gates estaticos.
- Nao houve validacao manual em browser real nem subida completa da stack PC1/PC2; ainda falta evidenciar o comportamento de rede no app completo com backend real.
- O risco residual prioritario seguinte permanece no frontend de historico paginado: `getChatHistoryPaginated(...)` ainda chama `/history` em vez de `/history/paginated`, embora isso nao tenha prioridade maior do que a exposicao de prompts corrigida neste ciclo.

## Ciclo 14 - Frontend do historico paginado chamava endpoint incorreto e quebrava consistencia de contrato

### Problema

- Categoria: disponibilidade funcional, consistencia frontend/backend e auditabilidade do fluxo de conversa.
- Fato observado: `frontend/src/app/services/domain/chat-api-service.ts` implementava `getChatHistoryPaginated(...)`, mas ainda chamava `/api/v1/chat/{conversation_id}/history` em vez de `/history/paginated`.
- Fato observado: o backend ja expunha `GET /api/v1/chat/{conversation_id}/history/paginated` em `backend/app/api/v1/endpoints/chat/chat_history.py`, e os contratos QA ja validavam esse endpoint dedicado.
- Impacto antes: a UI principal carregava mensagens usando um metodo chamado "paginado", mas recebia a resposta do endpoint simples, perdendo `total_count`, `has_more`, `next_offset` e qualquer evolucao futura de navegacao/telemetria do historico. Isso criava uma integracao silenciosamente inconsistente entre frontend e backend no fluxo central de conversa.

### Hipotese

Acredito que alinhar `getChatHistoryPaginated(...)` ao endpoint correto e reforcar o contrato com testes de frontend e QA elimina a divergencia silenciosa entre as camadas, porque o cliente passa a consumir o mesmo shape paginado que o backend ja expunha e os testes impedem regressao futura para o endpoint simples.

### Implementacao

- `frontend/src/app/services/domain/chat-api-service.ts`: `getChatHistoryPaginated(...)` passou a chamar `/api/v1/chat/{conversation_id}/history/paginated`.
- `frontend/src/app/services/domain/chat-api-service.contract.spec.ts`: adicionada cobertura de contrato para garantir a URL correta e a preservacao de `total_count`, `has_more`, `next_offset`, `limit` e `offset`.
- `qa/test_chat_history_contract.py`: fortalecido o contrato backend do endpoint paginado para verificar explicitamente os metadados de paginação, e nao apenas a lista de mensagens.
- Commit correspondente da implementacao: [e3e9516e](https://github.com/arthurparm/janus-completo/commit/e3e9516e6cd7d258de0401ea64e266cbcbb3ea51)

### Metricas

- Baseline observado por auditoria de codigo:
  - 1 metodo central do frontend com nome/contrato paginado chamava o endpoint nao paginado.
  - 100% dos carregamentos via `getChatHistoryPaginated(...)` perdiam metadados reais de paginação do backend.
- Depois da correcao:
  - 0 chamadas de `getChatHistoryPaginated(...)` usam o endpoint simples `/history`.
  - 100% das chamadas do metodo passam a consumir `/history/paginated` com metadados coerentes.
- Testes e validacoes executados nesta iteracao:
  - `backend\.venv\Scripts\python.exe -m pytest -q qa/test_chat_history_contract.py`: 10 passed.
  - `npm run test -- --watch=false --include src/app/services/domain/chat-api-service.contract.spec.ts --include src/app/features/conversations/conversations.spec.ts --include src/app/features/conversations/conversations-flows.spec.ts`: o `npm` voltou a encaminhar os argumentos de forma ampla para o Vitest; resultado efetivo: 29 arquivos, 125 testes passados, incluindo o novo contrato de `ChatApiService` e os fluxos de `Conversations`.
  - `npm run lint`: passou.
  - `npx ng build --configuration development`: passou.

### Riscos e limitacoes

- Nao houve validacao browser-guided contra backend real nesta iteracao; a confianca vem de contratos frontend/backend, QA HTTP e build Angular.
- O comando padrao `npm run build -- --configuration development` continua sensivel ao encaminhamento de argumentos nesta workspace; a validacao real do ciclo foi feita com `npx ng build --configuration development`.
- Permanecem fora do escopo desta iteracao os itens residuais de full-stack PC1/PC2, validacao browser real do stream e fechamento da trilha `thread_id`/LangGraph em `pending_actions`.

## Ciclo 15 - Trilha `thread_id`/LangGraph de `pending_actions` foi endurecida com bearer e ownership verificavel

### Problema

- Categoria: seguranca operacional, integracao backend/frontend e consistencia contratual.
- Fato observado: o proprio documento mantinha a trilha `thread_id`/LangGraph de `pending_actions` como risco residual prioritario apos o ciclo 14.
- Fato observado: o backend ja havia endurecido a trilha SQL, mas a trilha LangGraph ainda precisava fechar authz equivalente em listagem e em `approve/reject` por `thread_id`.
- Fato observado: a UI `tools` ja estava em modo seguro com `include_graph=false`, mas o frontend ainda precisava manter contrato coerente para aprovar/rejeitar itens vindos por `thread_id` sem reabrir a superficie insegura na tela.
- Impacto antes: sem o fechamento completo do ciclo, o codigo ficava parcialmente endurecido, a suite QA ainda tinha inconsistencias de identidade bearer-only e o audit log seguia desatualizado em relacao ao estado real da integracao.

### Hipotese

Acredito que exigir bearer em toda a trilha LangGraph de `pending_actions`, aplicar ownership verificavel com fallback controlado por `conversation_id` e negar por padrao quando esse contexto nao existir elimina a lacuna residual de authz sem regressao na UI, porque o frontend pode continuar em modo SQL-only enquanto backend e contratos mantem a compatibilidade segura para itens `thread_id`.

### Implementacao

- `backend/app/api/v1/endpoints/pending_actions.py`: consolidado o endurecimento bearer-only na trilha LangGraph, mantendo `allow_anonymous_fallback=False` para listagem e `approve/reject`.
- `backend/app/api/v1/endpoints/pending_actions.py`: mantido o modelo de autorizacao com owner explicito em state/config/metadata, fallback por `conversation_id` validado via `chat_service.get_history(...)` e `deny-by-default` quando nao ha contexto verificavel.
- `backend/app/api/v1/endpoints/pending_actions.py`: ajustada a ordem de verificacao em `approve/reject` para retornar `404` de forma consistente quando a thread realmente nao existe em `checkpoints`, antes da leitura do estado.
- `qa/test_pending_actions_contract.py`: normalizados ids bearer-only da fixture, removida a inconsistência residual `owner-1` versus `"1"`, e corrigida a semantica do caso legado SQL sem owner para refletir o fallback real por `conversation_id`.
- `qa/test_pending_actions_contract.py`: adicionados casos cobrindo `404` para `thread-missing` em `approve` e `reject`.
- `frontend/src/app/services/domain/observability-api-service.contract.spec.ts`: mantida a cobertura de contrato para roteamento seguro entre endpoints SQL e LangGraph.
- `frontend/src/app/features/tools/tools.ts`: preservado o comportamento seguro da tela `tools`, consultando `pending_actions` apenas com `include_sql=true` e `include_graph=false`.

### Metricas

- Baseline confirmado nesta iteracao:
  - havia uma inconsistência factual na suite QA bearer-only (`owner-1` versus `"1"`);
  - o caso legado SQL sem owner estava com nome e expectativa divergentes do comportamento real de fallback por `conversation_id`;
  - a semantica de `404` para `thread-missing` na trilha LangGraph nao estava explicitamente coberta por contrato.
- Depois da consolidacao:
  - `backend\.venv\Scripts\python.exe -m pytest -q qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py`: 22 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/pending_actions.py qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/pending_actions.py qa/test_pending_actions_contract.py`: passou.
  - `npm run test -- --watch=false --include src/app/services/domain/observability-api-service.contract.spec.ts`: o `npm` nao encaminhou os filtros como esperado e executou a suite Vitest completa; resultado efetivo: 29 arquivos passados, 129 testes passados, incluindo `observability-api-service.contract.spec.ts`.
  - `npm run lint`: passou.
  - `npx ng build --configuration development`: passou.

### Riscos e limitacoes

- Nao houve validacao browser real nem ciclo full-stack PC1/PC2 nesta iteracao; a confianca do ciclo 15 vem de contratos QA/backend, Vitest, lint e build.
- A tela `tools` permanece deliberadamente SQL-only; isso reduz superficie de risco, mas ainda falta uma validacao guiada em browser para mensagens de erro e feedback visual de approve/reject.
- O comando `npm run test -- --watch=false --include ...` continua sensivel ao encaminhamento de argumentos nesta workspace; a evidência valida desta iteracao e o resultado efetivo da suite Vitest completa, nao o filtro solicitado.
- O ciclo reduz o risco residual principal de ownership/authz em `pending_actions` LangGraph, mas o fechamento do esforco de audit log ainda depende de evidência operacional em ambiente real e revisao final de readiness.

## Ciclo 16 - Legado operacional de `pending_actions` foi extinto e a trilha crítica ficou visível no frontend

### Problema

- Categoria: seguranca operacional, consistencia backend/frontend e auditabilidade do modulo de chat.
- Fato observado: mesmo apos o ciclo 15, `backend/app/api/v1/endpoints/pending_actions.py` ainda permitia fallback de ownership por `conversation_id` para registros SQL sem `user_id` persistido.
- Fato observado: o proprio backlog do documento ainda tratava como aberta a definicao final para `pending_actions` legadas sem owner persistido.
- Fato observado: a tela `frontend/src/app/features/tools/tools.ts` continuava priorizando uma visao de eventos `codex_*`, o que nao refletia a trilha critica de approve/reject e bloqueios do modulo de chat.
- Fato observado: quando o backend passasse a responder erros estruturados para owner ausente, a UI ainda precisava interpretar `detail.code/detail.message` corretamente.
- Impacto antes: o modulo seguia com uma excecao legada em authz, a trilha de auditoria critica nao ficava clara na UI e a integracao entre decisao backend e feedback frontend permanecia incompleta para signoff de seguranca.

### Hipotese

Acredito que extinguir o fallback legado de runtime para `pending_actions` sem owner persistido, fazer backfill deterministico onde houver dono recuperavel e expor no frontend a trilha critica com `trace_id`, endpoint e status elimina a ultima ambiguidade operacional do modulo e melhora a auditabilidade real sem reabrir a superficie insegura da UI.

### Implementacao

- `backend/app/repositories/pending_action_repository.py`: `create(...)` passou a exigir `user_id` persistido; adicionados utilitarios para listar registros sem owner e atribuir owner em saneamento.
- `backend/app/services/db_migration_service.py`: adicionada rotina idempotente de backfill de `pending_actions.user_id` a partir de `conversation_id` persistido em `args_json` e do owner da conversa em `sessions`.
- `backend/app/api/v1/endpoints/pending_actions.py`: removido o fallback operacional por `conversation_id` para approve/reject SQL; registros sem owner persistido agora retornam `403` com `code="PENDING_ACTION_OWNER_REQUIRED"` e deixam trilha auditavel de bloqueio.
- `backend/app/api/v1/endpoints/pending_actions.py`: approve/reject SQL e LangGraph passaram a registrar eventos diretos de auditoria com `endpoint`, `status`, `trace_id`, `request_id`, source e identificadores do fluxo.
- `backend/app/services/chat_event_publisher.py`: os eventos publicados pelo chat passaram a carregar `trace_id`/`request_id` quando a correlacao estiver presente no contexto corrente.
- `frontend/src/app/features/tools/tools.ts` e `tools.html`: a UI deixou de mostrar apenas eventos `codex_*` e passou a destacar a trilha critica de chat/pending actions com `acao`, `status`, `trace` e `endpoint`, alem de interpretar erros estruturados do backend.
- `frontend/src/app/features/tools/tools.spec.ts`: adicionada cobertura para a trilha critica e para o parsing de erro estruturado.
- `qa/test_pending_actions_contract.py` e `qa/test_pending_actions_line_coverage.py`: atualizados para refletir a extincao do legado operacional e a nova resposta estruturada de bloqueio.

### Metricas

- Baseline confirmado nesta iteracao:
  - ainda existia 1 caminho funcional de approve/reject SQL dependente de owner inferido em runtime por `conversation_id`;
  - a tela `tools` ainda priorizava eventos `codex_*` em vez da trilha critica do modulo de chat;
  - o frontend ainda nao cobria o parsing de erro estruturado para bloqueio de legado extinto.
- Depois da correcao:
  - `backend\.venv\Scripts\python.exe -m pytest -q qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py`: 23 passed.
  - `backend\.venv\Scripts\python.exe -m pytest -q backend/tests/unit/test_chat_service_event_publisher_wiring.py`: 2 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/api/v1/endpoints/pending_actions.py backend/app/repositories/pending_action_repository.py backend/app/services/db_migration_service.py backend/app/services/chat_event_publisher.py qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/api/v1/endpoints/pending_actions.py backend/app/repositories/pending_action_repository.py backend/app/services/db_migration_service.py backend/app/services/chat_event_publisher.py qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py`: passou.
  - `npm run test -- --watch=false`: 30 arquivos passados, 131 testes passados.
  - `npm run lint`: passou.
  - `npx ng build --configuration development`: passou.
- Resultado operacional do ciclo:
  - 0 caminhos SQL de approve/reject permanecem autorizando `pending_actions` sem owner persistido via fallback de conversa.
  - 100% das `pending_actions` novas cobertas por este fluxo exigem `user_id` persistido em criacao.
  - a tela `tools` agora exibe a trilha critica do modulo em vez de uma visao centrada apenas em eventos `codex_*`.

### Riscos e limitacoes

- A rotina de backfill saneia apenas registros cujo owner pode ser recuperado de forma deterministica; residuos sem owner recuperavel passam a ficar bloqueados operacionalmente, nao removidos.
- Nao houve ciclo browser com backend real nem subida PC1/PC2 nesta iteracao; a confianca vem de contratos, testes unitarios, Vitest completo, lint e build.
- O comando `npm run test -- --watch=false` continua emitindo warning do `npm` sobre encaminhamento de `--watch`, mas a suite Vitest executada e o resultado final permanecem validos.
- O fechamento do esforco ainda depende de evidência operacional integrada em ambiente mais proximo do real, nao de nova definicao para legado de `pending_actions`, que deixa de ser item aberto.

## Decisão

Recomendação: manter as correções. Confiança: alta para contratos, integração local guiada e extinção do legado operacional; limitada por ausência de validação full-stack com infraestrutura PC2 ativa.

## Próximos passos

- `D+1` | Owner: `QA` | Consolidar uma matriz curta de fluxos críticos ainda não validados ponta a ponta: `chat/start`, `chat/message`, `stream`, `trace`, `study-jobs`, `pending_actions approve/reject`.
- `D+1` | Owner: `Frontend` | Executar validação guiada dos fluxos visíveis ao usuário para confirmação `low_confidence`, aprovação e rejeição de `pending_actions`, com evidência de comportamento esperado, estados de loading e mensagens de erro.
- `D+3` | Owner: `Backend` | Medir e zerar o backlog residual de registros bloqueados sem owner recuperável, via saneamento administrativo controlado e sem reintroduzir fallback de runtime.
- `D+3` | Owner: `Security` | Revisar os ciclos 9, 10, 11 e 15 como bloco consolidado de authz para confirmar que study jobs, conversas existentes e pending actions não operam sem identidade comparável.
- `D+7` | Owner: `Ops/Platform` | Executar um ciclo de validação em stack PC1/PC2 com coleta de evidências operacionais: health, logs, request IDs/trace IDs e resultado dos fluxos críticos.
- `Próxima sprint` | Owner: `QA` | Promover pelo menos um fluxo crítico de chat para cobertura browser/e2e reproduzível, priorizando aprovação/rejeição de pending action e polling de study job.
- `Pré-release` | Owner: `Backend + Frontend + QA + Security + Ops/Platform` | Fazer revisão final de readiness com checklist de evidências, critérios de validação e limitações remanescentes antes de declarar o esforço de audit log como concluído.

## Requisitos técnicos restantes

- Todos os caminhos de resolução de ação pendente devem operar com owner explícito persistido; residuos sem owner recuperável nao podem voltar a operar por fallback de runtime.
- A trilha `thread_id`/LangGraph precisa manter a decisão de engenharia já registrada neste documento: owner explícito quando disponível e `deny-by-default` quando não houver contexto verificável.
- Registros históricos sem `user_id` em `pending_actions` precisam permanecer fora da superfície operacional até saneamento administrativo definitivo, sem reintrodução de compatibilidade legada.
- Endpoints que operam sobre conversa existente devem continuar exigindo identidade comparável mesmo em modo de transição; qualquer exceção deve ser explicitamente documentada e testada.
- Fluxos sensíveis de chat precisam manter rastreabilidade mínima entre request, decisão e evidência operacional por `request_id`, `trace_id` ou identificador equivalente.
- O frontend deve continuar tratando corretamente confirmações heurísticas versus confirmações acionáveis, sem exibir botões de aprovação falsos para fluxos que exigem `pending_action_id`.
- O documento precisa manter uma visão consolidada do que já está endurecido, do que ainda depende de validação real e de quais limitações são aceitas temporariamente.

## Critérios de validação

- Suites de backend citadas nos ciclos devem permanecer verdes para os caminhos críticos já corrigidos, incluindo contratos HTTP/SSE, testes unitários focados e testes de `pending_actions`.
- Gates estáticos usados nesta auditoria devem continuar passando nos arquivos tocados: no mínimo `ruff check` e `py_compile`; quando aplicável ao frontend, lint/build ou suite equivalente.
- Deve existir validação focada dos fluxos de confirmação do chat no frontend, cobrindo `low_confidence`, approve e reject com comportamento consistente entre UI e contrato backend.
- Deve existir pelo menos uma validação ponta a ponta ou browser-guided dos fluxos críticos remanescentes antes do encerramento do esforço.
- Mudanças futuras que alterem authz, ownership ou transição anônima precisam atualizar este log com baseline, hipótese, implementação, métricas e riscos/limitações.

## Checks de compliance e evidência

- Cada validação crítica deve deixar evidência mínima anexável ou reproduzível: comando executado, resultado, data e artefato associado quando existir.
- Fluxos de aprovação/rejeição de ações sensíveis devem manter evidência suficiente para explicar quem aprovou, em qual contexto e com qual identificador técnico correlacionável.
- Logs e testes usados para signoff devem permitir correlação entre falha observada e caminho de código corrigido, preferencialmente com `request_id`, `trace_id` ou identificador de conversa/job/action.
- Limitações aceitas temporariamente devem permanecer explícitas no documento até serem eliminadas ou formalmente aceitas no gate pré-release.
- O fechamento do esforço exige revisão conjunta por papéis de `Backend`, `QA` e `Security`; quando houver dependência de ambiente real, incluir `Ops/Platform`.

## Prontidão para conclusão

- O esforço de chat critical audit log pode ser considerado concluído quando os riscos residuais principais estiverem reduzidos a itens explicitamente aceitos, e não a gaps implícitos de validação.
- Para isso, o documento precisa mostrar três coisas com clareza: o que já foi endurecido, o que ainda falta e quais evidências sustentam a confiança operacional atual.
- No estado atual, a maior parte do backend, da UI crítica e dos contratos já está estabilizada, mas a conclusão ainda depende de validação full-stack/browser e de saneamento administrativo do resíduo histórico já bloqueado.
- Até esse fechamento, este documento deve ser tratado como fonte viva de progresso, critérios de aceite e backlog crítico do sistema de chat.

## Ciclo 17 - Legado estrutural de `pending_actions` foi endurecido sem reabrir a superfície operacional

### Problema

- Categoria: seguranca operacional, consistencia backend/frontend, schema hardening e readiness final do modulo de chat.
- Fato observado: apos o ciclo 16, o runtime ja bloqueava `pending_actions` SQL sem owner persistido, mas `backend/app/models/pending_action_models.py` ainda declarava `user_id` como `nullable=True`.
- Fato observado: `backend/app/services/db_migration_service.py` ja fazia backfill deterministico, porem nao promovia explicitamente o schema para `NOT NULL` nem reportava de forma estruturada quando o resíduo historico ainda bloqueasse esse endurecimento.
- Fato observado: a UI `frontend/src/app/features/tools/tools.html` e os testes frontend ainda descreviam o estado residual sobretudo como "legado bloqueado", sem deixar claro que o legado operacional ja estava extinto e que o restante era backlog administrativo fora da superficie de approve/reject.
- Fato observado: a rodada anterior havia deixado pendente a reexecucao da suite frontend apos o ultimo teste de contrato de `observability-api-service`.
- Impacto antes: o contrato de dominio e o schema continuavam parcialmente desalinhados, a comunicacao visual do frontend ainda permitia ambiguidade semantica sobre o passivo historico e faltava uma rodada final de validacao consolidada para a iteracao.

### Hipotese

Acredito que alinhar o modelo ao contrato endurecido, fazer a migracao reportar explicitamente quando `pending_actions.user_id` pode ou nao ser promovido para `NOT NULL`, e reposicionar o resumo do frontend como backlog administrativo bloqueado elimina a ultima ambiguidade estrutural do legado sem reabrir nenhum fallback inseguro de runtime.

### Implementacao

- `backend/app/models/pending_action_models.py`: `PendingAction.user_id` passou a refletir o contrato de dominio endurecido como obrigatorio no modelo.
- `backend/app/services/db_migration_service.py`: adicionados helpers para inspecionar nulabilidade da coluna, contar residuos `user_id IS NULL` e gerar SQL de promocao `NOT NULL` conforme o dialeto suportado.
- `backend/app/services/db_migration_service.py`: `validate_schema()` passou a verificar explicitamente `pending_actions.user_id_not_null` e a eliminacao de linhas ownerless como checks separados de schema/dados.
- `backend/app/services/db_migration_service.py`: `migrate_schema()` passou a:
  - executar o backfill deterministico ja existente;
  - medir quantos registros ownerless restam;
  - promover `pending_actions.user_id` para `NOT NULL` quando nao houver resíduo impeditivo e o dialeto suportar a operacao;
  - retornar sinais estruturados de bloqueio (`pending_actions_user_id_not_null_blocked`) quando o schema nao puder ser endurecido por causa de historico irrecuperavel.
- `backend/app/repositories/pending_action_repository.py`: a mensagem do resumo administrativo passou a afirmar explicitamente que o legado operacional esta extinto, que o passivo restante e backlog administrativo e que novos registros ownerless sao rejeitados.
- `frontend/src/app/features/tools/tools.html`: o card administrativo passou a usar a linguagem "passivo historico bloqueado", reforcando que o backlog nao pertence mais a superficie operacional.
- `frontend/src/app/features/tools/tools.spec.ts`: adicionada cobertura de render para a mensagem de backlog administrativo e para a ausencia de qualquer botao dentro da secao de passivo historico.
- `frontend/src/app/services/domain/observability-api-service.contract.spec.ts` e `qa/test_observability_pending_actions_legacy_residue_contract.py`: payloads de contrato ajustados para a nova semantica da mensagem administrativa.
- `qa/test_db_migration_service_contract.py`: adicionados testes focados que provam:
  - promocao automatica de `pending_actions.user_id` para `NOT NULL` quando o resíduo ownerless for zero;
  - bloqueio explicito da promocao quando ainda restarem registros sem owner persistido.
- `tooling/async_ops_validation.py`: revisado nesta iteracao; o arquivo ja estava alinhado ao contrato bearer-only e sem `user_id` cliente-controlado, portanto nao exigiu novo patch funcional.

### Metricas

- Baseline confirmado nesta iteracao:
  - o runtime seguia seguro, mas o modelo SQLAlchemy ainda aceitava `user_id` nulo em `PendingAction`;
  - a migracao ainda nao reportava formalmente o bloqueio da promocao `NOT NULL`;
  - o frontend ainda comunicava o resíduo como "legado bloqueado" de forma menos precisa do que o objetivo atual de extincao do legado operacional.
- Depois da consolidacao:
  - `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m pytest -q qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py qa/test_observability_pending_actions_legacy_residue_contract.py qa/test_db_migration_service_contract.py backend/tests/unit/test_observability_service_instrumentation.py::test_pending_actions_legacy_residue_summary_records_metrics`: 32 passed.
  - `backend\.venv\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend/app/models/pending_action_models.py backend/app/services/db_migration_service.py backend/app/repositories/pending_action_repository.py backend/app/api/v1/endpoints/pending_actions.py backend/app/api/v1/endpoints/observability.py backend/app/services/observability_service.py qa/test_pending_actions_contract.py qa/test_pending_actions_line_coverage.py qa/test_db_migration_service_contract.py qa/test_observability_pending_actions_legacy_residue_contract.py`: passou.
  - `backend\.venv\Scripts\python.exe -m py_compile backend/app/models/pending_action_models.py backend/app/services/db_migration_service.py backend/app/repositories/pending_action_repository.py backend/app/api/v1/endpoints/pending_actions.py backend/app/api/v1/endpoints/observability.py backend/app/services/observability_service.py qa/test_db_migration_service_contract.py qa/test_observability_pending_actions_legacy_residue_contract.py`: passou.
  - `npm run test -- --watch=false`: 30 arquivos passados, 133 testes passados, incluindo `tools.spec.ts` e `observability-api-service.contract.spec.ts`.
  - `npm run lint`: passou.
  - `npx ng build --configuration development`: passou.
- Resultado tecnico do ciclo:
  - o contrato de aplicacao e o modelo agora convergem para `pending_actions` com owner persistido obrigatorio;
  - a migracao passa a declarar explicitamente se o endurecimento estrutural do schema foi aplicado ou bloqueado por resíduo historico;
  - a UI admin deixa mais claro que o que resta nao e fluxo operacional, e sim backlog administrativo bloqueado.

### Riscos e limitacoes

- Nao houve promocao real de `pending_actions.user_id` para `NOT NULL` em banco ativo nesta iteracao, porque a infraestrutura nao estava disponivel; a confianca aqui vem de contrato, logica de migracao e testes, nao de DDL executada em ambiente PC1/PC2.
- `python tooling/dev.py up` falhou no host atual com `FileNotFoundError: [WinError 2]` ao invocar `docker`; por isso nao houve validacao browser/full-stack real nesta rodada.
- `python tooling/dev.py doctor --host 127.0.0.1 --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json` confirmou `overall_ok: False`, `health_ok: False`, `deps_http_ok: False` e `deps_tcp_ok: False`, reforcando a indisponibilidade do backend real no ambiente.
- O warning do `npm` sobre encaminhamento de `--watch` permanece no workspace, mas a suite Vitest efetivamente executada e o resultado final continuam validos.
- Ainda nao existe medicao factual, nesta maquina, de quantos registros ownerless historicos restam no banco real; o ciclo fecha a trilha de endurecimento e a evidencia automatizada, mas a contagem real depende de ambiente com banco acessivel.

## Decisão

Recomendação: manter as correções. Confiança: alta para extinção do legado operacional, endurecimento estrutural localizado e integração contratual backend/frontend; limitada por ausência de execução real do fluxo PC1/PC2 e de DDL sobre banco ativo neste host.

## Próximos passos

- `D+1` | Owner: `Ops/Platform` | Disponibilizar ambiente com `docker` e dependencias PC2/PC1 para executar `python tooling/dev.py up` e validar a promocao real do schema, a contagem factual do backlog ownerless e o fluxo browser/full-stack da tela `tools`.
- `D+1` | Owner: `Backend` | Executar `migrate_schema()` e `validate_schema()` contra banco real, registrando se `pending_actions.user_id_not_null` foi aplicado ou se permaneceu bloqueado por resíduo historico.
- `D+1` | Owner: `QA` | Reproduzir no browser a tela `tools` com um caso controlado de pending action valida e um caso bloqueado por owner ausente, coletando evidencias de UX e trilha critica.
- `D+3` | Owner: `Security` | Revisar o resultado da promocao estrutural para confirmar que nenhum caminho de criacao/approve/reject reintroduz owner inferido em runtime.
- `Pré-release` | Owner: `Backend + Frontend + QA + Security + Ops/Platform` | Encerrar o effort apenas quando houver evidencia operacional real do ambiente integrado ou aceitacao formal do risco remanescente.
