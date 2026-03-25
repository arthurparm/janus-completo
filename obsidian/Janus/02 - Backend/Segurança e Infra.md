---
tipo: dominio
dominio: backend
camada: seguranca
fonte-de-verdade: codigo
status: ativo
---

# Segurança e Infra

## Objetivo
Mapear os guardrails transversais do backend com foco em autenticacao, autorizacao, limitacao de abuso e infraestrutura de protecao que sustenta os fluxos expostos pela API.

## Responsabilidades
- Cobrir emissao e validacao de token.
- Explicar como a identidade autenticada entra no request lifecycle.
- Registrar rate limits, headers e guards de endpoint.
- Ligar autenticacao classica aos demais controles de risco do backend.

## Entradas
- Headers HTTP, em especial `Authorization` e opcionalmente `X-User-Id` fora de producao.
- Segredos e flags de ambiente como `AUTH_JWT_SECRET`, `PUBLIC_API_KEY`, `AUTH_TRUST_X_USER_ID_HEADER`.
- Endpoints de auth em `backend/app/api/v1/endpoints/auth.py`.
- Guards de request e middlewares globais.

## Saidas
- Visao consolidada da seguranca operacional do backend.
- Mapa do caminho que transforma bearer token em ator autenticado.

## Dependencias
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Camadas de protecao

### Validacao de segredos no boot
- `secret_validator` roda no startup.
- Em producao, bloqueia o boot se segredos criticos ainda estiverem em valores default inseguros conhecidos.

### Middlewares globais relevantes
- `SecurityHeadersMiddleware`
- `DomainSLOMetricsMiddleware`
- `CorrelationMiddleware`
- `RateLimitMiddleware`
- `CORSMiddleware`
- `actor_binding`
- `require_api_key` quando `PUBLIC_API_KEY` estiver configurada

## Auth do backend

### Token interno do Janus
- O backend nao usa JWT padrao no fluxo local principal.
- `create_token()` serializa um payload com `user_id` e `exp`.
- Esse payload vira a primeira parte do token em base64url.
- A segunda parte e uma assinatura `HMAC-SHA256` do JSON do payload.
- `verify_token()` recompõe a assinatura e tambem verifica expiracao.

### Segredo de assinatura
- `AUTH_JWT_SECRET` e obrigatorio em producao.
- Fora de producao, se o segredo estiver ausente, o backend usa um segredo efemero por processo.
- Isso simplifica dev/teste, mas faz tokens antigos pararem de validar depois de restart quando o segredo nao e fixo.

## Binding da identidade autenticada

### Middleware `actor_binding`
- Roda em toda request.
- Chama `get_actor_user_id(request)`.
- Se houver `Authorization: Bearer <token>`, tenta validar o token e extrair `user_id`.
- O resultado vai para `request.state.actor_user_id`.

### Fallback por header
- Se nao houver bearer valido, `get_actor_user_id()` pode consultar `X-User-Id`.
- Esse caminho so e permitido fora de producao e com `AUTH_TRUST_X_USER_ID_HEADER = true`.
- Em producao, o backend ignora esse fallback.

### Guards server-side
- `require_authenticated_actor_id(request)` exige ator autenticado e devolve `401` caso contrario.
- `require_admin_actor(request)` exige que o ator seja admin.
- `require_same_user_or_admin(request, target_user_id)` restringe acesso a dono do recurso ou admin.

## Endpoints de autenticacao relevantes

### Login e sessao local
- `POST /api/v1/auth/local/login`
- `POST /api/v1/auth/local/register`
- `GET /api/v1/auth/local/me`
- `POST /api/v1/auth/local/request-reset`
- `POST /api/v1/auth/local/reset`

### Troca de token com providers
- `POST /api/v1/auth/firebase/exchange`
- `POST /api/v1/auth/supabase/exchange`

### Emissao controlada de token
- `POST /api/v1/auth/token`
- Exige ator autenticado.
- So permite emitir token para o proprio usuario, exceto se o ator for admin.

## Regras de auth local

### Login
- Aceita `email` ou `username` e `password`.
- Aplica rate limit por `auth.local_login`.
- Rejeita usuario inexistente, usuario sem senha local e senha incorreta com `401 Invalid credentials`.
- Se autenticado, emite token por `create_token()` e responde com `user`.

### Registro
- Exige `terms = true`.
- Valida unicidade de email, username e CPF.
- Armazena senha com hash PBKDF2.
- Persiste consentimentos relevantes.
- Pode atribuir role `ADMIN` ao primeiro usuario ou por CPF allowlist.
- Se nao houver promocao especial, garante role `USER`.

### Usuario atual
- `local_me()` depende diretamente de `request.state.actor_user_id`.
- Se nao houver ator, responde `401`.
- Se o ator nao existir mais no banco, responde `404`.

### Reset de senha
- `local_request_reset()` aplica rate limit e gera token aleatorio.
- O valor persistido no banco e apenas o hash SHA-256 do token.
- O token puro so pode ser devolvido em ambientes `test` ou `ci` com opt-in.
- `local_reset_password()` valida hash e expiracao antes de atualizar a senha.

## Password handling
- `hash_password()` usa `pbkdf2_sha256`.
- `salt` aleatorio de 16 bytes.
- `390000` iteracoes por padrao.
- `verify_password()` usa `hmac.compare_digest()` para comparar o derivado com o esperado.

## Rate limiting de auth
- `auth.token`: 20 tentativas por 60 segundos.
- `auth.local_login`: 10 tentativas por 60 segundos.
- `auth.local_request_reset`: 5 tentativas por 60 segundos.
- `auth.local_reset`: 10 tentativas por 60 segundos.
- A chave do bucket combina endpoint, IP e identificador normalizado.

## Papel do backend no fluxo de identidade do produto
- O frontend envia o bearer token.
- O middleware resolve `actor_user_id`.
- Os endpoints leem esse ator via guards de request.
- O payload de usuario devolvido pelo backend define `roles` e `permissions` que a UI consome.
- A role `admin` que protege `admin/autonomia` nasce aqui, nao no frontend.

## Outros guardrails de seguranca do backend
- `PUBLIC_API_KEY` pode exigir `X-API-Key` globalmente para quase toda a API.
- `SecurityHeadersMiddleware` fortalece resposta HTTP.
- `RateLimitMiddleware` existe alem do limitador especifico de auth.
- Em superfices de tools, a seguranca continua em `PolicyEngine`, `ToolExecutorService`, `python_sandbox` e `command_sandbox`.

## Relacao com o fluxo Login e Identidade
- O fluxo documentado no frontend so funciona porque o backend aceita o token customizado via `Authorization`.
- `GET /auth/local/me` e o elo entre token persistido no navegador e sessao restaurada na UI.
- A persistencia da identidade na UI nao implica sessao stateful no backend; o backend continua stateless em relacao ao token.
- O fluxo de logout web e somente client-side porque nao ha endpoint de revogacao nesse caminho.

## Arquivos-fonte
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/core/infrastructure/auth.py`
- `backend/app/core/security/request_guard.py`
- `backend/app/core/security/passwords.py`
- `backend/app/core/security/auth_rate_limiter.py`
- `backend/app/main.py`
- `backend/app/core/middleware/security_headers.py`
- `backend/app/core/infrastructure/rate_limit_middleware.py`
- `backend/app/core/infrastructure/python_sandbox.py`
- `backend/app/core/autonomy/policy_engine.py`
- `backend/app/core/tools/command_sandbox.py`
- `backend/app/services/tool_executor_service.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[06 - Qualidade e Testes/Contratos Cobertos]]
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]

## Riscos e lacunas
- A seguranca e distribuida entre middleware, endpoint, repositorio e servicos, exigindo leitura transversal.
- O fallback por `X-User-Id` em nao-producao pode ser mal interpretado se for confundido com o comportamento de producao.
- Sem revogacao server-side no fluxo web, a invalidez pratica do token depende de expiracao ou troca de segredo.
