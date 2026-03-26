---
tipo: dominio
dominio: frontend
camada: infraestrutura
fonte-de-verdade: codigo
status: ativo
---

# Guards Interceptors e Estado

## Objetivo
Explicar os mecanismos transversais do frontend que moldam autenticacao, navegacao protegida e comportamento HTTP global.

## Responsabilidades
- Mapear os interceptors efetivamente registrados.
- Registrar o papel dos guards no ciclo de navegacao.
- Ligar estado de auth e protecao de rotas.

## Entradas
- `core/auth`
- `core/guards`
- `core/interceptors`
- `app.config.ts`
- `app.routes.ts`

## Saidas
- Mapa de runtime da camada transversal do frontend.

## Dependencias
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[03 - Frontend/Shell e Navegação]]

## Cadeia HTTP ativa
- `baseUrlInterceptor`
- `authInterceptor`
- `errorLoggerInterceptor`
- `errorMappingInterceptor`

Ordem real:
- `baseUrlInterceptor -> authInterceptor -> errorLoggerInterceptor -> errorMappingInterceptor`

## O que cada interceptor faz

### `baseUrlInterceptor`
- Prefixa requests relativas com `API_BASE_URL`.
- Mantem URLs absolutas inalteradas.
- Evita double-prefix quando a URL ja veio com base normalizada.
- Nao prefixa assets e alguns endpoints especiais como `/healthz`.

### `authInterceptor`
- Le `JANUS_AUTH_TOKEN` de `localStorage` ou `sessionStorage` via `getStoredAuthToken()` ([auth.interceptor.ts:15](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L15)).
- Injeta `Authorization: Bearer <token>` quando a request ainda nao tem esse header ([auth.interceptor.ts:18-20](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L18-L20)).
- Tenta injetar `X-User-Id` a partir do token via `decodeTokenUserId()` ([auth.interceptor.ts:22-27](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L22-L27)).
- Nao persiste usuario nem reconstroi sessao; apenas propaga o token ja salvo.
- Nao falha requests anonimas; apenas atua quando o token esta disponivel.
- Para requests de histórico de chat, faz log debug detalhado com URL, headers e método ([auth.interceptor.ts:30-38](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/interceptors/auth.interceptor.ts#L30-L38)).

### `errorLoggerInterceptor`
- Registra erros para observabilidade do cliente.

### `errorMappingInterceptor`
- Mapeia indisponibilidade/offline e erros HTTP para mensagens mais controladas na UI.
- Nao reconstroi sessao e nao executa logout.

## Interceptors presentes no codigo, mas fora do runtime
- `frontend/src/app/core/interceptors/http.interceptor.ts` define classes para loading, timeout, retry e resposta a `401`.
- Esse arquivo nao esta registrado em `provideHttpClient()`.
- Portanto, qualquer leitura do fluxo que dependa dele esta incorreta para o runtime atual.

## Guards disponiveis
- `AuthGuard`
- `RoleGuard`
- `PermissionGuard`
- `NoAuthGuard`
- `SystemReadyGuard`

## Guards realmente no fluxo principal

### `AuthGuard`
- Protege as rotas privadas principais: `''`, `conversations`, `conversations/:conversationId`, `tools`, `observability`.
- Espera `authReady$` antes de decidir via `combineLatest([authReady$, isAuthenticated$])` com `filter(([ready]) => ready)` ([auth.guard.ts:42-44](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L42-L44)).
- Faz redirecionamento para `/login` com `returnUrl` quando a sessao nao existe via `this.router.navigate(['/login'], { queryParams: { returnUrl }, replaceUrl: true })` ([auth.guard.ts:52-55](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L52-L55)).
- Emite notificacao de warning "Acesso negado - Por favor, faça login para acessar esta página" ao bloquear acesso ([auth.guard.ts:57](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L57)).
- O `returnUrl` e gerado pelo guard, mas o `LoginComponent` atual nao o consome; depois do login a navegacao volta sempre para `/` ([login.ts:58-59](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/features/auth/login/login.ts#L58-L59)).

### `RoleGuard`
- Complementa `AuthGuard` em rotas administrativas, hoje apenas `admin/autonomia`.
- Espera `authReady$` e depende de `user.roles` via `combineLatest([authReady$, user$])` com `filter(([ready]) => ready)` ([auth.guard.ts:92-94](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L92-L94)).
- Usa semantica OR: basta uma role requerida existir em `user.roles` via `requiredRoles.some(role => user.roles?.includes(role) || false)` ([auth.guard.ts:101](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L101)).
- Se `user` ainda estiver ausente apos `authReady`, redireciona para `/login` ([auth.guard.ts:96-98](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L96-L98)).
- Se faltar role, notifica erro "Acesso negado - Você não tem permissão para acessar esta página" e redireciona para `/` ([auth.guard.ts:104-106](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/guards/auth.guard.ts#L104-L106)).

## Guards existentes, mas marginais ao fluxo atual

### `PermissionGuard`
- Implementa controle por permissoes.
- Usa semantica AND.
- Nao esta ligado a nenhuma rota atual.
- Nao espera `authReady`.
- Se vier a ser ligado sem ajuste, pode decidir cedo demais em reloads com sessao persistida.

### `NoAuthGuard`
- Serviria para barrar acesso de usuario autenticado a telas publicas.
- Hoje nao esta ligado a `/login` ou `/registro`.
- Consequencia pratica: usuario autenticado ainda pode abrir essas rotas manualmente.

### `SystemReadyGuard`
- No estado atual, seu criterio de prontidao e apenas `isAuthenticated$`.
- Isso nao representa prontidao real de sistema.

## Estado transversal relacionado a auth (Signals Angular)
- `AuthService` e a fonte de verdade da sessao em memoria usando Angular Signals.
- O token e a unica parte persistida entre recargas; `user` nao e salvo em storage.
- `currentUserValue` getter retorna `_user()` diretamente ([auth.service.ts:54-56](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L54-L56)).
- `user` e `isAdmin` sao signals derivados: `isAdmin = computed(() => this._user()?.roles?.includes('admin') ?? false)` ([auth.service.ts:51](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L51)).
- `authReady` controla quando os guards podem decidir sem race condition via `filter(([ready]) => ready)`.
- `isAuthenticated` signal controla acesso a rotas.
- `user` carrega `roles` e `permissions` vindos do backend no payload do login/me.
- A reconstituicao do `current user` acontece so no bootstrap via `GET /v1/auth/local/me`.
- `logout()` apenas limpa token/local state via `clearSession()`; nao faz chamada server-side ([auth.service.ts:195-197](file:///Users/arthurparaiso/repos/janus-completo/frontend/src/app/core/auth/auth.service.ts#L195-L197)).

## Leitura correta do runtime
- O frontend nao mantem uma sessao stateful no servidor.
- O comportamento transversal de autenticacao depende de token local + `/auth/local/me`.
- A protecao de rota aguarda a tentativa de bootstrap antes de redirecionar.
- O redirecionamento global por `401` que existe em outros arquivos nao participa do runtime real.
- O arquivo legado `http.interceptor.ts` ainda fala em limpar `localStorage['token']` e `localStorage['user']`, mas o runtime atual usa `JANUS_AUTH_TOKEN` e nao persiste `user`.

## Arquivos-fonte
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/*.ts`
- `frontend/src/app/app.config.ts`
- `frontend/src/app/app.routes.ts`

## Fluxos relacionados
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Riscos e lacunas
- Existe codigo transversal de HTTP que nao esta ativo e pode induzir interpretacao errada.
- `PermissionGuard` pode ter comportamento prematuro se passar a ser usado antes de adaptar a espera por `authReady`.
