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

**Data:** 2026-05-24
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria revisou o estado atual do código após a Sprint 1 e parte da Sprint 2.

### 1. Simplificação e Refatoração (Backend)

*   **Melhoria (Resolved)**: `ChatService` foi refatorado e reduzido para ~287 linhas, agindo agora como uma Facade para serviços especializados (`ConversationService`, `MessageOrchestrationService`, etc.).
*   **Complexidade (Novo)**: `backend/app/services/observability_service.py` cresceu para ~1200 linhas, acumulando responsabilidades de health check, métricas, logs, SLOs e anomalias. (Adicionado OQ-013)
*   **Dívida Técnica (Persistente)**: `backend/app/services/tool_service_improved.py` continua duplicado e sem uso aparente. Deve ser removido.

### 2. Simplificação e Refatoração (Frontend)

*   **Complexidade (Novo)**: `frontend/src/app/features/conversations/conversations.ts` (~1700 linhas) mistura responsabilidades de UI, gerenciamento de estado e lógica de negócios. Requer extração de Store e componentes menores. (Adicionado PX-013)
*   **God Object (Persistente)**: `frontend/src/app/services/backend-api.service.ts` (~1600 linhas) centraliza todas as chamadas de API.

### 3. Segurança e Configuração

*   **Melhoria (Resolved)**: `AUTH_RESET_RETURN_TOKEN` agora defaults para `False` em `config.py`, mitigando o risco de vazamento de tokens de reset de senha.
*   **Risco (Persistente)**: Segredos padrão (`change_me_...`) ainda existem em `backend/app/config.py` como defaults, embora `ENVIRONMENT` production force erro se `AUTH_JWT_SECRET` não estiver setado.

### 4. Confiabilidade e Lógica

*   **Fragilidade (Crítico/Persistente)**: Apesar de `OQ-012` estar marcado como "feito", o arquivo `backend/app/db/sync_events.py` ainda utiliza `loop.create_task` dentro de handlers síncronos do SQLAlchemy. Isso pode causar falhas silenciosas se o event loop não estiver disponível ou for encerrado prematuramente.

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Remover `backend/app/services/tool_service_improved.py`.
    *   Reinvestigar a correção de `OQ-012` para garantir execução assíncrona robusta (usando background tasks ou filas).
2.  **Curto Prazo (P1)**:
    *   Iniciar refatoração do `ConversationsComponent` (Frontend) para `ConversationStore`.
3.  **Médio Prazo (P2)**:
    *   Refatorar `ObservabilityService` em micro-serviços de domínio.
