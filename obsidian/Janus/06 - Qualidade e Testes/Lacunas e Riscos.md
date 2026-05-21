---
tipo: qualidade
dominio: testes
camada: riscos
fonte-de-verdade: codigo
status: ativo
---

# Lacunas e Riscos

## Objetivo
Registrar as fragilidades percebidas a partir do codigo e da cobertura.

## Responsabilidades
- Sinalizar acoplamentos altos.
- Sinalizar zonas de baixa visibilidade.

## Entradas
- Leitura estrutural do backend/frontend.
- Inventario de testes.

## Saidas
- Backlog tecnico de risco arquitetural.

## Dependencias
- [[06 - Qualidade e Testes/Mapa de Testes]]
- [[02 - Backend/Como o Backend Pensa]]

## Template padrao de item de risco

### Guia de preenchimento
- **Identificador (ID)**: unico e imutavel (ex.: `RISK-001`). Use sequencia incremental.
- **Titulo**: frase curta e objetiva que descreve o risco.
- **Descricao (cenario)**: descreva o que acontece, onde acontece e por que e um risco. Preserve o enunciado original do item como citacao ou primeira linha.
- **Categoria**: escolha uma entre `qualidade`, `tecnica`, `processo`, `compliance`.
- **Probabilidade (1-5)**:
  - 1: rarissimo, depende de condicao improvavel
  - 2: pouco provavel, ocorre em casos de borda
  - 3: possivel, pode ocorrer em uso real sem grande surpresa
  - 4: provavel, tende a ocorrer com frequencia
  - 5: quase certo, ocorre com alta recorrencia
- **Impacto (1-5)**:
  - 1: baixo impacto local, facil de contornar
  - 2: impacto moderado em um fluxo, recuperavel
  - 3: impacto significativo em fluxo principal ou qualidade percebida
  - 4: impacto alto (operacao, dados, confiabilidade), requer acao rapida
  - 5: impacto critico (seguranca, indisponibilidade ampla, perda de dados)
- **Nivel de risco (PxI)**: calcule `probabilidade x impacto` (intervalo 1..25).
- **Status**: `identificado`, `em mitigacao`, `mitigado`, `materializado`.
- **Responsavel**: pessoa ou papel (ex.: `QA`, `Backend`, `Frontend`, `Infra`) que acompanha.
- **Plano de mitigacao**: acoes especificas e verificaveis (idealmente com criterio de aceite).
- **Prazo limite**: data-alvo (formato `AAAA-MM-DD`).
- **Ultima atualizacao**: data da ultima revisao do item (formato `AAAA-MM-DD`).
- **Referencias**: links internos e arquivos relacionados (ex.: `[[04 - Fluxos End-to-End/Conversa e Chat]]`, ou caminhos citados em `Arquivos-fonte`).

### Modelo (copiar/colar)
> [!risk] RISK-XXX - Titulo do risco
> - **Descricao (cenario):** "<enunciado original>" + detalhes
> - **Categoria:** tecnica|qualidade|processo|compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado|em mitigacao|mitigado|materializado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** a definir
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

## Registro de riscos (migrado)

### Visao consolidada
| ID | Titulo | Categoria | Prob. | Impacto | Nivel | Status | Responsavel | Referencias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | BackendApiService concentra contratos demais | tecnica | 3 | 3 | 9 | identificado | a definir | `frontend/src/app/services/backend-api.service.ts` |
| RISK-002 | ConversationsComponent concentra subfluxos demais | tecnica | 3 | 3 | 9 | identificado | a definir | `frontend/src/app/features/conversations/conversations.ts` |
| RISK-003 | Kernel compoe quase tudo manualmente | tecnica | 3 | 3 | 9 | identificado | a definir | `backend/app/core/kernel.py` |
| RISK-004 | Deploy distribuido PC1/PC2 aumenta superficie de falha | processo | 3 | 3 | 9 | identificado | a definir | [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]] |
| RISK-005 | Backend tem capacidades maiores que a UX operacional atual | processo | 3 | 3 | 9 | identificado | a definir | a definir |
| RISK-006 | REST e SSE do chat divergem apesar da mesma UX | qualidade | 4 | 4 | 16 | identificado | a definir | [[04 - Fluxos End-to-End/Conversa e Chat]] |
| RISK-007 | ChatStudyJobService e in-memory e perde estado em restart | tecnica | 4 | 3 | 12 | identificado | a definir | `backend/app/services/chat_study_service.py` |
| RISK-008 | GET /api/v1/chat/start descarta title aceito | qualidade | 3 | 2 | 6 | identificado | a definir | `backend/app/services/chat/message_orchestration_service.py` |
| RISK-009 | AgentEventsService depende de EventSource sem headers e pode quebrar com auth enforced | compliance | 3 | 4 | 12 | identificado | a definir | `frontend/src/app/core/services/agent-events.service.ts` |
| RISK-010 | Dominio de tools mistura catalogo em memoria, import side-effects e pendencias SQL/LangGraph | tecnica | 3 | 3 | 9 | identificado | a definir | `frontend/src/app/features/tools/tools.ts` |
| RISK-011 | Pouca evidencia de E2E de UX completa | qualidade | 4 | 4 | 16 | identificado | a definir | [[06 - Qualidade e Testes/Mapa de Testes]] |
| RISK-012 | Saude de container pode divergir de saude logica | qualidade | 3 | 4 | 12 | identificado | a definir | [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]] |
| RISK-013 | Integracoes de LLM/local runtime dependem fortemente de configuracao | processo | 3 | 3 | 9 | identificado | a definir | a definir |
| RISK-014 | Frontend escuta tool_status, mas backend nao emite no StreamingService | qualidade | 3 | 3 | 9 | identificado | a definir | `backend/app/services/chat/streaming_service.py` |
| RISK-015 | SSE nao indexa mensagens no RAG nem chama maybe_summarize, podendo divergir do REST | qualidade | 4 | 4 | 16 | identificado | a definir | `backend/app/services/chat/streaming_service.py` |
| RISK-016 | Pending action fallback depende de user_id; UI pode confirmar sem ID estruturado | compliance | 3 | 4 | 12 | identificado | a definir | `frontend/src/app/features/tools/tools.ts` |
| RISK-017 | Tela /tools lista apenas pending actions SQL (include_graph: false), mas backend tem LangGraph | qualidade | 3 | 2 | 6 | identificado | a definir | `frontend/src/app/features/tools/tools.ts` |
| RISK-018 | approve_sql_action/reject_sql_action mudam status, mas aprovacao SQL nao reexecuta tool | qualidade | 3 | 3 | 9 | identificado | a definir | `frontend/src/app/features/tools/tools.ts` |
| RISK-019 | Catalogo de tools e process-local; registry/historico/rate limits se perdem em restart | tecnica | 4 | 3 | 12 | identificado | a definir | a definir |
| RISK-020 | Registro de tools depende de import side-effects; agent_tools entra por outros fluxos | tecnica | 4 | 3 | 12 | identificado | a definir | `backend/app/core/kernel.py` |
| RISK-021 | ActionRegistry.register pode sobrescrever tool pelo mesmo nome; ordem de registro define efetivo | compliance | 3 | 4 | 12 | identificado | a definir | a definir |
| RISK-022 | ToolService.PROTECTED_TOOLS protege apenas parte; outras tools nativas removiveis via DELETE | compliance | 3 | 4 | 12 | identificado | a definir | a definir |
| RISK-023 | Criacao dinamica de tool nao recebe requires_confirmation; guardrail fica indireto | compliance | 3 | 5 | 15 | identificado | a definir | a definir |
| RISK-024 | execute_system_command docstring diz sem restricoes, mas usa run_restricted_command (doc diverge execucao) | qualidade | 3 | 2 | 6 | identificado | a definir | a definir |
| RISK-025 | AutonomyLoop executa um selected_step; resto do plano vira contexto, nao contrato | tecnica | 4 | 4 | 16 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-026 | PUT /policy reconstrui PolicyEngine sem revalidar plano atual nem persistir na AutonomyRun aberta | tecnica | 3 | 4 | 12 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-027 | Planner interno nao aplica validacao args_schema/allowlist/blocklist do caminho manual | compliance | 3 | 5 | 15 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-028 | AutonomyLoop enqueue_router nao chama validacoes/safety/simulacao/can_continue_cycle antes do enqueue | compliance | 3 | 5 | 15 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-029 | Perda de lease em _run_loop encerra por break sem cleanup completo; AUTONOMY_ACTIVE pode ficar stale | tecnica | 3 | 4 | 12 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-030 | Fechamento automatico depende de TaskState terminal voltar ao router; falhas podem prender goal in_progress | tecnica | 3 | 4 | 12 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-031 | PATCH /autonomy/goals/{id}/status completed sempre agenda self-study mesmo se ja completed | qualidade | 3 | 2 | 6 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-032 | AutonomyAdminService.run_self_study sem lock; multiplos gatilhos podem concorrer | tecnica | 3 | 4 | 12 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |
| RISK-033 | Self-study limita tempo/arquivos e pode fechar partial; cobertura incompleta sem alerta forte | qualidade | 3 | 3 | 9 | identificado | a definir | [[04 - Fluxos End-to-End/Autonomia]] |

### Itens detalhados

> [!risk] RISK-001 - BackendApiService concentra contratos demais
> - **Descricao (cenario):** "`BackendApiService` concentra contratos demais."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** mapear contratos expostos, separar por dominios e adicionar testes de contrato para chamadas criticas
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/services/backend-api.service.ts`

> [!risk] RISK-002 - ConversationsComponent concentra subfluxos demais
> - **Descricao (cenario):** "`ConversationsComponent` concentra subfluxos demais."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** separar subfluxos por componentes/servicos e adicionar cobertura de testes de integracao por fluxo principal
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/features/conversations/conversations.ts`

> [!risk] RISK-003 - Kernel compoe quase tudo manualmente
> - **Descricao (cenario):** "O kernel compoe quase tudo manualmente."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** mapear dependencias criticas e reduzir composicao manual onde impacta testabilidade; padronizar bootstrap e testes de inicializacao
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `backend/app/core/kernel.py`

> [!risk] RISK-004 - Deploy distribuido PC1/PC2 aumenta superficie de falha
> - **Descricao (cenario):** "O deploy distribuido PC1/PC2 aumenta superficie de falha."
> - **Categoria:** processo
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir healthchecks logicos, contratos operacionais e cenarios de falha/recuperacao por componente
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

> [!risk] RISK-005 - Backend tem capacidades maiores que a UX operacional atual
> - **Descricao (cenario):** "Capacidades internas do backend sao maiores que a UX operacional atual."
> - **Categoria:** processo
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** levantar capacidades internas nao expostas na UX e definir cobertura (testes/monitoramento) para evitar divergencia entre operacao e implementacao
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-006 - REST e SSE do chat divergem apesar da mesma UX
> - **Descricao (cenario):** "REST e SSE do chat tem capacidades diferentes apesar de servirem a mesma UX."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 16
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir contrato unificado (eventos, indexacao, sumarizacao) e criar testes E2E cobrindo REST e SSE com mesmos criterios de aceite
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Conversa e Chat]]

> [!risk] RISK-007 - ChatStudyJobService e in-memory e perde estado em restart
> - **Descricao (cenario):** "`ChatStudyJobService` e in-memory e perde estado em restart."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** persistir estado de jobs ou documentar limite; adicionar teste de resiliencia (restart) e verificacao de recuperacao/erro claro
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `backend/app/services/chat_study_service.py`

> [!risk] RISK-008 - GET /api/v1/chat/start descarta title aceito
> - **Descricao (cenario):** "`GET /api/v1/chat/start` aceita `title`, mas a implementacao descarta o valor."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 2
> - **Nivel (PxI):** 6
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** alinhar contrato do endpoint com implementacao e adicionar teste de contrato/integ cobrindo persistencia/retorno de title
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `backend/app/services/chat/message_orchestration_service.py`

> [!risk] RISK-009 - AgentEventsService depende de EventSource sem headers e pode quebrar com auth enforced
> - **Descricao (cenario):** "`AgentEventsService` depende de `EventSource` sem headers; se `CHAT_AUTH_ENFORCE_REQUIRED` subir, o stream de eventos tende a quebrar."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir estrategia de autenticacao para SSE e criar teste de regressao cobrindo eventos com auth habilitado
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/core/services/agent-events.service.ts`

> [!risk] RISK-010 - Dominio de tools mistura catalogo em memoria, import side-effects e pendencias SQL/LangGraph
> - **Descricao (cenario):** "O dominio de tools mistura catalogo em memoria, import side-effects, pendencias SQL e pendencias LangGraph sob a mesma UX operacional."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** separar semanticas (SQL vs LangGraph) na UX e nos contratos; padronizar eventos e persistencia; adicionar testes por tipo de pendencia
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/features/tools/tools.ts`

> [!risk] RISK-011 - Pouca evidencia de E2E de UX completa
> - **Descricao (cenario):** "Pouca evidencia de E2E de UX completa."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 16
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir fluxos E2E prioritarios (chat, tools, autonomia) e implementar suite E2E com criterios de aceite por fluxo
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[06 - Qualidade e Testes/Mapa de Testes]]

> [!risk] RISK-012 - Saude de container pode divergir de saude logica
> - **Descricao (cenario):** "Diferenca potencial entre saude de container e saude logica."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir sinais de saude logica e garantir healthchecks/alertas alinhados; adicionar testes de smoke que validem invariantes logicas
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

> [!risk] RISK-013 - Integracoes de LLM/local runtime dependem fortemente de configuracao
> - **Descricao (cenario):** "Parte das integracoes de LLM/local runtime depende fortemente de configuracao."
> - **Categoria:** processo
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** documentar configuracoes suportadas e criar testes de validacao de config (startup/health) cobrindo combinacoes criticas
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-014 - Frontend escuta tool_status, mas backend nao emite no StreamingService
> - **Descricao (cenario):** "O frontend escuta `tool_status`, mas o backend atual nao emite esse evento em `StreamingService`."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** alinhar contrato de eventos (emitir tool_status ou remover dependencia); adicionar teste de integracao do stream validando eventos esperados
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `backend/app/services/chat/streaming_service.py`, `frontend/src/app/services/chat-stream.service.ts`

> [!risk] RISK-015 - SSE nao indexa mensagens no RAG nem chama maybe_summarize, podendo divergir do REST
> - **Descricao (cenario):** "O fluxo SSE nao indexa mensagens no RAG nem chama `maybe_summarize()`, entao historico e grounding podem divergir do caminho REST."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 16
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** unificar efeitos colaterais (indexacao/sumarizacao) entre REST e SSE; adicionar testes de regressao garantindo equivalencia
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `backend/app/services/chat/streaming_service.py`

> [!risk] RISK-016 - Pending action fallback depende de user_id; UI pode confirmar sem ID estruturado
> - **Descricao (cenario):** "A criacao de pending action fallback depende de `user_id`; em cenarios anonimos ou mal resolvidos a UI pode receber confirmacao sem ID estruturado."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir regra de identidade obrigatoria para pendencias e adicionar testes cobrindo cenarios anonimos/mal resolvidos com resposta deterministica
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/features/tools/tools.ts`

> [!risk] RISK-017 - Tela /tools lista apenas pending actions SQL, mas backend tem LangGraph
> - **Descricao (cenario):** "A tela `/tools` lista apenas pending actions SQL (`include_graph: false`), embora o backend tambem tenha pending actions LangGraph com semantica diferente de retomada."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 2
> - **Nivel (PxI):** 6
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** explicitar semantica e origem das pendencias na UX; criar testes de listagem cobrindo ambos os tipos quando aplicavel
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/features/tools/tools.ts`

> [!risk] RISK-018 - approve_sql_action/reject_sql_action nao reexecutam tool
> - **Descricao (cenario):** "`approve_sql_action()` e `reject_sql_action()` apenas mudam o status em `pending_actions` e sincronizam o historico do chat; a aprovacao SQL nao reexecuta a tool pendente."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir contrato do que significa "aprovar" e implementar reexecucao ou feedback claro; adicionar testes de fluxo de aprovacao
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `frontend/src/app/features/tools/tools.ts`

> [!risk] RISK-019 - Catalogo de tools e process-local e se perde em restart
> - **Descricao (cenario):** "O catalogo de tools e process-local: `action_registry`, historico de chamadas e rate limits em memoria sao perdidos em restart e nao representam necessariamente outros processos/workers."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir persistencia/replicacao para registry e limites, ou documentar escopo; adicionar testes de restart e consistencia em multi-processo
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-020 - Registro de tools depende de import side-effects
> - **Descricao (cenario):** "O registro de tools depende de side-effects de import. `Kernel.startup()` garante `os_tools` e `ui_tools`, mas varias tools de `agent_tools` so entram no registry quando esse modulo e importado por outro fluxo."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** explicitar registro deterministico no startup e adicionar teste de inicializacao garantindo toolset esperado sem dependencia de import order
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** `backend/app/core/kernel.py`

> [!risk] RISK-021 - Tools podem ser sobrescritas por nome e ordem define efetivo
> - **Descricao (cenario):** "`ActionRegistry.register()` permite sobrescrever uma tool existente pelo mesmo nome; a permissao efetiva e a implementacao efetiva dependem da ordem de registro."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** bloquear sobrescrita sem aprovacao explicita e adicionar testes garantindo imutabilidade de tools criticas e previsibilidade de registry
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-022 - PROTECTED_TOOLS protege apenas parte e outras tools nativas removiveis via DELETE
> - **Descricao (cenario):** "`ToolService.PROTECTED_TOOLS` protege apenas parte das tools built-in; outras tools nativas continuam removiveis via `DELETE /api/v1/tools/{tool_name}`."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** revisar superficie de remocao e exigir politicas/roles; adicionar testes de autorizacao para endpoints de tools
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-023 - Criacao dinamica de tool sem requires_confirmation explicito
> - **Descricao (cenario):** "As rotas de criacao dinamica de tool nao recebem `requires_confirmation`; uma tool criada em runtime entra no registry sem esse guardrail explicito, salvo bloqueios indiretos de politica/permissao."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 5
> - **Nivel (PxI):** 15
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** tornar requires_confirmation parte do contrato de criacao e adicionar testes garantindo guardrails para tools dinamicas
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-024 - Docstring de execute_system_command diverge da execucao real
> - **Descricao (cenario):** "`execute_system_command()` declara \"sem restricoes\" no docstring, mas a implementacao usa `run_restricted_command()`; a documentacao inline do proprio codigo ja diverge da execucao real."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 2
> - **Nivel (PxI):** 6
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** alinhar documentacao e implementacao e adicionar teste de contrato/documentacao para evitar divergencias de garantias
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** a definir

> [!risk] RISK-025 - AutonomyLoop executa um selected_step e nao executa o plano inteiro
> - **Descricao (cenario):** "O `AutonomyLoop` nao executa um plano inteiro; ele escolhe um unico `selected_step` e publica um `TaskState` para o `router`. O restante do plano vira contexto, nao contrato de execucao."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 4
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 16
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** definir contrato de execucao do plano e adicionar testes de fluxo garantindo execucao/estado consistente entre etapas
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-026 - PUT /policy nao revalida plano atual nem persiste na AutonomyRun aberta
> - **Descricao (cenario):** "`PUT /policy` reconstrui o `PolicyEngine`, mas nao revalida o plano atual em memoria nem persiste a politica atualizada na `AutonomyRun` ja aberta."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** tornar atualizacao de policy transacional com plano/run e adicionar testes garantindo consistencia apos PUT /policy
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-027 - Planner interno nao aplica validacoes do caminho manual
> - **Descricao (cenario):** "O caminho manual de plano (`POST /start` com `plan`, `PUT /plan`) valida `args_schema`, allowlist e blocklist; o planner interno nao aplica a mesma validacao."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 5
> - **Nivel (PxI):** 15
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** unificar validacao do planner com a validacao manual e adicionar testes garantindo equivalencia de regras
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-028 - AutonomyLoop enqueue_router nao chama validacoes/safety/simulacao antes do enqueue
> - **Descricao (cenario):** "O `PolicyEngine` possui gates de comando, escopo, capability, content safety e simulacao destrutiva, mas o `AutonomyLoop` em `enqueue_router` nao chama `validate_tool_call()`, `validate_content_safety()`, `simulate_tool_call()` nem `can_continue_cycle()` antes do enqueue."
> - **Categoria:** compliance
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 5
> - **Nivel (PxI):** 15
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** aplicar validacoes obrigatorias antes de enfileirar e adicionar testes cobrindo bloqueios de policy/safety no fluxo de autonomia
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-029 - Perda de lease encerra loop sem cleanup completo e pode deixar AUTONOMY_ACTIVE stale
> - **Descricao (cenario):** "Se o lease de runtime for perdido durante `_run_loop()`, o loop encerra por `break`, mas esse caminho nao passa pelo cleanup completo de `stop()`. Isso pode deixar `AUTONOMY_ACTIVE` stale e a `AutonomyRun` ainda marcada como `running`."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** garantir cleanup idempotente em todos os caminhos de saida e adicionar testes simulando perda de lease com estado final consistente
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-030 - Falha antes de TaskState terminal pode prender goal em in_progress
> - **Descricao (cenario):** "O fechamento automatico da meta depende de um `TaskState` terminal com `meta.autonomy.goal_id` retornar ao `router`. Se a cadeia de workers falhar antes desse retorno, a goal pode ficar presa em `in_progress`."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** adicionar reconciliacao/timeout e testes de falha parcial garantindo transicao de estado ou alerta operacional
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-031 - PATCH completed sempre agenda self-study mesmo quando ja completed
> - **Descricao (cenario):** "`PATCH /autonomy/goals/{id}/status` com `completed` sempre agenda self-study em `BackgroundTasks`, mesmo quando o status ja era `completed`."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 2
> - **Nivel (PxI):** 6
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** tornar operacao idempotente e adicionar teste garantindo nao re-agendamento quando status ja for completed
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-032 - Self-study pode iniciar concorrente por falta de lock
> - **Descricao (cenario):** "`AutonomyAdminService.run_self_study()` nao tem lock proprio. Startup, trigger manual e trigger por conclusao de goal podem iniciar runs concorrentes sobre o mesmo repo."
> - **Categoria:** tecnica
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 4
> - **Nivel (PxI):** 12
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** adicionar lock/lease e testes simulando concorrencia garantindo exclusao mutua e comportamento deterministico
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

> [!risk] RISK-033 - Self-study pode fechar partial e reduzir cobertura sem alerta forte
> - **Descricao (cenario):** "O self-study limita tempo e quantidade de arquivos (`MAX_RUN_SECONDS`, `MAX_FILES_PER_RUN`) e pode fechar como `partial`; isso protege o processo, mas tambem significa cobertura incompleta sem alerta forte na API."
> - **Categoria:** qualidade
> - **Probabilidade (1-5):** 3
> - **Impacto (1-5):** 3
> - **Nivel (PxI):** 9
> - **Status:** identificado
> - **Responsavel:** a definir
> - **Plano de mitigacao:** explicitar status partial e adicionar sinalizacao/alerta; criar testes garantindo que partial seja retornado e tratado no consumidor
> - **Prazo limite:** a definir
> - **Ultima atualizacao:** a definir
> - **Referencias:** [[04 - Fluxos End-to-End/Autonomia]]

## Arquivos-fonte
- `backend/app/core/kernel.py`
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/streaming_service.py`
- `backend/app/services/chat_study_service.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/core/autonomy/policy_engine.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/main.py`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/features/tools/tools.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `frontend/src/app/services/chat-stream.service.ts`
- `frontend/src/app/core/services/agent-events.service.ts`
- `qa/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- Esta nota e deliberadamente viva e deve crescer conforme incidentes reais forem mapeados.
