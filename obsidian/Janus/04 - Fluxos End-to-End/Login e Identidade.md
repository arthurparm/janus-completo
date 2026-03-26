---
tipo: fluxo
dominio: identidade
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Login e Identidade

## Objetivo
Documentar o fluxo real de autenticacao ponta a ponta do Janus usando exclusivamente o codigo como fonte: entrada do usuario, emissao e validacao de token, persistencia de sessao, carregamento do usuario atual e protecao de rotas.

## Responsabilidades
- Reconstruir o caminho real usado hoje pela UI web.
- Ligar frontend Angular, backend FastAPI e controles de seguranca.
- Explicar contratos de request/response, estados da sessao e pontos de falha.
- Separar o fluxo efetivo das capacidades existentes mas nao usadas pela UI atual.

## Entradas
- Credenciais digitadas pelo usuario em `/login` ou `/registro`.
- Token salvo em `localStorage` ou `sessionStorage`.
- Header `Authorization: Bearer <token>` nas requests autenticadas.
- Configuracoes de seguranca como `AUTH_JWT_SECRET`, `AUTH_RATE_LIMITS` e `AUTH_TRUST_X_USER_ID_HEADER`.

## Saidas
- Sessao autenticada no frontend (`isAuthenticated = true`, `user` populado).
- Token Janus assinado e persistido no navegador.
- `request.state.actor_user_id` preenchido no backend para requests autenticadas.
- Rotas protegidas liberadas ou negadas de acordo com autenticacao e role.

## Dependencias
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[03 - Frontend/Guards Interceptors e Estado]]
- [[02 - Backend/Segurança e Infra]]

## Escopo lido
- `frontend/src/app/features/auth/login/login.ts`
- `frontend/src/app/features/auth/login/login.html`
- `frontend/src/app/features/auth/register/register.ts`
- `frontend/src/app/features/auth/register/register.html`
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/core/interceptors/base-url.interceptor.ts`
- `frontend/src/app/services/auth.utils.ts`
- `frontend/src/app/services/api.config.ts`
- `frontend/src/app/app.config.ts`
- `frontend/src/app/app.routes.ts`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/core/infrastructure/auth.py`
- `backend/app/core/security/request_guard.py`
- `backend/app/core/security/passwords.py`
- `backend/app/core/security/auth_rate_limiter.py`
- `backend/app/main.py`
- `backend/app/repositories/user_repository.py`
- `backend/app/models/user_models.py`

## Resumo executivo
- O fluxo principal da UI e login local por `POST /api/v1/auth/local/login`.
- O backend devolve um token proprio do Janus e um payload de usuario; a UI passa a considerar a sessao autenticada imediatamente.
- Nao existe cookie de sessao, refresh token, logout server-side nem revogacao explicita de token no fluxo web atual.
- A restauracao da sessao entre recargas depende do token ainda estar salvo no navegador e de `GET /api/v1/auth/local/me` aceitar esse token.
- O frontend persiste apenas o token; o `current user` fica em memoria e e reconstruido no bootstrap.
- O backend transforma o token em identidade autenticada via middleware que popula `request.state.actor_user_id`.
- A navegacao protegida depende de `AuthGuard` e `RoleGuard`; a role `admin` vem do backend e e apenas consumida pelo frontend.
- `AuthGuard` envia `returnUrl`, mas o login atual ignora esse parametro e sempre redireciona para `/`.
- Login social aparece na tela, mas `loginWithProvider()` hoje apenas retorna `false` no modo local.

## Componentes participantes

### Frontend
- `LoginComponent`: coleta credenciais, dispara login e exibe recuperacao de senha.
- `RegisterComponent`: coleta dados de cadastro e autentica o usuario ao final do registro.
- `AuthService`: guarda o estado da sessao e faz bootstrap via `/auth/local/me`.
- `authInterceptor`: anexa `Authorization` e tenta anexar `X-User-Id`.
- `baseUrlInterceptor`: prefixa chamadas relativas com `API_BASE_URL`.
- `AuthGuard` e `RoleGuard`: protegem rotas privadas.

### Backend
- `POST /auth/local/login`: autentica usuario local.
- `POST /auth/local/register`: cria usuario local e ja emite token.
- `GET /auth/local/me`: materializa o usuario atual a partir do ator autenticado.
- `POST /auth/local/request-reset`: inicia reset de senha.
- `POST /auth/local/reset`: conclui reset de senha.
- `create_token()` e `verify_token()`: emissao e validacao do token interno.
- `actor_binding`: middleware que resolve o ator autenticado em cada request.
- `require_authenticated_actor_id()`: guarda server-side para endpoints autenticados.

## Artefatos e dados principais

### Token Janus
- Formato real: `base64url(payload_json).base64url(signature)` - não é JWT padrão de três partes.
- O payload contem pelo menos `user_id` e `exp`.
- A assinatura e `HMAC-SHA256(payload_json, AUTH_JWT_SECRET)`.
- O TTL usado por login e registro locais e `3600` segundos.
- Decodificação no frontend via `decodeTokenUserId()` lê a primeira parte do token ([auth.utils.ts:3-17](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/services/auth.utils.ts#L3-L17)).

### Usuario retornado para o frontend
- `id`
- `email`
- `username`
- `display_name`
- `roles`
- `permissions`

### Estado de sessao no frontend (Signals do AuthService)
- `_isAuthenticated`: signal privado, exposto como readonly `isAuthenticated` ([auth.service.ts:36-41](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L36-L41)).
- `_user`: signal privado contendo objeto User, exposto como readonly `user` ([auth.service.ts:37-42](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L37-L42)).
- `_authReady`: signal privado indicando quando o bootstrap terminou, exposto como readonly `authReady` ([auth.service.ts:39-44](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L39-L44)).
- `_firebaseAuthReady`: signal privado, marcado como `true` imediatamente, funciona como flag de compatibilidade ([auth.service.ts:38-43](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L38-L43)).

Observacoes:
- `user` nao e serializado em `localStorage` nem `sessionStorage` - fica apenas em memória.
- `firebaseAuthReady` e apenas uma flag de compatibilidade, não representa autenticação Firebase real.
- `currentUserValue` getter retorna valor atual do signal `_user` ([auth.service.ts:54-56](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L54-L56)).
- `isAdmin` computed verifica se `user.roles` contém 'admin' ([auth.service.ts:51](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L51)).

## Contratos HTTP reais

### Login local
Request:
```json
{
  "email": "user@example.com",
  "password": "Senha@123"
}
```

Response de sucesso:
```json
{
  "token": "<janus-token>",
  "user": {
    "id": "1",
    "email": "user@example.com",
    "username": "user",
    "display_name": "User Name",
    "roles": ["user"],
    "permissions": ["read"]
  }
}
```

Observacoes:
- O backend tambem aceita `username`, mas a tela de login atual envia apenas `email`.
- `password` tem validacao minima de 8 caracteres no backend.

### Cadastro local
Request:
```json
{
  "username": "user",
  "full_name": "User Name",
  "cpf": "00000000000",
  "phone": "11999999999",
  "email": "user@example.com",
  "password": "Senha@123",
  "terms": true
}
```

Response:
- Mesmo formato de `token + user` do login.

### Usuario atual
Request:
- `GET /api/v1/auth/local/me`
- Requer `Authorization: Bearer <token>`

Response:
```json
{
  "id": "1",
  "email": "user@example.com",
  "username": "user",
  "display_name": "User Name",
  "roles": ["user"],
  "permissions": ["read"]
}
```

### Reset de senha
Request de inicio:
```json
{
  "email": "user@example.com"
}
```

Request de confirmacao:
```json
{
  "token": "<reset-token>",
  "password": "NovaSenha@123"
}
```

## Sequencia ponta a ponta

### 1. Bootstrap da sessao na abertura da aplicacao
1. O Angular instancia `AuthService` e seu construtor executa `initializeAuth()` ([auth.service.ts:61-86](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L61-L86)).
2. `authReady` inicia como `false` e `_firebaseAuthReady` vai para `true` imediatamente ([auth.service.ts:66-67](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L66-L67)).
3. `getStoredAuthToken()` procura `JANUS_AUTH_TOKEN` primeiro em `localStorage` depois em `sessionStorage` ([auth.utils.ts:19-25](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/services/auth.utils.ts#L19-L25)).
4. Se nao houver token, o frontend sobe anonimo e marca `authReady = true` imediatamente.
5. Se houver token, `AuthService` chama `GET /v1/auth/local/me` com o token no header Authorization ([auth.service.ts:72-74](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L72-L74)).
6. O `baseUrlInterceptor` transforma a URL em `/api/v1/auth/local/me`.
7. O `authInterceptor` anexa `Authorization: Bearer <token>` e tenta extrair `X-User-Id` do token ([auth.interceptor.ts:18-20](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L18-L20)).
8. O backend resolve `request.state.actor_user_id` no middleware `actor_binding`.
9. `local_me()` usa esse ator autenticado para carregar o usuario.
10. Em sucesso, o frontend seta `_isAuthenticated.set(true)`, popula `_user.set(user)` e conclui com `_authReady.set(true)`.
11. Em falha, `clearSession()` remove token de ambos os storages, limpa `VISITOR_MODE_KEY`, zera `_user` e `_isAuthenticated` e finaliza como anonimo.

### 2. Login local
1. O usuario informa email e senha em `/login` via formulário reativo ([login.ts:22-26](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L22-L26)).
2. `LoginComponent.loginEmailPassword()` valida o formulario e bloqueia múltiplas chamadas via flag `loading` ([login.ts:43-51](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L43-L51)).
3. Se a tela ja acumulou 5 falhas, ela aplica um lock client-side de 60 segundos ([login.ts:114-118](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L114-L118)).
4. `AuthService.loginWithPassword(email, password, remember)` envia `POST /api/v1/auth/local/login` com tratamento de erro detalhado ([auth.service.ts:88-108](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L88-L108)).
5. O backend aplica `enforce_auth_rate_limit(..., endpoint_key="auth.local_login")`.
6. O backend procura usuario por email; se necessario, tenta username.
7. Se o usuario nao existir, nao tiver `password_hash` ou a senha nao conferir, devolve `401 Invalid credentials`.
8. Se autenticar, o backend emite token por `create_token(user.id, 3600)` e monta o payload de usuario por `_build_local_user()`.
9. O frontend persiste o token via `storeAuthToken(token, remember)` - `localStorage` quando `remember = true`, `sessionStorage` quando `false` ([auth.service.ts:98](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L98)).
10. O frontend remove `VISITOR_MODE_KEY`, seta `_isAuthenticated.set(true)` e grava `_user.set(out.user)` apenas em memoria.
11. `LoginComponent` espera 100 ms e navega sempre para `/` ([login.ts:58-59](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L58-L59)).
12. O query param `returnUrl` enviado pelo `AuthGuard` é ignorado - o redirecionamento sempre vai para a raiz, não restaura a rota original desejada.

### 3. Cadastro local
1. O usuario preenche `/registro` com username, nome, CPF, telefone, email, senha e aceite de termos.
2. O frontend valida CPF e aplica regras fortes de senha, incluindo negacao de senha que contenha dados pessoais do proprio formulario.
3. `AuthService.registerLocal(...)` envia `POST /api/v1/auth/local/register`.
4. O backend valida `terms`, unicidade de email/username/CPF e formato de CPF.
5. A senha e transformada por `hash_password()` antes de persistir.
6. O backend cria o usuario, grava consentimentos e define roles iniciais.
7. Em seguida, emite token e devolve `token + user`.
8. O frontend sempre salva esse token em `localStorage`.
9. O frontend tambem seta `isAuthenticated = true` e grava `user` em memoria.
10. A tela exibe sucesso e reseta o formulario, mas nao redireciona automaticamente; o usuario fica autenticado mesmo permanecendo em `/registro`.

### 4. Carregamento do usuario atual
1. Qualquer reload da aplicacao depende de `GET /api/v1/auth/local/me`.
2. O endpoint so funciona se `request.state.actor_user_id` tiver sido resolvido do bearer token.
3. O backend retorna o payload montado por `_build_local_user()`.
4. O frontend nao faz re-fetch de `/local/me` logo apos login ou cadastro; ele confia no `user` retornado por esses endpoints.
5. Se `/local/me` falhar no bootstrap, `AuthService.clearSession()` apaga token dos dois storages, remove `VISITOR_MODE_KEY` e volta a aplicacao para estado anonimo.

### 5. Protecao de rotas
1. O roteamento protege `''`, `conversations`, `conversations/:conversationId`, `tools` e `observability` com `AuthGuard`.
2. `admin/autonomia` exige `AuthGuard` e `RoleGuard` com `data.roles = ['admin']`.
3. `AuthGuard` espera `authReady$` antes de decidir via `combineLatest([authReady$, isAuthenticated$])` com `filter(([ready]) => ready)` para evitar race conditions.
4. Se a sessao nao estiver autenticada, `AuthGuard` navega para `/login?returnUrl=<rota-original>` e dispara notificacao de acesso negado.
5. Se a sessao estiver autenticada, a rota e liberada.
6. `RoleGuard` tambem espera `authReady$` e verifica se `user.roles` contém pelo menos uma role requerida (semântica OR).
7. Se nao houver usuario carregado após `authReady`, ele redireciona para `/login`.
8. Se houver usuario sem role suficiente, ele notifica erro "Acesso negado - Você não tem permissão para acessar esta página" e redireciona para `/`.
9. `PermissionGuard` existe com semantica AND para `permissions`, mas nao participa de nenhuma rota atual.
10. `NoAuthGuard` existe para bloquear acesso de usuários autenticados a telas públicas, mas nao está conectado a `/login` nem `/registro`.
11. `SystemReadyGuard` existe mas seu check atual apenas espelha `isAuthenticated$`, não representando prontidão real do sistema.

### 6. Logout e retorno a estado anonimo
1. O logout visivel no shell chama `AuthService.logout()`.
2. `logout()` apenas executa `clearSession()`.
3. Isso remove o token persistido, limpa `VISITOR_MODE_KEY`, zera `isAuthenticated` e `user`.
4. O `Header` entao navega explicitamente para `/login`.

## Roles e autorizacao no frontend
- `roles` e `permissions` chegam no payload `user` devolvido por login, registro e `/local/me`.
- `AuthService.isAdmin` e apenas um `computed()` sobre `user.roles?.includes('admin')`.
- O frontend nao calcula roles por conta propria; ele so consome o que o backend envia.
- No fluxo atual, a unica rota realmente amarrada a role e `admin/autonomia`.

## Emissao e validacao do token

### Emissao
- `create_token()` usa `AUTH_JWT_SECRET` para assinar o payload.
- Em producao, o segredo e obrigatorio.
- Fora de producao, se o segredo estiver ausente, o backend usa um segredo efemero por processo e registra warning.
- Consequencia: em ambientes sem segredo fixo, um restart invalida tokens emitidos anteriormente.

### Validacao
- `get_actor_user_id()` prioriza `Authorization: Bearer`.
- `verify_token()` rejeita token sem separador `.`, com assinatura diferente ou expirado.
- Se tudo estiver correto, retorna `user_id`.
- Em nao-producao, existe fallback opcional por `X-User-Id` quando `AUTH_TRUST_X_USER_ID_HEADER = true`.
- Em producao, o fallback por header e bloqueado.

### Implicacao no frontend
- `decodeTokenUserId()` e `decodeTokenExp()` leem a primeira parte do token.
- Isso parece estranho se alguem assumir JWT padrao, mas esta correto para o token customizado do Janus.
- O `authInterceptor` consegue derivar `X-User-Id` por causa desse formato.

## Regras de identidade e autorizacao no backend

### Resolucao do usuario
- `UserRepository.get_by_email()` e o caminho principal do login da UI.
- `UserRepository.get_by_username()` existe como alternativa suportada pelo endpoint.
- `local_me()` busca o usuario por `UserRepository.get_user(uid)`.

### Roles
- `_build_local_user()` lista roles do banco, converte para minusculas e adiciona `admin` se `repo.is_admin(user.id)` for verdadeiro.
- Se nenhuma role existir, a resposta para o frontend cai em `['user']`.
- No fluxo local atual, `permissions` e sempre `['read']`.

### Promocao para admin
- Se nao houver nenhum admin no sistema, o primeiro usuario pode ser promovido para `ADMIN`.
- O cadastro tambem pode promover usuario a admin por CPF allowlist.
- O login pode reforcar essa promocao via consentimento relacionado ao CPF.
- Essa decisao acontece toda no backend; o frontend apenas consome a role devolvida.

## Persistencia de sessao no frontend
- Chave padrao: `JANUS_AUTH_TOKEN`.
- `remember = true`: token vai para `localStorage`.
- `remember = false`: token vai para `sessionStorage`.
- `logout()` so limpa estado local e storage.
- Nao existe endpoint de logout, blacklist de token ou revogacao no backend para esse fluxo.

## Recuperacao de senha
1. `recoverAccess()` envia `POST /api/v1/auth/local/request-reset`.
2. O backend gera `secrets.token_urlsafe(32)`.
3. O valor salvo no banco e apenas `sha256(token)`.
4. O prazo vem de `AUTH_RESET_TOKEN_TTL_SECONDS`, com minimo de 300 segundos.
5. O token puro so e devolvido em `test` ou `ci` com `AUTH_RESET_RETURN_TOKEN = true`.
6. `submitResetPassword()` envia `POST /api/v1/auth/local/reset`.
7. O backend compara hash, verifica expiracao e substitui `password_hash`.
8. O token de reset e invalidado logo apos o uso ao limpar `password_reset_token_hash` e `password_reset_expires_at`.

## Tratamento de falhas

### Frontend
- `401` no login: mapeado para erro de credenciais invalidas ou sessao nao autorizada.
- `422` no login: mapeado para erro de request invalida, incluindo senha curta ou email invalido.
- `429` no login: mapeado para rate limit de autenticacao.
- Falha em `/local/me`: limpa sessao local e conclui bootstrap como anonimo.

### Backend
- `401`: credenciais invalidas ou token bearer invalido/ausente em endpoints protegidos.
- `403`: uso indevido de `/auth/token` por ator diferente do alvo sem permissao de admin.
- `409`: conflito de email, username ou CPF no cadastro.
- `422`: erro de validacao de payload, termos nao aceitos ou CPF invalido.
- `400`: token de reset invalido ou expirado.

## Controles de seguranca ligados ao fluxo

### Senha
- Armazenamento com `pbkdf2_sha256`.
- `salt` aleatorio de 16 bytes.
- `390000` iteracoes por padrao.
- Comparacao com `hmac.compare_digest()`.

### Rate limit de autenticacao
- `auth.local_login`: 10 tentativas por 60 segundos por IP + identificador.
- `auth.local_request_reset`: 5 tentativas por 60 segundos.
- `auth.local_reset`: 10 tentativas por 60 segundos.
- `auth.token`: 20 tentativas por 60 segundos.

### Exposicao de identidade
- O frontend injeta `Authorization` automaticamente quando ha token salvo.
- O backend converte esse token em `request.state.actor_user_id`.
- `require_authenticated_actor_id()` e o guard server-side basico para recursos autenticados.

## O que existe no codigo, mas nao compoe o fluxo web principal
- `loginWithProvider('google' | 'github')` existe na UI, mas retorna `false`.
- `POST /api/v1/auth/firebase/exchange` e `POST /api/v1/auth/supabase/exchange` existem no backend, mas nao sao usados pela tela de login atual.
- `POST /api/v1/auth/token` existe para emissao controlada de token por usuario, mas nao faz parte do fluxo de login da UI.
- `PermissionGuard`, `NoAuthGuard` e `SystemReadyGuard` existem, mas nao estruturam o caminho principal da navegacao atual.

## Diferencas entre o fluxo real e a intuicao comum
- Nao ha JWT padrao.
- Nao ha refresh token.
- Nao ha cookie de sessao.
- Nao ha logout server-side.
- O `returnUrl` gerado pelo guard nao e consumido pela tela de login.
- O cadastro autentica imediatamente, mas nao redireciona.
- `firebaseAuthReady` nao significa sessao Firebase validada.

## Arquivos-fonte
- `frontend/src/app/features/auth/login/login.ts`
- `frontend/src/app/features/auth/login/login.html`
- `frontend/src/app/features/auth/register/register.ts`
- `frontend/src/app/features/auth/register/register.html`
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/core/interceptors/base-url.interceptor.ts`
- `frontend/src/app/services/auth.utils.ts`
- `frontend/src/app/services/api.config.ts`
- `frontend/src/app/app.routes.ts`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/core/infrastructure/auth.py`
- `backend/app/core/security/request_guard.py`
- `backend/app/core/security/passwords.py`
- `backend/app/core/security/auth_rate_limiter.py`
- `backend/app/main.py`
- `backend/app/repositories/user_repository.py`
- `backend/app/models/user_models.py`

## Fluxos relacionados
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[03 - Frontend/Guards Interceptors e Estado]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[02 - Backend/Segurança e Infra]]

## Riscos e lacunas
- O fluxo de retorno pos-login ainda ignora `returnUrl`.
- A UI sugere login social, mas a implementacao efetiva esta desativada.
- Sem segredo fixo fora de producao, restart do backend invalida tokens emitidos antes.
- Como nao ha revogacao server-side, a invalidacao pratica do token depende de expiracao ou troca de segredo.
