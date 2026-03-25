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
- Le token de `localStorage` ou `sessionStorage`.
- Injeta `Authorization: Bearer <token>` quando a request ainda nao tem esse header.
- Tenta injetar `X-User-Id` a partir do token.
- Nao falha requests anonimas; apenas atua quando o token esta disponivel.

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
- Protege as rotas privadas principais.
- Espera `authReady` antes de decidir.
- Faz redirecionamento para `/login` com `returnUrl` quando a sessao nao existe.

### `RoleGuard`
- Complementa `AuthGuard` em rotas administrativas.
- Hoje participa apenas de `admin/autonomia`.
- Espera `authReady` e depende de `user.roles`.

## Guards existentes, mas marginais ao fluxo atual

### `PermissionGuard`
- Implementa controle por permissoes.
- Usa semantica AND.
- Nao esta ligado a nenhuma rota atual.
- Nao espera `authReady`.

### `NoAuthGuard`
- Serviria para barrar acesso de usuario autenticado a telas publicas.
- Hoje nao esta ligado a `/login` ou `/registro`.

### `SystemReadyGuard`
- No estado atual, seu criterio de prontidao e apenas `isAuthenticated$`.
- Isso nao representa prontidao real de sistema.

## Estado transversal relacionado a auth
- `AuthService` e a fonte de verdade da sessao em memoria.
- `authReady` controla quando os guards podem decidir sem race condition.
- `isAuthenticated` controla acesso a rotas.
- `user` carrega `roles` e `permissions` vindos do backend.

## Leitura correta do runtime
- O frontend nao mantem uma sessao stateful no servidor.
- O comportamento transversal de autenticacao depende de token local + `/auth/local/me`.
- A protecao de rota aguarda a tentativa de bootstrap antes de redirecionar.
- O redirecionamento global por `401` que existe em outros arquivos nao participa do runtime real.

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
