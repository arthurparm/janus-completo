## Objetivo
- Estabelecer controles mínimos viáveis de segurança e governança desde o MVP, garantindo confiança, rastreabilidade e proteção por usuário/grupo.

## Escopo Inicial (MVP+)
- Autenticação por `X-API-Key` e preparação para OAuth2/JWT.
- RBAC básico com roles e checagens em endpoints críticos.
- Motor de políticas (Policy Engine) aplicando allowlist/blocklist, risco e rate limit.
- Consentimentos com escopos e trilhas de auditoria por usuário.
- Observabilidade e auditoria exportável por conversa/ação.

## Controles Principais
- Autenticação: reforçar `X-API-Key` em rotas não públicas (`janus/app/main.py:239-246`).
- Autorização: usar `Role`/`is_admin` onde faltam checagens (ex.: conversas, produtividade).
- Rate limiting: camada HTTP (`janus/app/core/infrastructure/rate_limit_middleware.py:54-87`) + por ferramenta (`janus/app/core/tools/action_module.py:365-430`).
- Policy Engine: validar chamadas de ferramentas e passos do planner (`janus/app/core/autonomy/policy_engine.py:61-116`).
- Consentimentos: exigir `scope` antes de ações sensíveis (ex.: calendário/e‑mail).

## Integrações no Código
- `janus/app/main.py`
  - Garantir middleware de correlação e rate limit ativo (linhas 218–229; 239–246).
- RBAC
  - Modelos/Repo: `janus/app/models/user_models.py:35-51`, `janus/app/repositories/user_repository.py:36-62`.
  - Endpoints: checagens explícitas em `janus/app/api/v1/endpoints/users.py:35-41` e operações de conversa `janus/app/repositories/chat_repository_sql.py:111-148`.
- Policy Engine
  - Validar ferramentas no fluxo: `janus/app/services/assistant_service.py:37-75`, `janus/app/services/autonomy_service.py:254-285`.
  - Configuração dinâmica: `update_policy_config` (`janus/app/services/autonomy_service.py:167-194`).
- Rate Limit
  - HTTP: `rate_limit_middleware.py:54-87`.
  - Por ferramenta: `ActionRegistry.check_rate_limit` e `record_call` (`janus/app/core/tools/action_module.py:365-430`).
- Consentimentos
  - Modelos/Repo/Endpoints: `janus/app/models/consent_models.py:1-17`, `janus/app/repositories/consent_repository.py:12-24`, `janus/app/api/v1/endpoints/consents.py:22-68`.
  - Uso em produtividade: `_ensure_consent` (`janus/app/api/v1/endpoints/productivity.py:19-22,38-41`).

## Dados e Modelos
- Canonizar `ConsentScope` com enum único e evitar duplicidade entre modelos globais e por usuário.
- Persistir trilhas de consentimento (quem/quando/o quê), com possibilidade de revogação.
- Registrar políticas por usuário/grupo (allowlist, limites, risco).

## Observabilidade e Auditoria
- Propagar `TRACE_ID` e `user_id` em spans e logs (ver `janus/app/core/infrastructure/logging_config.py`).
- Expor auditoria de ferramentas e conversas (`janus/app/api/v1/endpoints/observability.py:93-97`).
- Dashboards centrados no usuário (Grafana) e export de auditoria.

## Fluxos HITL (opcional desde cedo)
- Introduzir revisão humana para escopos sensíveis (ex.: enviar e‑mail, alterar arquivos).
- Orquestrar via broker/filas (`janus/app/core/infrastructure/message_broker.py:69-123,258-335`).

## Quick Wins
- Ativar/enforcar `X-API-Key` nas rotas; confirmar lista de exceções.
- Exigir consentimento nos endpoints de produtividade com `_ensure_consent`.
- Aplicar `ActionRegistry` rate limits em todas as ferramentas registradas.
- Adicionar checagens `is_admin` onde operações são destrutivas de dados públicos.

## Roadmap (4–8 semanas)
- Semana 1–2: reforço de autenticação, RBAC mínimo, consentimentos e rate limit; auditoria básica.
- Semana 3–4: Policy Engine abrangendo escopos/risco; export de auditoria; testes de segurança.
- Semana 5–8: OAuth2/JWT por usuário, políticas dinâmicas, HITL e painéis de auditoria.

## Critérios de Aceitação
- Políticas aplicadas por escopo; consentimentos registrados e revogáveis.
- Tracing por conversa/ação; painel por usuário; auditoria exportável.
- RBAC funcional nos endpoints críticos; limites respeitados em HTTP e ferramentas.

## Riscos e Mitigação
- Duplicidade de modelos de consentimento → consolidar enum/Repo único.
- Vazamento de contexto de usuário → revisar logs/telemetria; mascarar dados sensíveis.
- Bypass de rate limit em ferramentas novas → enforce via `ActionRegistry` e testes.

## Referência
- Baseado em `/c:/repos/janus-completo/docs/pendencias-janus.md` e nos arquivos citados acima.
