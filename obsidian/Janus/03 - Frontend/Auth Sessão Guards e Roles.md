---
tipo: dominio
dominio: frontend
camada: autenticacao
fonte-de-verdade: codigo
status: ativo
---

# Auth Sessão Guards e Roles

## Objetivo
Registrar como o frontend Angular implementa sessao, bootstrap de identidade, guards, roles e interacao com os endpoints de autenticacao.

## Responsabilidades
- Explicar como `AuthService` sobe, restaura e derruba a sessao.
- Documentar os interceptors e guards que realmente participam do runtime.
- Mostrar como a UI consome `roles` e `permissions`.
- Destacar diferencas entre comportamentos implementados e expectativas comuns.

## Entradas
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/core/interceptors/base-url.interceptor.ts`
- `frontend/src/app/app.config.ts`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/features/auth/login/login.ts`
- `frontend/src/app/features/auth/register/register.ts`
- `frontend/src/app/services/auth.utils.ts`

## Saidas
- Modelo mental unico do fluxo de auth no frontend.
- Mapa de guards ativos e comportamento de redirecionamento.
- Contrato da sessao local consumida pela UI.

## Dependencias
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[03 - Frontend/Guards Interceptors e Estado]]
- [[03 - Frontend/Shell e Navegação]]

## Estado de autenticacao no frontend

### Sinais expostos por `AuthService`
- `isAuthenticated`
- `user`
- `firebaseAuthReady`
- `authReady`

### Observables derivados
- `isAuthenticated$`
- `user$`
- `firebaseAuthReady$`
- `authReady$`

### Computeds relevantes
- `isAdmin`: verdadeiro quando `user.roles` contem `admin`
- `userEmail`: devolve `user.email` ou string vazia

## Bootstrap real da sessao
1. `AuthService` executa `initializeAuth()` no construtor ([auth.service.ts:61-86](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L61-L86)).
2. O startup sempre comeca com `authReady = false` e `_firebaseAuthReady.set(true)` imediatamente ([auth.service.ts:66-67](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L66-L67)).
3. `firebaseAuthReady` funciona como flag de compatibilidade, não dependendo de handshake real com Firebase Auth.
4. `getStoredAuthToken()` procura primeiro em `localStorage` e depois em `sessionStorage` via [auth.utils.ts:19-25](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/services/auth.utils.ts#L19-L25).
5. Se houver token, o frontend chama `GET ${API_BASE_URL}/v1/auth/local/me` com o token no header Authorization ([auth.service.ts:72-74](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L72-L74)).
6. Com `API_BASE_URL = /api`, a chamada efetiva fica em `/api/v1/auth/local/me`.
7. Se a resposta vier com usuario, o service popula `_user.set(user)`, marca `_isAuthenticated.set(true)` e conclui com `_authReady.set(true)` ([auth.service.ts:75-76](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L75-L76)).
8. Se a resposta falhar, `clearSession()` apaga o token dos dois storages, remove `VISITOR_MODE_KEY`, zera `_user` e `_isAuthenticated` e sobe a aplicacao como anonima ([auth.service.ts:78](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L78) e [auth.service.ts:188-193](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L188-L193)).
9. Se nao houver token salvo, nenhuma chamada a `/local/me` e feita e `authReady` vai para `true` imediatamente.

## Persistencia da sessao
- A chave padrao do token e `JANUS_AUTH_TOKEN`.
- `storeAuthToken(token, true)` grava em `localStorage`.
- `storeAuthToken(token, false)` grava em `sessionStorage`.
- O login respeita o checkbox `remember`.
- O cadastro ignora uma escolha de persistencia e sempre grava em `localStorage`.
- `logout()` apenas limpa storage e estado local; nao existe round-trip de encerramento no backend.

## Cadeia HTTP que impacta auth

### Interceptors realmente ativos
- `baseUrlInterceptor`
- `authInterceptor`
- `errorLoggerInterceptor`
- `errorMappingInterceptor`

Ordem de registro:
- `baseUrlInterceptor -> authInterceptor -> errorLoggerInterceptor -> errorMappingInterceptor`

### `baseUrlInterceptor`
- Prefixa requests relativas com `API_BASE_URL`.
- Nao prefixa URLs absolutas.
- Evita double-prefix.
- Ignora caminhos de assets e alguns endpoints raiz como `/healthz`.

### `authInterceptor`
- Le o token salvo por `getStoredAuthToken()` ([auth.interceptor.ts:15](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L15)).
- Se a request ainda nao tiver `Authorization`, injeta `Authorization: Bearer <token>` ([auth.interceptor.ts:18-20](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L18-L20)).
- Se a request ainda nao tiver `X-User-Id`, tenta decodificar o token e enviar esse header tambem ([auth.interceptor.ts:22-27](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L22-L27)).
- `decodeTokenUserId()` le a primeira parte do token (formato Janus: `payload.signature`), não JWT padrão ([auth.utils.ts:3-17](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/services/auth.utils.ts#L3-L17)).
- O interceptor nao exige autenticacao: requests anonimas continuam funcionando sem falhar no cliente.
- Para requests de histórico de chat, faz log debug detalhado ([auth.interceptor.ts:30-38](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L30-L38)).

### Interceptors existentes fora da cadeia atual
- `frontend/src/app/core/interceptors/http.interceptor.ts` contem classes para loading, timeout, retry e tratamento de `401`.
- Esse arquivo nao esta registrado em `provideHttpClient()`.
- Logo, qualquer comportamento de redirecionamento em `401` definido nele nao faz parte do runtime real.

## Fluxo de login no frontend
1. A tela `/login` coleta `email`, `password` e `remember` via formulário reativo ([login.ts:22-26](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L22-L26)).
2. O form exige email válido e password preenchida com validadores Angular.
3. `LoginComponent.loginEmailPassword()` bloqueia reentradas via `loading` e aplica lock local de 60 segundos após 5 falhas consecutivas ([login.ts:43-46](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L43-L46) e [login.ts:114-118](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L114-L118)).
4. `AuthService.loginWithPassword()` envia `POST /api/v1/auth/local/login` com `email` e `password` ([auth.service.ts:88-108](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L88-L108)).
5. Em sucesso, `storeAuthToken(token, remember)` persiste o token, remove `VISITOR_MODE_KEY`, seta `_isAuthenticated.set(true)` e `_user.set(out.user)` ([auth.service.ts:98-101](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L98-L101)).
6. Depois do sucesso, a tela espera 100 ms e navega sempre para `/` ([login.ts:58-59](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L58-L59)).
7. O `returnUrl` gerado pelo `AuthGuard` é ignorado - o redirecionamento sempre vai para a raiz.

## Tratamento de erro no login
- `401`: vira `reason = invalid_credentials` com mensagem "Email/usuario ou senha invalidos. Verifique os dados ou use 'Recuperar acesso'." ou "Sessao nao autorizada. Faca login novamente." ([auth.service.ts:216-225](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L216-L225)).
- `422`: vira `reason = invalid_request` com mensagens específicas para senha curta ("Senha invalida: use no minimo 8 caracteres.") ou email inválido ([auth.service.ts:227-241](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L227-L241)).
- `429`: vira `reason = rate_limited` com mensagem "Muitas tentativas. Aguarde 1 minuto e tente novamente." ([auth.service.ts:242-249](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L242-L249)).
- Outros casos: `reason = unknown` com mensagem genérica "Falha no login. Tente novamente.".
- O componente de login acumula tentativas falhas e bloqueia por 60 segundos após 5 falhas consecutivas ([login.ts:114-118](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L114-L118)).

## Recuperacao de senha na UI
- `recoverAccess()` chama `POST /api/v1/auth/local/request-reset`.
- Se a API devolver `reset_token`, a tela mostra o token ao usuario no proprio formulario.
- Se a API nao devolver token, a tela mostra uma mensagem neutra de recuperacao.
- `submitResetPassword()` chama `POST /api/v1/auth/local/reset`.
- O frontend exige minimo de 8 caracteres e confirmacao de senha antes de enviar.

## Cadastro no frontend
- `RegisterComponent` coleta `username`, `fullName`, `cpf`, `phone`, `email`, `password` e `terms`.
- O CPF e validado no cliente.
- A senha precisa:
  - ter pelo menos 8 caracteres
  - conter maiuscula
  - conter minuscula
  - conter numero
  - conter caractere especial
  - nao conter tokens derivados de nome, username, email, CPF ou telefone
- Em sucesso, `AuthService.registerLocal()` autentica imediatamente o usuario.
- A tela nao redireciona; ela mostra sucesso e reseta o formulario.

## Guards

### `AuthGuard`
- Espera `authReady$` ficar `true` antes de decidir ([auth.guard.ts:42-44](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L42-L44)).
- Usa `combineLatest([authReady$, isAuthenticated$])` com `filter(([ready]) => ready)` e `take(1)` para evitar race conditions.
- Se autenticado, libera a rota retornando `true`.
- Se nao autenticado, redireciona para `/login` com `returnUrl` via `this.router.navigate(['/login'], { queryParams: { returnUrl }, replaceUrl: true })` ([auth.guard.ts:52-55](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L52-L55)).
- Dispara notificacao de warning "Acesso negado - Por favor, faça login para acessar esta página" ([auth.guard.ts:57](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L57)).
- Implementa `CanActivate`, `CanActivateChild` e `CanLoad` para proteção completa de rotas.

### `RoleGuard`
- Tambem espera `authReady$` antes de decidir ([auth.guard.ts:92-94](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L92-L94)).
- Le `route.data['roles']` como array de strings requeridas ([auth.guard.ts:86](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L86)).
- Usa semantica OR: basta uma role requerida estar em `user.roles` via `requiredRoles.some(role => user.roles?.includes(role) || false)` ([auth.guard.ts:101](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L101)).
- Sem usuario carregado após `authReady`, redireciona para `/login` ([auth.guard.ts:96-98](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L96-L98)).
- Sem role suficiente, mostra notificação de erro "Acesso negado - Você não tem permissão para acessar esta página" e redireciona para `/` ([auth.guard.ts:104-106](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L104-L106)).

### `PermissionGuard`
- Le `route.data['permissions']`.
- Usa semantica AND: todas as permissoes exigidas precisam estar em `user.permissions`.
- Nao espera `authReady$`; se for usado em rotas carregadas logo no bootstrap, pode decidir cedo demais.
- Nao esta conectado a nenhuma rota atual.

### `NoAuthGuard`
- Bloqueia tela publica quando o usuario ja esta autenticado.
- Hoje nao esta ligado a `/login` nem a `/registro`.

### `SystemReadyGuard`
- Existe, mas o check atual apenas espelha `isAuthenticated$`.
- Nao representa uma verificacao real de prontidao do sistema.

## Rotas e protecao atuais
- `''`: `AuthGuard`
- `conversations`: `AuthGuard`
- `conversations/:conversationId`: `AuthGuard`
- `tools`: `AuthGuard`
- `observability`: `AuthGuard`
- `admin/autonomia`: `AuthGuard + RoleGuard` com `roles = ['admin']`
- `login`: publica
- `registro`: publica
- `**`: redireciona para `login`

## Roles e permissoes consumidas pela UI
- `isAdmin` deriva apenas de `user.roles`.
- A rota `admin/autonomia` depende desse array vindo do backend.
- `permissions` hoje chegam como `['read']` no fluxo local.
- Nao existe refresh dedicado de roles; mudancas de role so chegam quando o objeto `user` muda.

## Comportamentos importantes
- O frontend depende do token estar valido no storage para restaurar sessao.
- O retorno pos-login ignora `returnUrl`.
- Login social aparece na tela, mas nao autentica no codigo atual.
- `firebaseAuthReady` hoje nao prova sessao autenticada com Firebase.
- A UI confia no payload `user` devolvido por login e cadastro sem refazer `/local/me` logo em seguida.

## Arquivos-fonte
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/core/interceptors/base-url.interceptor.ts`
- `frontend/src/app/app.config.ts`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/features/auth/login/login.ts`
- `frontend/src/app/features/auth/register/register.ts`
- `frontend/src/app/services/auth.utils.ts`
- `frontend/src/app/services/api.config.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[03 - Frontend/Guards Interceptors e Estado]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Riscos e lacunas
- `returnUrl` e produzido pelo guard, mas nao consumido pela tela de login.
- O arquivo `http.interceptor.ts` pode induzir leitura errada do runtime porque nao esta registrado.
- `PermissionGuard`, `NoAuthGuard` e `SystemReadyGuard` existem, mas nao foram integrados ao fluxo principal atual.
