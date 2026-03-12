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

## Achados do dia (2026-03-12)

### 11. Silent Fail-Open em Quedas de Conexão com RabbitMQ (Confiabilidade)
**Descrição:** Observou-se que o backend `app.core.infrastructure.message_broker` falha silenciosamente capturando exceções gerais (`except Exception: pass`) em múltiplas chamadas (`channel.default_exchange.publish`, getters da Management API, e callbacks de consumo). Isso pode esconder indisponibilidades do RabbitMQ e colocar a aplicação em modo offline sem nenhum disparo de alerta claro (Silent Fail-Open).
**Evidências:**
- `backend/app/core/infrastructure/message_broker.py`: Blocos `try...except Exception: pass` engolem erros críticos (como `[Errno 111] Connection refused`) em métodos centrais como `_consume_loop` e envio de mensagens via `default_exchange.publish`.

**Próximos passos:**
- Adicionar logs explícitos nas cláusulas de exceção antes de dar `pass` ou ignorar.
- Integrar os alertas com as métricas do serviço de observabilidade.
- Acompanhamento sob a issue SG-030 em `melhorias-possiveis.md`.

### 12. Vulnerabilidades Mapeadas de Código Fonte (Bandit - B314 e B108)
**Descrição:** O analisador estático (Bandit) identificou vulnerabilidades relacionadas ao parsing de arquivos XML e hardcode de caminhos temporários.
**Evidências:**
- `backend/app/services/document_parser_service.py`: Utiliza `xml.etree.ElementTree.fromstring` para realizar o parsing de artefatos DOCX. O uso da biblioteca nativa é vulnerável a ataques XML (como Billion Laughs ou XXE), sendo sinalizado como B314 pelo Bandit.
- `backend/app/core/memory/log_aware_reflector.py`: Utiliza um caminho `"/tmp/janus.log"` predefinido, sendo categorizado como uso inseguro de temp directory (B108).
- Scripts como `backend/app/core/infrastructure/python_sandbox.py` contêm `try...except Exception: pass` e chamadas a `exec()` (B102, ignorado se estritamente validado mas preocupante).

**Próximos passos:**
- Substituir o uso de `xml.etree.ElementTree` pelo pacote seguro `defusedxml` nas dependências.
- Mover a definição dos caminhos temporários para usar a API nativa do Python `tempfile`.
- Acompanhamento sob a issue SG-031 em `melhorias-possiveis.md`.

### 13. Exposição Indevida do Agente Windows
**Descrição:** Reavaliação de riscos revelou que a aplicação do agente local `backend/windows_agent.py` não só está desprovida de autenticação, como sobe o servidor Uvicorn em `0.0.0.0:5001`.
**Evidências:**
- `backend/windows_agent.py`: Linha `uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")` permite acesso de qualquer dispositivo na LAN, permitindo execução RCE / screenshots para qualquer atacante não autorizado na rede interna.

**Próximos passos:**
- Redefinir `host` para `127.0.0.1` restringindo acesso a rede de loopback.
- Acompanhamento sob a issue SG-032.

### 14. Fragilidade em Chamadas de Rede de Testes e Scripts
**Descrição:** Testes e toolings de E2E chamam a rede via `urllib` ou `requests` sem garantir configurações de Timeout adequadas, o que pode bloquear CI/CD pipelines indefinidamente.
**Evidências:**
- Chamadas `urlopen` em `backend/app/core/infrastructure/message_broker.py` ou requisições na suite de E2E perdem parametrização de timeout (verificação secundária do Bandit e QA pipelines).

**Próximos passos:**
- Parametrizar tempos de resposta (timeouts) para 5s a 10s em scripts dependentes de rede.
- Acompanhamento sob a issue SG-033.
