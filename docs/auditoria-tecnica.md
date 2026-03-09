# Auditoria Técnica Diária - Janus

Data de criação: 2026-03-01
Objetivo: Registrar as descobertas das auditorias contínuas, consolidar débitos técnicos e evidenciar pontos de risco no sistema.

## Achados do dia

### 1. Vazamento de PII em Logging (LGPD/Segurança)
**Descrição:** Observou-se que múltiplos serviços loggam inputs do usuário, artefatos completos ou prévias de mensagens, o que pode conter Informações Pessoalmente Identificáveis (PII) sensíveis. Não há redação ou ofuscação aplicada nesses fluxos antes da escrita do log.
**Evidências:**
- `backend/app/services/chat_command_handler.py`: Os comandos como `/feedback [mensagem]` loggam os argumentos (`args`) de forma integral.
- `backend/app/services/chat_event_publisher.py`: O método `_publish_to_log` expõe até 100 caracteres de "content_preview" e o método fallback printa PII (`payload["content"][:100]`).
- `backend/app/services/collaboration_service.py`: Logga conteúdo e argumentos (`key`, `author`, `project_description`) durante a orquestração e uso dos endpoints `add_artifact` e troca de mensagens inter-agente.
- `backend/app/interfaces/daemon/daemon.py`: A interface Janus Daemon logga o comando de voz recebido.
- `backend/app/core/tools/productivity_tools.py`: Logga os meta dados do e-mail de saída (recipient, subject).

**Próximos passos:**
- Estender os padrões de Redação (PII Redaction) de `backend/app/core/memory/security.py` (_PII_PATTERNS) para toda a camada do logger.
- Registrar SG-014 no backlog técnico (`melhorias-possiveis.md`) e acoplar com as definições em `lgpd.md`.

### 2. Endpoints Não Autenticados (Segurança)
**Descrição:** Os endpoints do workspace dependem puramente do injetor de serviços `get_collaboration_service` e dispensam camadas de AuthN/AuthZ. Atores não-autenticados poderiam subverter os workspaces e inclusive forçar um desligamento do sistema (Shutdown).
**Evidências:**
- Endpoint `add_artifact` ou `shutdown_system` em `backend/app/api/v1/endpoints/workspace.py` não chama métodos como `Depends(get_current_user)`.

**Próximos passos:**
- Mapear a matriz de AuthZ das rotas de `workspace.py` e adicionar RBAC ou validação de Token simples.
- Adicionar issue SG-015 para o backlog ativo de segurança.

### 3. Rate Limit Brute Force Vulnerabilidade (Segurança)
**Descrição:** Endpoints de autenticação estão expostos sem controle de taxa volumétrica. Em caso de indisponibilidade do Redis, a arquitetura foi desenhada para retornar `503 Service Unavailable` em vez de falhar de modo resiliente e aberto (Fail-Open), paralisando a aplicação global.
**Evidências:**
- `backend/app/api/v1/endpoints/auth.py`: Falta do uso de `@limiter.limit("5/minute")` nos endpoints `login` e `refresh`.
- Middleware `backend/app/core/infrastructure/rate_limit_middleware.py`: Comportamento estrito Fail-Closed dependente de Redis.

**Próximos passos:**
- Ajustar injeções de Rate Limiting para fail-open no core e restringir escopo no `auth.py`.
- Criar a issue OQ-013 (Fail-Closed) e SG-017 (Rate-Limit de Auth) no backlog.

### 4. Fragilidades Estruturais - Ciclomática e Dependências Físicas (Cód/Testes)
**Descrição:** Hardcodes de caminhos de arquivos e componentes inflados com responsabilidades excessivas violam o princípio de Single Responsibility (SRP).
**Evidências:**
- God Objects: `backend/app/services/observability_service.py` (~1200 linhas) e `frontend/src/app/services/backend-api.service.ts` (~1638 linhas), `frontend/src/app/features/conversations/conversations.ts` (~1700 linhas).
- Caminhos Físicos Quebrados: Configurações estáticas `/app/workspace` que não resolvem via ambiente (`app.core.infrastructure.filesystem_manager.WORKSPACE_DIR`).
- Criação prematura de instâncias em `NeuralTrainer.mkdir()` corrompendo importações assíncronas em testes por falta de permissões pré-configuradas.
- Criação frágil de execuções via `loop.create_task` em `DataRetentionService` rodando em SQLAlchemy `sync_events.py`.

**Próximos passos:**
- Substituir imports engessados pelas referências dinâmicas no file system manager. Refatorar as classes monolíticas aplicando injeção de dependência e divisão por domínio.

## Achados do dia (2026-03-03)

### 5. Configurações Vulneráveis e Despadronizadas
**Descrição:** Observou-se que credenciais estão sendo definidas diretamente no código com valores default inseguros, o que pode resultar em exploração em caso de má configuração do ambiente. Além disso, classes estão acessando variáveis de ambiente sem passar pelo Pydantic Settings, reduzindo previsibilidade.
**Evidências:**
- `backend/app/config.py`: Variáveis `NEO4J_PASSWORD`, `POSTGRES_PASSWORD` e `RABBITMQ_PASSWORD` possuem valores hardcoded (ex: `"change_me_neo4j_password"`).
- `backend/app/services/chat_agent_loop.py`: Acesso direto a `os.getenv` em vez de utilizar `app.config.settings` (ex: `os.getenv("CHAT_TOOL_RISK_PROFILE")`).

**Próximos passos:**
- Remover valores default no `config.py` para credenciais e exigir injeção nas variáveis de ambiente.
- Refatorar `chat_agent_loop.py` para depender do `Settings`.
- Inserir itens SG-018 e OQ-015 no roadmap (`melhorias-possiveis.md`).

### 6. Isolamento e Dependências no Build / Testes
**Descrição:** O pipeline de build do backend e os testes do frontend apresentam riscos de quebra pela falta de restrições em ferramentas do ecossistema e estado compartilhado entre requisições.
**Evidências:**
- `backend/requirements.txt`: Dependências possuem ranges amplos (sem `requirements.lock` via pip-tools ou poetry), o que pode introduzir falhas silently se packages secundários atualizarem, e falta fixar `asyncpg` corretamente (apesar de estar no requirements de testes/base com condicional, não há lock determinístico).
- `backend/app/core/tools/productivity_tools.py`: Variáveis em escopo global de módulo (`_notes`, `_calendar_events`) vazam estado entre usuários e causam perda de dados em restarts.
- `frontend/src/app/core/auth/auth.service.spec.ts`: Testes unitários falham esporadicamente (timeouts/unhandled open requests) por não mockarem corretamente o `HttpClient` na chamada `loginWithPassword`.

**Próximos passos:**
- Congelar versões introduzindo pip-compile (lockfile).
- Refatorar a store de `productivity_tools.py` para uso de um serviço ou banco de dados com escopo por usuário/sessão.
- Refatorar testes do `AuthService` com `HttpTestingController`.
- Inserir PL-011, SG-019 e OQ-016 no roadmap (`melhorias-possiveis.md`).

## Achados do dia (2026-03-09)

### 7. Risco de Execução de Código e Manipulação de Arquivos via Componentes Core e Sandbox
**Descrição:** Observou-se que o Sandbox Python e ferramentas auxiliares estão operando com execuções inseguras (`exec`, `eval`, `shell=True`) e manipulando arquivos temporários e URLs de forma estática e não higienizada, propiciando potenciais RCE e SSRF na infraestrutura.
**Evidências:**
- `backend/app/core/tools/launcher_tools.py`: `subprocess` operando em modo shell (`shell=True`).
- `backend/app/core/infrastructure/python_sandbox.py`: Execução nativa e direta da string de código com `exec()`.
- `backend/app/core/tools/faulty_tools.py`: Uso de `eval()`.
- `backend/app/core/memory/log_aware_reflector.py`: Utilização de caminhos no diretório global compartilhado `/tmp/janus.log` sem escopo efêmero isolado.
- `backend/app/core/infrastructure/message_broker.py` & `backend/app/core/tools/agent_tools.py`: Uso de `urllib.request.urlopen` suscetível a schemes arbitrários.

**Próximos passos:**
- Remover `shell=True`, migrar de `eval` para `ast.literal_eval`, refatorar manipulação de logs para usar APIs temporárias seguras, e validar esquemas de URLs (HTTP/HTTPS).

### 8. Identificação de Múltiplos Riscos de Cadeia de Suprimento no Frontend
**Descrição:** Verificou-se que a camada de frontend baseia-se em bibliotecas atualmente exploráveis. Foram identificados múltiplos vetores incluindo Path Traversal, XSS, Bypass de Rate Limit (IPv6) e envenenamento de protótipos.
**Evidências:**
- `npm audit` aponta falhas severas nos pacotes `dompurify` (Moderate, XSS), `express-rate-limit` (High, IPv6 bypass), `hono` (High, Cookie Attribute Injection), `immutable` (High, Prototype pollution) e `tar` (High, Path Traversal).

**Próximos passos:**
- Engatilhar processo de bump de dependências frontend, atualizando pacotes para as respectivas minor/patch fix. Registrar e acompanhar vulnerabilidades não mitigadas.
