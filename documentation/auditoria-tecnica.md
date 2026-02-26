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

**Data:** 2026-02-23
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria contínua focou em identificar novas vulnerabilidades de segurança e oportunidades de refatoração, validando também o estado dos achados anteriores.

### 1. Simplificação e Dívida Técnica (Backend)

*   **Duplicação de Código (Crítica e Persistente)**: O arquivo `backend/app/services/tool_service_improved.py` permanece no repositório sendo idêntico a `backend/app/services/tool_service.py`. Deve ser removido imediatamente para evitar confusão.
    *   **Evidência**: Leitura de ambos os arquivos confirma conteúdo idêntico.
*   **God Object em Observabilidade**: O `backend/app/services/observability_service.py` acumula responsabilidades de Health Check, Metrics, Audit Logs, Anomaly Detection e SLO Reports. Deve ser refatorado em serviços menores (`HealthService`, `MetricsService`, `AuditService`).
    *   **Evidência**: Arquivo extenso com múltiplos domínios misturados.

### 2. Segurança e Vulnerabilidades

*   **Endpoints de Workspace Desprotegidos**: Os endpoints em `backend/app/api/v1/endpoints/workspace.py` (ex: `/system/shutdown`, `/workspace/artifacts/add`) dependem de `get_collaboration_service` que não aplica autenticação ou autorização. Qualquer cliente na rede pode desligar o sistema.
    *   **Evidência**: `shutdown_system` não possui `Depends(get_current_user)` ou verificação de role ADMIN.
*   **Confiança Indevida em Header de Identidade**: `backend/app/core/infrastructure/auth.py` confia no header `X-User-Id` se `AUTH_TRUST_X_USER_ID_HEADER` for True (default). Isso permite bypass de autenticação trivial se o gateway não sanitizar esse header.
    *   **Risco**: Impersonação total de qualquer usuário.
*   **Rate Limit Fail-Open**: O middleware `RateLimitMiddleware` (`backend/app/core/infrastructure/rate_limit_middleware.py`) falha "aberto" (permite requisição) se o Redis estiver indisponível ou script Lua falhar, a menos que `FAIL_CLOSED` seja ativado.
    *   **Evidência**: Código `except Exception: return await call_next(request)` em blocos de verificação.
*   **Risco de PII em Logs de Eventos**: `ChatEventPublisher` (`backend/app/services/chat_event_publisher.py`) e `ChatService` podem logar conteúdo de mensagens em nível INFO/DEBUG sem redação adequada.

### 3. Confiabilidade e Lógica Frágil

*   **Dispatch Assíncrono Inseguro (DataRetention)**: O problema de `loop.create_task` em `sync_events.py` persiste. A limpeza de dados do usuário (LGPD) pode ser perdida se o processo reiniciar.
    *   **Recomendação**: Substituir por publicação em fila persistente (RabbitMQ) para garantir execução assíncrona durável (Item OQ-013 adicionado).

## Próximos Passos

1.  **Imediato (P0)**:
    *   Proteger endpoints de `workspace.py` com `Depends(require_admin)`.
    *   Revisar e documentar o risco de `X-User-Id` em produção.
    *   Remover arquivo morto `tool_service_improved.py`.

2.  **Curto Prazo (P1)**:
    *   Refatorar `ObservabilityService` para reduzir complexidade.
    *   Migrar trigger de `DataRetentionService` para message broker.
    *   Sanitizar logs de `ChatEventPublisher`.
