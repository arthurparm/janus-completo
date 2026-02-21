# Auditoria Técnica - Janus

**Data:** 2025-05-23
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria focou na análise estática do código fonte (`janus/` e `front/`) para identificar áreas de simplificação, lógica frágil e riscos de segurança.

### 1. Simplificação e Dívida Técnica (Backend)

*   **Duplicação de Código Crítica**: O arquivo `janus/app/services/tool_service_improved.py` é idêntico a `janus/app/services/tool_service.py`. Isso sugere um refatoramento abandonado ou merge incorreto.
    *   **Evidência**: `diff janus/app/services/tool_service.py janus/app/services/tool_service_improved.py` (sem saída).
*   **Complexidade em `ChatService`**: O arquivo `janus/app/services/chat_service.py` possui 1722 linhas e acumula muitas responsabilidades (processamento de mensagens, streaming, chamadas de ferramentas, log de eventos).
    *   **Evidência**: `wc -l janus/app/services/chat_service.py` -> 1722.
*   **Inicialização Monolítica**: `janus/app/main.py` contém lógica de startup extensa e mistura configuração de middlewares, instrumentação e rotas, dificultando testes isolados.

### 2. Simplificação e Dívida Técnica (Frontend)

*   **God Object Service**: `front/src/app/services/janus-api.service.ts` (~700 linhas) centraliza TODAS as chamadas de API do sistema (Auth, Chat, System, Tools, Memory, etc.). Isso viola o Princípio da Responsabilidade Única (SRP) e dificulta a manutenção e testes.
    *   **Evidência**: `wc -l front/src/app/services/janus-api.service.ts` -> ~700. Contém métodos para `getSystemStatus`, `startChat`, `listTools`, `getMemoryTimeline`, etc.

### 3. Segurança e Vulnerabilidades

*   **Segredos Default em Código**: `janus/app/config.py` define senhas padrão inseguras (`"password"`, `"janus_pass"`) e `CORS_ALLOW_ORIGINS` como `["*"]`.
    *   **Risco**: Se implantado sem sobrescrever variáveis de ambiente, o sistema fica vulnerável. O CORS permissivo expõe a API a ataques CSRF/XSS de qualquer origem.
*   **Retorno de Token de Reset**: `janus/app/api/v1/endpoints/auth.py` no endpoint `/local/request-reset` retorna o token de reset no corpo da resposta se `ENVIRONMENT != "production"`.
    *   **Risco**: Depender de variável de ambiente para segurança é frágil. Se um ambiente de produção for configurado incorretamente como "development" ou "staging", qualquer um pode resetar senhas.
*   **Impersonação de Admin**: O endpoint `/token` (`issue_token`) permite que um admin gere tokens para QUALQUER usuário (`target_id`).
    *   **Risco**: Falta de auditoria específica para essa ação crítica pode permitir abuso de privilégio indetectado.

### 4. LGPD e Privacidade

*   **Retenção de Dados**: Embora exista `janus/app/services/data_retention_service.py`, não foi identificada chamada explícita para expurgo automático de logs ou dados sensíveis em `main.py` ou agendadores visíveis.
    *   **Ação**: Verificar se o worker de retenção está ativo e configurado corretamente.

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Remover `janus/app/services/tool_service_improved.py`.
    *   Remover defaults inseguros de `janus/app/config.py` (obrigar definição via env var ou falhar).
    *   Refatorar `janus-api.service.ts` quebrando em `AuthService`, `ChatService`, `SystemStatusService`, etc.

2.  **Médio Prazo (P2)**:
    *   Refatorar `ChatService` (backend) extraindo handlers específicos.
    *   Implementar auditoria robusta para geração de tokens de impersonação.
    *   Validar e documentar política de retenção de dados (LGPD).

---

# Auditoria Técnica - Janus

**Data:** 2026-02-20
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

Esta auditoria focou na análise estática do código fonte (`janus/` e `front/`) para identificar áreas de simplificação, lógica frágil e riscos de segurança.

### 1. Simplificação e Dívida Técnica (Backend)

*   **Duplicação de Código (Persistente)**: O arquivo `janus/app/services/tool_service_improved.py` continua idêntico a `janus/app/services/tool_service.py`, ignorando recomendação anterior (DX-012).
    *   **Evidência**: `diff janus/app/services/tool_service.py janus/app/services/tool_service_improved.py` (sem saída).
*   **Complexidade em `ChatService`**: O arquivo `janus/app/services/chat_service.py` permanece monolítico (1722 linhas), dificultando manutenção e testes.

### 2. Simplificação e Dívida Técnica (Frontend)

*   **God Object Service (Crítico)**: `front/src/app/services/janus-api.service.ts` (~800 linhas) continua centralizando todas as chamadas de API, violando SRP (FE3-015).

### 3. Segurança e Vulnerabilidades

*   **Segredos Default em Código (Crítico)**: `janus/app/config.py` mantém senhas padrão (`"password"`, `"janus_pass"`) e `CORS_ALLOW_ORIGINS=["*"]`. (SG-011)
*   **Vazamento de Token de Reset (Crítico)**: `janus/app/api/v1/endpoints/auth.py` retorna o token de reset na resposta quando `AUTH_RESET_RETURN_TOKEN` é True (default). (SG-012)
*   **Impersonação sem Auditoria**: Endpoint `/token` permite impersonação por admin sem log explícito de auditoria de segurança.

### 4. Lógica Frágil e Concorrência

*   **Execução Assíncrona em Contexto Síncrono**: O uso de `loop.create_task` dentro de handlers de eventos SQLAlchemy (síncronos) em `janus/app/db/sync_events.py` para chamar `DataRetentionService` é frágil. Se o loop estiver fechando ou sobrecarregado, a limpeza de dados pode falhar silenciosamente.

### 5. LGPD e Privacidade

*   **Retenção de Logs e Auditoria**: Não foi identificada política automatizada de rotação de logs (`janus.log`) ou expurgo de eventos antigos na tabela de auditoria, risco de acumulação infinita de dados.
*   **Dados Pessoais em Logs**: `janus.log` é gravado em disco sem rotação configurada no nível da aplicação (depende de logrotate externo não verificado no repo).

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Remover `janus/app/services/tool_service_improved.py`.
    *   Corrigir `DataRetentionService` para usar `run_in_executor` ou background worker robusto.
    *   Desabilitar `AUTH_RESET_RETURN_TOKEN` por default em produção.
    *   Forçar erro no startup se senhas padrão forem usadas em produção.

2.  **Médio Prazo (P2)**:
    *   Implementar Job Cron para limpeza de logs de auditoria > 90 dias.
    *   Refatorar `janus-api.service.ts` em serviços de domínio (`AuthService`, `ChatService`).

---

# Auditoria Técnica - Janus

**Data:** 2026-02-21
**Responsável:** Jules (AI Software Engineer)

## Achados do Dia

### 1. Simplificação e Dívida Técnica (Backend)

*   **Duplicação de Código (Resolvido)**: O arquivo `janus/app/services/tool_service_improved.py` foi removido nesta data. (DX-012 Feito).
*   **Complexidade Extrema em `ChatService`**: `janus/app/services/chat_service.py` atingiu 1720 linhas, centralizando lógica de SSE, ferramentas, métricas e persistência. (AG-011)

### 2. Simplificação e Dívida Técnica (Frontend)

*   **God Object Service (Agravamento)**: `front/src/app/services/janus-api.service.ts` cresceu para **1434 linhas**, duplicando de tamanho desde a primeira observação. A refatoração é urgente (FE3-015).

### 3. Segurança e Vulnerabilidades

*   **Segredos Default Persistentes**: Apesar da existência de testes de validação (`test_sg011_security_config.py`), o arquivo `janus/app/config.py` ainda contém strings hardcoded (`"change_me_neo4j_password"`, etc.).
    *   **Risco**: Dependência exclusiva de validação em runtime (se existir) para impedir deploy inseguro. Recomenda-se remover os defaults do código ou torná-los vazios/obrigatórios via Pydantic.
*   **PII em Logs (LGPD)**: O Daemon (`janus/app/interfaces/daemon/daemon.py`) loga o conteúdo bruto dos comandos de voz: `logger.info(f"Command received: {command}")`. Isso pode expor dados sensíveis ou PII nos logs de aplicação.

## Próximos Passos

1.  **Imediato (P0/P1)**:
    *   Sanitizar logs no Daemon (remover conteúdo bruto do comando ou usar nível DEBUG/TRACE).
    *   Refatorar `janus-api.service.ts` (Frontend).

2.  **Status de Itens Anteriores**:
    *   `janus/app/services/tool_service_improved.py` -> **Removido**.
    *   `AUTH_RESET_RETURN_TOKEN` -> **Corrigido** (default agora é False e validado por teste).
    *   Validação de Config -> **Existente em Testes**, mas defaults hardcoded permanecem.
