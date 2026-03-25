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
1. `AuthService` executa `initializeAuth()` no construtor.
2. O startup sempre comeca com `authReady = false`.
3. `firebaseAuthReady` vai para `true` imediatamente. Hoje isso nao depende de handshake real com Firebase Auth.
4. `getStoredAuthToken()` procura primeiro em `localStorage` e depois em `sessionStorage`.
5. Se houver token, o frontend chama `GET ${API_BASE_URL}/v1/auth/local/me`.
6. Com `API_BASE_URL = /api`, a chamada efetiva fica em `/api/v1/auth/local/me`.
7. Se a resposta vier com usuario, o service popula `user`, marca `isAuthenticated = true` e conclui com `authReady = true`.
8. Se a resposta falhar, `clearSession()` apaga o token dos dois storages, remove `VISITOR_MODE_KEY`, zera `user` e sobe a aplicacao como anonima.
9. Se nao houver token salvo, nenhuma chamada a `/local/me` e feita.

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
- Le o token salvo por `getStoredAuthToken()`.
- Se a request ainda nao tiver `Authorization`, injeta `Authorization: Bearer <token>`.
- Se a request ainda nao tiver `X-User-Id`, tenta decodificar o token e enviar esse header tambem.
- `decodeTokenUserId()` le a primeira parte do token, o que faz sentido porque o token interno Janus e `payload.signature`, nao JWT padrao.
- O interceptor nao exige autenticacao: requests anonimas continuam funcionando sem falhar no cliente.

### Interceptors existentes fora da cadeia atual
- `frontend/src/app/core/interceptors/http.interceptor.ts` contem classes para loading, timeout, retry e tratamento de `401`.
- Esse arquivo nao esta registrado em `provideHttpClient()`.
- Logo, qualquer comportamento de redirecionamento em `401` definido nele nao faz parte do runtime real.

## Fluxo de login no frontend
1. A tela `/login` coleta `email`, `password` e `remember`.
2. O form exige email valido e password preenchida.
3. `LoginComponent.loginEmailPassword()` bloqueia reentradas via `loading`.
4. A tela aplica lock local de 60 segundos depois de 5 falhas consecutivas.
5. `AuthService.loginWithPassword()` envia `POST /api/v1/auth/local/login` com `email` e `password`.
6. Se a API devolver `token`, o frontend persiste o token, remove `VISITOR_MODE_KEY`, seta `isAuthenticated = true` e grava `out.user`.
7. Depois do sucesso, a tela espera 100 ms e navega sempre para `/`.

## Tratamento de erro no login
- `401`: vira `reason = invalid_credentials` e orientacao para revisar credenciais ou recuperar acesso.
- `422`: vira `reason = invalid_request` com mensagens diferentes para senha curta, email invalido ou payload invalido.
- `429`: vira `reason = rate_limited`.
- Outros casos: `reason = unknown`.

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
- Espera `authReady$` ficar `true`.
- Usa `combineLatest([authReady$, isAuthenticated$])`.
- Se autenticado, libera a rota.
- Se nao autenticado, redireciona para `/login` com `returnUrl` e dispara notificacao de acesso negado.

### `RoleGuard`
- Tambem espera `authReady$`.
- Le `route.data['roles']`.
- Usa semantica OR: basta uma role requerida estar em `user.roles`.
- Sem usuario carregado, redireciona para `/login`.
- Sem role suficiente, mostra erro e redireciona para `/`.

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
