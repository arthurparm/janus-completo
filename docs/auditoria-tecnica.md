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

## Achados do dia (2026-03-08)

### 7. Segurança de Host e Endpoints Expostos
**Descrição:** O agente de Windows (`backend/windows_agent.py`) levanta um servidor FastAPI na porta 5001 expondo capacidades destrutivas e invasivas do OS (Screen Capture, Notificações Toast e Text-to-Speech) sem aplicar nenhum controle de acesso ou autenticação.
**Evidências:**
- `backend/windows_agent.py`: A inicialização ocorre com `uvicorn.run(app, host="0.0.0.0", port=5001)` e endpoints (ex: `@app.post("/screenshot")`) não exigem credenciais.

**Próximos passos:**
- Implementar verificação de token ou header (`Depends(verify_token)`) para garantir que apenas o daemon do Docker Janus possa acessar esses endpoints.
- Registrar SG-021 no backlog.

### 8. Risco de LGPD e Privacidade em Captura de Tela
**Descrição:** Ainda em `backend/windows_agent.py`, a ferramenta de captura de tela é capaz de gravar a área de trabalho inteira (fallback default de `ImageGrab.grab()` ou quando modo explícito for "full"). Isso implica que PII do usuário hospedado (mensagens pessoais, emails no fundo) podem ser gravados pelo agente sem ofuscação/minimização e sem log de auditoria explícito de consentimento.
**Evidências:**
- `backend/windows_agent.py`: Em `capture_active_window()`, se a janela não for detectada ou pywin32 falhar, ele faz o fallback global `return ImageGrab.grab()`.

**Próximos passos:**
- Adicionar logs de auditoria atrelando capturas ao request_id original. Restringir a captura "full" via flag de consentimento explícito, favorecendo sempre recortes mínimos (active window).
- Adicionar issue SG-022 no backlog de melhorias.

### 9. Vulnerabilidades Mapeadas de Dependências
**Descrição:** O Frontend acumula dependências defasadas ou com exploits conhecidos atestados via `npm audit` (ex: dompurify e node-server).
**Evidências:**
- Packages como `@hono/node-server`, `dompurify` e `express-rate-limit` no ecossistema do frontend apresentam issues de segurança de rede e XSS em suas versões atuais.

**Próximos passos:**
- Atualizar a árvore de dependências no pacote do frontend, validando eventuais breaking changes.
- Adicionar a issue SG-024 no `melhorias-possiveis.md`.

### 10. Vulnerabilidades de Código Fonte (Bandit)
**Descrição:** O analisador estático (Bandit) identificou dois riscos médios/críticos relacionados ao uso de bibliotecas na base de código, nomeadamente injeção de SQL e geração insegura de números.
**Evidências:**
- `backend/app/services/dedupe_service.py`: Construção de comandos SQL (ex: `f"UPDATE {table} SET user_id = :canon WHERE user_id IN :dups"`) usando f-strings pode abrir brechas caso o parâmetro `table` seja corrompido ou manipulado futuramente. Risco de SQL Injection (Bandit B608).
- `backend/app/api/v1/endpoints/auto_analysis.py`: Uso do `random` padrão para lidar com dados possivelmente aplicados a fluxos sensíveis, o que é inseguro criptograficamente (Bandit B311).

**Próximos passos:**
- Mudar para `secrets` module no lugar do `random` no `auto_analysis.py`.
- Refatorar a query de banco em `dedupe_service.py` limitando os nomes de tabelas permitidas ou usando construtores ORM de forma explícita.
- Documentar SG-020 e SG-025 no backlog.

## Achados do dia (2026-03-31)

### 11. API Drift Detectado
**Descrição:** A extração do inventário da API identificou um aumento no número de endpoints expostos, e 205 endpoints sem cobertura de testes. As alterações impactaram os módulos de Autonomy, Chat, Observability e Tasks.
**Evidências:**
- `outputs/qa/api_coverage_report.json` e `outputs/qa/api_inventory.json` refletem novos endpoints sem cobertura, ex: POST `/api/v1/tasks/consolidation` e GET `/api/v1/tasks/health/rabbitmq`.
**Próximos passos:**
- Documentar a nova cobertura e agendar criação de testes para os endpoints expostos recentemente, garantindo que a cobertura da API atinja as métricas alvo.
- Adicionar issue OQ-018 ao backlog.

## Achados do dia (2026-04-10)

### 12. Áreas Simplificáveis e Lógicas Frágeis (Ocultação de Erros)
**Descrição:** O analisador estático Bandit reportou B110 (Try, Except, Pass detectado) em múltiplos arquivos do backend. A presença contínua de blocos try-except silenciosos masca erros operacionais ou falhas lógicas, dificultando a resolução de bugs e deixando o código mais frágil a edge-cases e cenários de concorrência.
**Evidências:**
- `backend/app/repositories/llm_repository.py`: Omissão silenciosa na importação e geração de spans via OpenTelemetry (`except Exception: pass`).
- `backend/app/services/chat/message_orchestration_service.py`: Em dezenas de instâncias ao interagir com dependências como indexação e persistência de dados.
- `backend/app/core/infrastructure/auth.py`: Falhas silenciosas ao processar headers JWT e headers arbitrários.

**Próximos passos:**
- Documentar no backlog técnico (OQ-020).
- Substituir usos sistemáticos de `pass` por um fallback seguro, log apropriado (ex: `logger.warning()`) ou um Circuit Breaker/Fallback Response robusto que exponha a métrica de erro sem derrubar o request.

### 13. Lógicas Frágeis de Teste Isolado e Ausência de Timeouts
**Descrição:** Scripts de teste de ferramentas operacionais estão bypassando os pipelines padrão (como o pytest/CI), carecem de timeouts explícitos para suas funções e imprimem diretamente para stdout, arriscando instabilidades de rede prolongadas (hangs) e vazamentos de contexto PII caso rodados fora de um container.
**Evidências:**
- `tooling/test_debate_system.py`: Ausência de configuração de timeout assíncrono durante `debate_graph.astream()`, bem como prints diretamente para a saída padrão expondo lógica possivelmente sensível sem minimização via Logger.
- `tooling/seed-repro-scenarios.ps1`: Isolado em shell ao invés de atrelado a suítes de QA formal que detectem regressões semânticas.

**Próximos passos:**
- Englobar invocações assíncronas isoladas sob `asyncio.wait_for`.
- Converter a saída para logging estruturado via `structlog` com redação.
- Incorporar (OQ-019 e SG-050) no tracking oficial.

### 14. Riscos de LGPD e Privacidade em Observabilidade / Shadow IT
**Descrição:** Observou-se a presença de monitoramentos paralelos gerando logs textuais em chiaro ('Shadow IT'), expondo identidades de usuários da rede, além da falha de redação PII na camada de autorreflexão evolutiva que expõe transações a vazamentos por conta de leituras brutas em in-memory.
**Evidências:**
- `tooling/secure-tailscale-setup.ps1`: Grava nomes de host, transações de autenticação e falhas em claro dentro de `tailscale-security-monitor.log` via um script Powershell não rastreado, com ausência completa das restrições _PII_PATTERNS.
- `backend/app/core/memory/log_aware_reflector.py`: Ingere o `janus.log` diretamente para retroalimentar a evolução (`SafeEvolutionManager`) sem rodar o texto nos regexes de mascaramento (PII redaction), o que essencialmente realoca/repassa PII sem consentimento e sem expurgo garantido.

**Próximos passos:**
- Alterar script de Tailscale para usar output anônimo (hash no nome de host) e rodar via canais padronizados que possuam LGPD Scrubbing.
- Implementar chamada obrigatória de `redact_pii_text_only` no ingestão de `log_aware_reflector.py`.
- Mapear os riscos SG-050 e SG-040 para futura mitigação.

### 15. Vulnerabilidades de Injeção de Comando e Contorno de Autenticação
**Descrição:** Observou-se a presença contínua de vulnerabilidades de Code Injection em ambientes Windows (via `shell=True`) que podem resultar em RCE local, bem como falhas críticas de autenticação em `auth.py` ao depender do header não verificado `X-User-Id`. A vulnerabilidade no `X-User-Id` é agravada pela flag `AUTH_TRUST_X_USER_ID_HEADER=True` nativa no config padrão.
**Evidências:**
- `backend/app/core/tools/launcher_tools.py`: Subprocesses executados sob a diretiva insegura `shell=True` para comandos do SO.
- `backend/app/core/infrastructure/auth.py`: Validação de identidade via header `X-User-Id` sem validação de gateway (Trust por padrão local).

**Próximos passos:**
- Adicionar validações de injeção aos argumentos ou remover a tag `shell=True`.
- Forçar `AUTH_TRUST_X_USER_ID_HEADER=False` no default e garantir integridade via JWT (Issue já referenciada como SG-016).
- Adicionar issue de RCE/Sandbox (SG-051) para os processos de ferramentas locais no backlog.
