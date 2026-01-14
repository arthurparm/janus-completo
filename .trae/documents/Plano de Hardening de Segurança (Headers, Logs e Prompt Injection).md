Vou implementar as correções de segurança solicitadas focando nos pontos críticos identificados:

### 1. Security Headers Middleware (Prioridade Alta)
Implementar um middleware dedicado para adicionar headers HTTP de segurança que estão faltando atualmente.
*   **Ação:** Criar `janus/app/core/middleware/security_headers.py`.
*   **Headers:**
    *   `Content-Security-Policy` (CSP): Restringir fontes de scripts/estilos.
    *   `Strict-Transport-Security` (HSTS): Forçar HTTPS.
    *   `X-Content-Type-Options`: Prevenir MIME sniffing.
    *   `X-Frame-Options`: Prevenir Clickjacking.
    *   `Referrer-Policy`: Controlar vazamento de referer.
*   **Integração:** Registrar este middleware em `janus/app/main.py`.

### 2. Sanitização de PII nos Logs
Integrar a lógica de redação de PII existente ao sistema de logs central.
*   **Ação:** Modificar `janus/app/core/infrastructure/logging_config.py`.
*   **Mudança:** Importar `redact_pii` de `janus/app/core/memory/security.py` e aplicá-la no processador de logs, garantindo que CPFs, e-mails e telefones sejam mascarados automaticamente em todos os logs da aplicação, não apenas chaves de API.

### 3. Mitigação de Prompt Injection (`PolicyEngine`)
Adicionar uma camada de validação de conteúdo no motor de políticas.
*   **Ação:** Atualizar `janus/app/core/autonomy/policy_engine.py`.
*   **Implementação:** Adicionar método `validate_content_safety` que verifica padrões comuns de injeção (ex: tentativas de ignorar instruções anteriores) antes de permitir o planejamento ou execução de ferramentas.
