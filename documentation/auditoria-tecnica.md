# Auditoria Técnica - Janus

**Data:** 2025-05-23
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria focou na análise estática do código fonte (`backend/` e `frontend/`) para identificar áreas de simplificação, lógica frágil e riscos de segurança.

### 1. Simplificação e Dívida Técnica (Backend)

*   **Duplicação de Código Crítica**: O arquivo `backend/app/services/tool_service_improved.py` é idêntico a `backend/app/services/tool_service.py`. Isso sugere um refatoramento abandonado ou merge incorreto.
    *   **Evidência**: `diff backend/app/services/tool_service.py backend/app/services/tool_service_improved.py` (sem saída).
*   **Complexidade em `ChatService`**: O arquivo `backend/app/services/chat_service.py` possui 1722 linhas e acumula muitas responsabilidades (processamento de mensagens, streaming, chamadas de ferramentas, log de eventos).
    *   **Evidência**: `wc -l backend/app/services/chat_service.py` -> 1722.
*   **Inicialização Monolítica**: `backend/app/main.py` contém lógica de startup extensa e mistura configuração de middlewares, instrumentação e rotas, dificultando testes isolados.

### 2. Simplificação e Dívida Técnica (Frontend)

*   **God Object Service**: `frontend/src/app/services/backend-api.service.ts` (~700 linhas) centraliza TODAS as chamadas de API do sistema (Auth, Chat, System, Tools, Memory, etc.). Isso viola o Princípio da Responsabilidade Única (SRP) e dificulta a manutenção e testes.
    *   **Evidência**: `wc -l frontend/src/app/services/backend-api.service.ts` -> ~700. Contém métodos para `getSystemStatus`, `startChat`, `listTools`, `getMemoryTimeline`, etc.

### 3. Segurança e Vulnerabilidades

*   **Segredos Default em Código**: `backend/app/config.py` define senhas padrão inseguras (`"password"`, `"janus_pass"`) e `CORS_ALLOW_ORIGINS` como `["*"]`.
    *   **Risco**: Se implantado sem sobrescrever variáveis de ambiente, o sistema fica vulnerável. O CORS permissivo expõe a API a ataques CSRF/XSS de qualquer origem.
*   **Retorno de Token de Reset**: `backend/app/api/v1/endpoints/auth.py` no endpoint `/local/request-reset` retorna o token de reset no corpo da resposta se `ENVIRONMENT != "production"`.
    *   **Risco**: Depender de variável de ambiente para segurança é frágil. Se um ambiente de produção for configurado incorretamente como "development" ou "staging", qualquer um pode resetar senhas.
*   **Impersonação de Admin**: O endpoint `/token` (`issue_token`) permite que um admin gere tokens para QUALQUER usuário (`target_id`).
    *   **Risco**: Falta de auditoria específica para essa ação crítica pode permitir abuso de privilégio indetectado.

### 4. LGPD e Privacidade

*   **Retenção de Dados**: Embora exista `backend/app/services/data_retention_service.py`, não foi identificada chamada explícita para expurgo automático de logs ou dados sensíveis em `main.py` ou agendadores visíveis.
    *   **Ação**: Verificar se o worker de retenção está ativo e configurado corretamente.

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Remover `backend/app/services/tool_service_improved.py`.
    *   Remover defaults inseguros de `backend/app/config.py` (obrigar definição via env var ou falhar).
    *   Refatorar `backend-api.service.ts` quebrando em `AuthService`, `ChatService`, `SystemStatusService`, etc.

2.  **Médio Prazo (P2)**:
    *   Refatorar `ChatService` (backend) extraindo handlers específicos.
    *   Implementar auditoria robusta para geração de tokens de impersonação.
    *   Validar e documentar política de retenção de dados (LGPD).

---

# Auditoria Técnica - Janus

**Data:** 2026-02-20
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria focou na análise estática do código fonte (`backend/` e `frontend/`) para identificar áreas de simplificação, lógica frágil e riscos de segurança.

### 1. Simplificação e Dívida Técnica (Backend)

*   **Duplicação de Código (Persistente)**: O arquivo `backend/app/services/tool_service_improved.py` continua idêntico a `backend/app/services/tool_service.py`, ignorando recomendação anterior (DX-012).
    *   **Evidência**: `diff backend/app/services/tool_service.py backend/app/services/tool_service_improved.py` (sem saída).
*   **Complexidade em `ChatService`**: O arquivo `backend/app/services/chat_service.py` permanece monolítico (1722 linhas), dificultando manutenção e testes.

### 2. Simplificação e Dívida Técnica (Frontend)

*   **God Object Service (Crítico)**: `frontend/src/app/services/backend-api.service.ts` (~800 linhas) continua centralizando todas as chamadas de API, violando SRP (FE3-015).

### 3. Segurança e Vulnerabilidades

*   **Segredos Default em Código (Crítico)**: `backend/app/config.py` mantém senhas padrão (`"password"`, `"janus_pass"`) e `CORS_ALLOW_ORIGINS=["*"]`. (SG-011)
*   **Vazamento de Token de Reset (Crítico)**: `backend/app/api/v1/endpoints/auth.py` retorna o token de reset na resposta quando `AUTH_RESET_RETURN_TOKEN` é True (default). (SG-012)
*   **Impersonação sem Auditoria**: Endpoint `/token` permite impersonação por admin sem log explícito de auditoria de segurança.

### 4. Lógica Frágil e Concorrência

*   **Execução Assíncrona em Contexto Síncrono**: O uso de `loop.create_task` dentro de handlers de eventos SQLAlchemy (síncronos) em `backend/app/db/sync_events.py` para chamar `DataRetentionService` é frágil. Se o loop estiver fechando ou sobrecarregado, a limpeza de dados pode falhar silenciosamente.

### 5. LGPD e Privacidade

*   **Retenção de Logs e Auditoria**: Não foi identificada política automatizada de rotação de logs (`janus.log`) ou expurgo de eventos antigos na tabela de auditoria, risco de acumulação infinita de dados.
*   **Dados Pessoais em Logs**: `janus.log` é gravado em disco sem rotação configurada no nível da aplicação (depende de logrotate externo não verificado no repo).

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Remover `backend/app/services/tool_service_improved.py`.
    *   Corrigir `DataRetentionService` para usar `run_in_executor` ou background worker robusto.
    *   Desabilitar `AUTH_RESET_RETURN_TOKEN` por default em produção.
    *   Forçar erro no startup se senhas padrão forem usadas em produção.

2.  **Médio Prazo (P2)**:
    *   Implementar Job Cron para limpeza de logs de auditoria > 90 dias.
    *   Refatorar `backend-api.service.ts` em serviços de domínio (`AuthService`, `ChatService`).

---

# Auditoria Técnica - Janus

**Data:** 2026-02-27
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria baseia-se nas últimas modificações e no estado atual do sistema para rastrear a qualidade, lógica, e segurança:

### 1. Simplificação e Dívida Técnica
*   **Acesso Inconsistente a Configurações**: A classe `ChatAgentLoop` (`backend/app/services/chat_agent_loop.py`) utiliza chamadas diretas a `os.getenv` para ler variáveis de ambiente de risco (ex: `CHAT_TOOL_RISK_PROFILE`, `CHAT_TOOL_AUTO_CONFIRM`, etc.) em vez de usar o `app.config.settings` do Pydantic.
    *   **Evidência**: Múltiplas linhas como `risk_profile = os.getenv("CHAT_TOOL_RISK_PROFILE", RiskProfile.BALANCED)` em `backend/app/services/chat_agent_loop.py`.
*   **Componentes de Frontend Monolíticos**: O componente de visualização principal (`frontend/src/app/features/conversations/conversations.ts`) atingiu mais de ~1682 linhas de código, acoplando lógica pesada à renderização, violando o SRP.
    *   **Evidência**: `wc -l frontend/src/app/features/conversations/conversations.ts` retornando `1682`.

### 2. Segurança e Vulnerabilidades
*   **Ausência de Rate Limiting e Decoradores em Autenticação**: Os endpoints de login e requests sensíveis em `backend/app/api/v1/endpoints/auth.py` carecem de proteções explícitas de `@limiter.limit`.
    *   **Risco**: A ausência de limits específicos nas rotas de login eleva o risco de ataques de força-bruta em larga escala ou account takeover.

### 3. LGPD e Privacidade
*   **Log de Preview do Conteúdo de Chat (PII Risk)**: O serviço de eventos `backend/app/services/chat_event_publisher.py` publica snippets (`preview`) das mensagens do chat via `content_preview=payload["content"][:100]`. Considerando o escopo natural dos chats, isso implica provável registro de PII.
    *   **Risco**: Violações da política de LGPD se PII vazar em sistemas de monitoramento (ex: grafana, logs centrais) sem mecanismo de Opt-out ou purga associada.

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Sanitizar a propriedade `content_preview` em `ChatEventPublisher` ou removê-la para mitigar a exposição de PII/LGPD.
    *   Implementar `@limiter.limit` (Rate Limiting) explícito e restrito nos endpoints de `auth.py`.

2.  **Médio Prazo (P2)**:
    *   Refatorar o acesso a configurações do `ChatAgentLoop` transferindo as definições para `app.config.Settings` com validação de tipos via Pydantic.
    *   Decompor a view do frontend `conversations.ts` usando componentes menores.
