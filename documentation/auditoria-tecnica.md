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

**Data:** 2026-02-24
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

### 1. Melhorias (Simplificação e Refatoração)

*   **Refatoração do `ChatService`**: O arquivo `backend/app/services/chat_service.py` foi massivamente refatorado, caindo de 1722 linhas para ~287 linhas. A lógica complexa foi delegada para `ChatAgentLoop` (282 linhas) e `ChatCommandHandler` (110 linhas), melhorando significativamente a modularidade.
    *   **Evidência**: `wc -l backend/app/services/chat_service.py` -> 287.

### 2. Dívida Técnica Persistente

*   **Duplicação de Código (Crítica)**: `backend/app/services/tool_service_improved.py` continua idêntico a `backend/app/services/tool_service.py`. Deve ser removido imediatamente. (DX-012, P0).
*   **God Object Frontend (Crítico)**: `frontend/src/app/services/backend-api.service.ts` cresceu para 1439 linhas (anteriormente ~800), agravando a violação de SRP. Requer refatoração urgente. (FE3-015, P0).

### 3. Confiabilidade e Lógica Frágil

*   **Instabilidade em Métricas Prometheus**: `backend/app/core/workers/neural_training_system.py` define métricas (`_TRAINING_JOBS`, etc.) no nível do módulo. Isso pode causar erros de `ValueError: Duplicated timeseries` durante testes ou reloads se não envolto em `try...except`. (OQ-013).
*   **Rate Limiter Fail-Open**: `backend/app/core/infrastructure/rate_limit_middleware.py` falha silenciosamente (desabilita limites) se o arquivo Lua estiver ausente ou Redis indisponível, a menos que `fail_closed` seja ativado. (OQ-014).

### 4. Segurança e Privacidade

*   **Risco de PII em Logs**: `ChatCommandHandler` loga o conteúdo completo do feedback do usuário (`args`) em `logger.info("user_feedback_received", feedback=args...)`. Se o usuário enviar dados sensíveis, estes serão persistidos em logs. (SG-014).
*   **Acesso a Configuração Inconsistente**: `ChatAgentLoop` utiliza `os.getenv` diretamente para `CHAT_TOOL_RISK_PROFILE`, ignorando a centralização em `app.config.settings` e potenciais overrides de teste. (PL-011).
*   **Segredos Default**: `backend/app/config.py` mantém senhas padrão.

## Próximos Passos

1.  **Imediato (P0)**:
    *   Remover `backend/app/services/tool_service_improved.py`.
    *   Iniciar decomposição do `backend-api.service.ts` (criar `AuthService` e `ChatService` no frontend).

2.  **Curto Prazo (P1)**:
    *   Envolver definição de métricas em `neural_training_system.py` com bloco `try...except ValueError` (padrão Registry).
    *   Sanitizar logs de feedback em `ChatCommandHandler` (logar apenas tamanho ou hash, ou aplicar redaction).
    *   Implementar verificação de existência do script Lua no startup do `RateLimitMiddleware` ou embutir o script no código python.

3.  **Médio Prazo (P2)**:
    *   Migrar `os.getenv` em `ChatAgentLoop` para `settings`.
