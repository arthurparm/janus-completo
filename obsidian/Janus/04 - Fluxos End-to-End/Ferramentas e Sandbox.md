---
tipo: fluxo
dominio: execucao
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Ferramentas e Sandbox

## Objetivo
Cobrir o plano de execução de ferramentas do Janus.

## Responsabilidades
- Explicar catálogo, criação dinâmica e execução segura.
- Ligar tool executor, pending actions e sandbox.
- Delimitar onde a UI termina e onde a execução real começa.

## Entradas
- Solicitação do usuário.
- Metadados de ferramenta.
- Políticas de risco e permissão.
- Chamadas do LLM em `tool_call_envelope`.

## Saídas
- Execução ou bloqueio controlado.
- Estatísticas de uso e trilha de aprovação.

## Dependências
- [[02 - Backend/Segurança e Infra]]
- [[02 - Backend/Autonomia e Workers]]
- [[03 - Frontend/Serviços de Integração]]

## Sequência
1. Frontend explora ou aciona ferramentas.
2. Backend lista ferramentas e permissões via `/tools`.
3. `ToolService` resolve metadados; `ToolExecutorService` coordena execução.
4. Ações sensíveis podem gerar pending actions e confirmação.
5. O sandbox protege execução Python/OS quando aplicável.

## Sequência detalhada do runtime real
1. O frontend `/tools` carrega catálogo, estatísticas, auditoria e pending actions, mas não executa tool no browser.
2. O backend lista ferramentas e permissões via `/tools`.
3. `ToolService` resolve catálogo e metadados sobre o `action_registry`.
4. A execução real acontece no backend, principalmente via `ChatAgentLoop` -> `ToolExecutorService`, quando o LLM devolve um `tool_call_envelope`.
5. `ToolExecutorService` valida schema, política, quotas, confirmação humana e timeout antes de invocar a tool.
6. Ações sensíveis podem gerar pending actions SQL ou interrupções LangGraph, dependendo do fluxo.
7. O sandbox protege execução Python e comandos restritos quando aplicável.

## Catálogo real
- O catálogo vive em memória no singleton `action_registry`.
- `ToolService` e `ToolRepository` apenas refletem esse registro.
- Fontes reais de registro:
  - import de `app.core.tools.agent_tools`
  - `Kernel.startup()` com `register_os_tools()` e `register_ui_tools()`
  - `register_external_cli_tools()`
  - `productivity_tools.py`
  - criação dinâmica por `/api/v1/tools/create/from-function` e `/api/v1/tools/create/from-api`
- `ActionRegistry.register()` permite sobrescrever uma tool existente pelo mesmo nome; a implementação e a permissão efetivas dependem da ordem de registro.
- O `ToolService` possui uma camada de proteção (`PROTECTED_TOOLS`) que impede a deleção de ferramentas vitais (ex: `write_file`, `read_file`, `execute_python_code`, `search_web`).

## Categorias e permissões
- Categorias expostas por `/api/v1/tools/categories/list`:
  - `filesystem`
  - `api`
  - `database`
  - `computation`
  - `web`
  - `system`
  - `custom`
  - `dynamic`
- Permissões expostas por `/api/v1/tools/permissions/list`:
  - `read_only`
  - `safe`
  - `write`
  - `dangerous`
- O filtro HTTP de `/api/v1/tools/` suporta `category`, `permission_level` e `tags`.

## Onde termina a UI
- `frontend/src/app/features/tools/tools.ts` usa:
  - `getTools()`
  - `getToolStats()`
  - `listAuditEvents({ limit: 100 })`
  - `listPendingActions({ include_sql: true, include_graph: false })`
- A própria tela só aprova/rejeita pending actions.
- Possui filtros locais para Pending Actions por nível de risco (`high`, `medium`, `low`), origem (`sql`, `langgraph`) e busca textual.
- Aplica computações dedicadas para destacar o uso e eventos de ferramentas relacionadas a código (prefixo `codex_`).
- Não há execução de tool, criação dinâmica nem uso do endpoint `/api/v1/sandbox/*` na feature `/tools`.

## Onde começa a execução real
- O prompt do agente instrui o LLM a responder com um envelope JSON estrito:
  - `type = "tool_call_envelope"`
  - `version = "1.0"`
  - `calls = [{ name, args }]`
- `ChatAgentLoop` extrai esse envelope com `parse_tool_calls(...)`. O método `_extract_json_envelope_payload` é resiliente e busca blocos delimitados por crases ou extrai o objeto JSON nativamente caso haja texto em volta.
- `ToolExecutorService.execute_tool_calls(...)` então:
  - valida `args_schema` diretamente com Pydantic (`model_validate`)
  - faz content safety e gera sumário de escopo (`_build_scope_metadata` para targets como `file_path` e `conversation_id`)
  - audita a pré-execução (`tool_precheck`) ofuscando dados sensíveis via `redact_sensitive_payload`
  - consulta `PolicyEngine`
  - aplica quotas e rate limits
  - decide por executar, bloquear ou pedir confirmação
  - invoca a ferramenta suportando nativamente implementações assíncronas (`ainvoke`, corrotinas) e síncronas (`asyncio.to_thread`)
  - registra auditoria e estatísticas
- `AssistantService` é um caminho alternativo: executa tools direto no `action_registry`, sem passar pelo `ToolExecutorService`.

## Criação dinâmica
- `POST /api/v1/tools/create/from-function`
  - transforma código Python em tool com `DynamicToolGenerator.from_python_code()`
  - a execução do código gerado passa por `python_sandbox.execute(...)`
- `POST /api/v1/tools/create/from-api`
  - cria uma wrapper HTTP com `DynamicToolGenerator.from_api_endpoint()`
  - há implementação explícita apenas para `GET` e `POST`
- `DELETE /api/v1/tools/{tool_name}`
  - remove do registry
  - o bloqueio de remoção usa apenas `ToolService.PROTECTED_TOOLS`

## Governança
- `PolicyEngine` cruza `permission_level` com:
  - `risk_profile` (configurado via `CHAT_TOOL_RISK_PROFILE`)
  - `allowlist` (`CHAT_TOOL_ALLOWLIST`)
  - `blocklist` (`CHAT_TOOL_BLOCKLIST`)
  - `capability_allowlist`
  - `scope_allowlist`
  - `command_allowlist`
  - `command_blocklist_tokens`
- O `PolicyEngine` também utiliza as variáveis `CHAT_TOOL_MAX_ACTIONS` e `CHAT_TOOL_MAX_SECONDS` para limites de ciclo.
- `ToolExecutorService` ainda aplica:
  - limite de ações por ciclo
  - timeout (`TOOL_EXECUTOR_TIMEOUT_SECONDS`, padrão 30s)
  - concorrência por semaphore (`TOOL_EXECUTOR_MAX_CONCURRENCY`, padrão 4)
  - quota diária por usuário (avaliada via `ToolUsageRepository` e DB baseada em `TOOL_DAILY_QUOTAS`)
  - sliding window quota por usuário/projeto (avaliada via Redis em `get_redis_usage_tracker()` baseada em `TOOL_SLIDING_WINDOW_QUOTAS`)
- Tools com `requires_confirmation=True` ou que na simulação (`simulate_tool_call`) sinalizem ação destrutiva (`is_destructive`) geram pending action automaticamente em vez de execução imediata.

## Pending actions
- Fonte `sql`
  - criada pelo `ToolExecutorService` e por fallbacks de confirmação do chat
  - persistida em `pending_actions`
  - a UI `/tools` mostra esse tipo hoje
  - aprovar/rejeitar muda status e sincroniza o histórico do chat, mas não reexecuta a tool automaticamente
- Fonte `langgraph`
  - listada por `GET /api/v1/pending_actions/` quando `include_graph=true`
  - aprovar/rejeitar retoma o grafo em background

## Sandbox
- `python_sandbox`
  - base real de `execute_python_code`, `execute_python_expression`, `SandboxService` e tools dinâmicas `from-function`
  - restringe imports e pode rodar em Docker sem rede
- `command_sandbox`
  - bloqueia operadores de shell, multiline, tokens perigosos e executáveis fora da allowlist
  - é usado por tools como `execute_shell` e `execute_system_command`
- Endpoints dedicados em `/api/v1/sandbox/`:
  - `/execute`: recebe `CodeExecutionRequest` (code, context) e retorna output, error, tempo de execução e variáveis afetadas.
  - `/evaluate`: recebe `ExpressionRequest` (expression) e retorna result, error e tempo de execução.
  - `/capabilities`: retorna capacidades e restrições configuradas no sandbox.

## Arquivos-fonte
- `frontend/src/app/features/tools/tools.ts`
- `frontend/src/app/services/backend-api.service.ts`
- `backend/app/api/v1/endpoints/tools.py`
- `backend/app/api/v1/endpoints/pending_actions.py`
- `backend/app/api/v1/endpoints/sandbox.py`
- `backend/app/services/tool_service.py`
- `backend/app/services/tool_executor_service.py`
- `backend/app/services/sandbox_service.py`
- `backend/app/core/tools/action_module.py`
- `backend/app/core/tools/*`
- `backend/app/core/infrastructure/python_sandbox.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[03 - Frontend/Observability Frontend]]

## Riscos/Lacunas
- A superfície de tooling é poderosa e precisa de governança contextual, não só estática.
- O catálogo é dinâmico e dependente de ordem de registro.
- A aprovação SQL e a aprovação LangGraph não representam o mesmo comportamento operacional.
