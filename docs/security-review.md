# Security Review - Weekly Audit

Data: 2026-02-23
Responsavel: Jules (AI Agent)
Escopo: Backend Security, Config, Auth, Rate Limiting, Dependencies.

## 1. Resumo Executivo

A varredura detectou riscos críticos de segurança relacionados à configuração de segredos, confiança implícita em headers de autenticação e vazamento potencial de PII em logs. A infraestrutura de rate limiting depende do Redis e pode falhar fechada em produção, o que é um comportamento de risco para disponibilidade.

## 2. Checklist de Verificação

| Categoria | Item | Status | Observação |
|---|---|---|---|
| **Auth** | Endpoint de troca de token (Supabase/Firebase) validado | ✅ | `auth.py` valida tokens externos antes de emitir JWT interno. |
| **Auth** | Header `X-User-Id` confiável | ❌ | **CRÍTICO:** `backend/app/core/infrastructure/auth.py` confia no header se `AUTH_TRUST_X_USER_ID_HEADER` for True, permitindo impersonation se não houver gateway na frente. |
| **Secrets** | Segredos hardcoded no código | ❌ | **ALTO:** `backend/app/config.py` contém defaults inseguros para `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`. |
| **Secrets** | Validação de segredos em produção | ❌ | Não há validação que impeça o uso de segredos default em produção. |
| **Logging** | Redação de PII em logs | ⚠️ | **MÉDIO:** `ChatEventPublisher` e `CollaborationService` podem logar conteúdo de mensagens/artefatos. `logging_config.py` tem redação básica, mas insuficiente para objetos complexos. |
| **Rate Limit** | Proteção contra brute-force | ⚠️ | **MÉDIO:** Middleware existe (`RateLimitMiddleware`), mas endpoints de auth (`/login`, `/refresh`) não têm limites específicos documentados no código. |
| **Rate Limit** | Fail-open vs Fail-closed | ⚠️ | Configurado para `fail-closed` em produção se Redis cair (`settings.RATE_LIMIT_FAIL_CLOSED`), risco de DoS acidental. |
| **Deps** | Dependências vulneráveis | ⚠️ | `backend/requirements.txt` usa `asyncpg==0.29.0` (ok), mas `sqlalchemay==2.0.45` e outras libs sem lock file (apenas requirements.txt) geram risco de supply chain. |

## 3. Gaps Identificados e Recomendações

### 3.1. Autenticação e Autorização (P0)
- **Gap:** Confiança no header `X-User-Id` em `auth.py`.
- **Risco:** Um atacante pode forjar esse header se tiver acesso direto à porta da API, ignorando o JWT.
- **Recomendação:** Remover suporte a `X-User-Id` em produção ou exigir mTLS/IP allowlist estrito para o gateway. Definir `AUTH_TRUST_X_USER_ID_HEADER=False` por padrão.

### 3.2. Gerenciamento de Segredos (P0)
- **Gap:** Valores default ("change_me_...") em `config.py`.
- **Risco:** Deploy acidental em produção com senhas padrão.
- **Recomendação:** Adicionar validador Pydantic que lança erro fatal se `ENVIRONMENT=production` e os segredos forem os defaults.

### 3.3. Proteção de Dados (PII) (P1)
- **Gap:** Logs de `ChatEventPublisher` e `CollaborationService` podem conter PII do usuário.
- **Risco:** Violação de LGPD/GDPR se logs forem vazados ou retidos indevidamente.
- **Recomendação:** Implementar `PII Redactor` robusto no nível do `structlog` que varre recursivamente dicionários/JSONs antes de emitir o log.

### 3.4. Disponibilidade (P1)
- **Gap:** Rate Limit configurado para `fail-closed` em produção.
- **Risco:** Se o Redis cair, toda a API retorna 503.
- **Recomendação:** Mudar para `fail-open` (logar erro mas permitir requisição) ou garantir HA do Redis.

## 4. Próximos Passos

1. Criar tasks de correção para os itens P0 (Auth e Secrets).
2. Refinar a política de redação de logs.
3. Fixar versões de dependências com `pip-tools` ou similar para evitar drift.
