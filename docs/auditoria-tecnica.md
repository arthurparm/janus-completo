# Auditoria Técnica - Achados do Dia

## Data: 2026-02-28

### 1. Áreas Simplificáveis
- **God Objects:**
  - `frontend/src/app/services/backend-api.service.ts` (~1638 linhas).
  - `backend/app/services/observability_service.py` (~1200 linhas).
  - `frontend/src/app/features/conversations/conversations.ts` (~1700 linhas).
- **Padrões Inconsistentes:**
  - `ChatAgentLoop` utiliza `os.getenv` diretamente para configuração, ignorando o objeto centralizado `app.config.settings`.
- **Duplicação:**
  - O arquivo `backend/app/services/tool_service_improved.py` é uma duplicação técnica de `tool_service.py` (já mapeado na melhoria DX-012).

### 2. Lógicas Frágeis
- **Armazenamento em Memória Não-Persistente:**
  - `backend/app/core/tools/productivity_tools.py` faz uso de dicionários globais na memória (`_notes`, `_calendar_events`), gerando risco de perda de dados e problemas de concorrência.
- **Testes Flaky/Edge Cases:**
  - Os testes em `frontend/src/app/core/auth/auth.service.spec.ts` que testam `loginWithPassword` não mockam adequadamente o HTTP Client, levando a timeouts frequentes.

### 3. Vulnerabilidades de Segurança
- **AuthN/AuthZ:**
  - Endpoints de `backend/app/api/v1/endpoints/workspace.py` dependem de `get_collaboration_service` que não força autenticação, expondo endpoints críticos como `add_artifact` e `shutdown_system`.
  - Vulnerabilidade crítica em `backend/app/core/infrastructure/auth.py`, que confia cegamente no cabeçalho `X-User-Id` (`AUTH_TRUST_X_USER_ID_HEADER=True`), permitindo bypass/impersonation.
- **Rate Limiting:**
  - Endpoints em `backend/app/api/v1/endpoints/auth.py` (login, refresh) carecem de rate limit (`@limiter.limit`), abrindo vetor para ataques de força bruta.

### 4. Riscos LGPD e Privacidade (PII Logging)
- **Log de Conteúdo Sensível:**
  - `ChatCommandHandler`: loga conteúdo de feedback completo do usuário em `args`.
  - `ChatEventPublisher`: loga previews de mensagens em `_publish_to_log`.
  - `CollaborationService`: loga o conteúdo de mensagens e artefatos.
  - `backend/app/interfaces/daemon/daemon.py`: loga os comandos de voz em texto cru.
  - `backend/app/core/tools/productivity_tools.py`: loga metadados de e-mails (remetente, assunto).

## Próximos Passos
1. Atualizar o `melhorias-possiveis.md` com as novas descobertas listadas acima.
2. Planejar sprints de refatoração para God Objects.
3. Abrir tickets emergenciais para correção imediata (P0) das vulnerabilidades de Auth e LGPD.
