---
tipo: dominio
dominio: frontend
camada: autenticacao
fonte-de-verdade: codigo
status: ativo
---

# Auth Sessão Guards e Roles

## Objetivo
Registrar o comportamento real de autenticacao e autorizacao do frontend Angular.

## Escopo de leitura
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/core/interceptors/base-url.interceptor.ts`
- `frontend/src/app/app.config.ts`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/features/auth/login/login.ts`
- `frontend/src/app/features/auth/register/register.ts`
- `frontend/src/app/services/auth.utils.ts`

## Sessao: inicializacao real
- `AuthService` executa `initializeAuth()` no construtor.
- O startup da auth sempre comeca com `authReady = false`.
- `firebaseAuthReady` e marcado como `true` imediatamente, sem handshake real com Firebase Auth. No estado atual ele funciona como flag de compatibilidade, nao como prova de sessao Firebase.
- O token e lido por `getStoredAuthToken()`, que busca primeiro `localStorage` e depois `sessionStorage`.
- A chave padrao do token e `JANUS_AUTH_TOKEN`, vinda de `VITE_AUTH_TOKEN_KEY` com fallback em `frontend/src/app/services/api.config.ts`.
- Quando existe token, o frontend chama `GET ${API_BASE_URL}/v1/auth/local/me`.
- Com a configuracao padrao (`API_BASE_URL = /api`) e o `baseUrlInterceptor` ativo, essa chamada efetiva fica em `/api/v1/auth/local/me`.
- Se `/auth/local/me` responder com sucesso, `AuthService` marca `isAuthenticated = true` e popula `user` com o payload retornado.
- Se `/auth/local/me` falhar por qualquer motivo, `clearSession()` apaga o token dos dois storages, remove `JANUS_VISITOR_MODE` do `localStorage`, zera `user` e mantem a sessao como nao autenticada.
- Se nao houver token, a sessao sobe como anonima e `authReady` vai para `true` sem chamada de perfil.

## Persistencia do token
- `storeAuthToken(token, remember)` usa `localStorage` quando `remember = true`.
- Quando `remember = false`, o token vai para `sessionStorage`.
- O login respeita o checkbox `remember`.
- O cadastro nao respeita escolha do usuario: `registerLocal()` sempre salva com `remember = true`.
- `logout()` so limpa estado local; nao existe chamada de revogacao ou encerramento de sessao no backend.
- `clearSession()` limpa tambem `VISITOR_MODE_KEY`, entao qualquer modo visitante local e abandonado apos login, logout ou falha de restauracao.

## /auth/local/me no fluxo real
- `/auth/local/me` e o unico passo de restauracao de sessao na abertura da aplicacao.
- O login e o cadastro nao fazem re-fetch desse endpoint depois da autenticacao; o frontend passa a confiar no `user` retornado diretamente por `/auth/local/login` ou `/auth/local/register`.
- A protecao de rotas depende do estado produzido por esse bootstrap inicial ou pelas mutacoes de login/cadastro.

## Interceptors que impactam auth
- O `provideHttpClient()` ativo registra apenas `baseUrlInterceptor`, `authInterceptor`, `errorLoggerInterceptor` e `errorMappingInterceptor`.
- O `authInterceptor` anexa `Authorization: Bearer <token>` quando a request ainda nao possui esse header.
- O mesmo interceptor tenta adicionar `X-User-Id` a partir de `decodeTokenUserId(token)`.
- `decodeTokenUserId()` e `decodeTokenExp()` leem `parts[0]` do token, nao `parts[1]`. Se o token for um JWT convencional `header.payload.signature`, a leitura do payload tende a falhar e `X-User-Id` nao sera enviado.
- Os interceptors em classe de `frontend/src/app/core/interceptors/http.interceptor.ts` nao entram na cadeia HTTP atual. Logo, o redirecionamento global em `401` definido ali nao faz parte do fluxo efetivo.
- `errorMappingInterceptor` trata indisponibilidade/offline, mas nao restaura nem encerra sessao.

## Login local
- `LoginComponent` chama `AuthService.loginWithPassword(email, password, remember)`.
- O service envia `POST ${API_BASE_URL}/v1/auth/local/login` com `email` e `password`.
- Se a resposta trouxer `token`, o frontend persiste o token, remove `VISITOR_MODE_KEY`, marca a sessao autenticada e armazena `out.user`.
- Depois do sucesso, a tela espera 100 ms e navega sempre para `/`.
- O componente nao consome `returnUrl` da query string. O guard gera esse parametro, mas o login nao o usa na navegacao de retorno.
- `loginWithProvider('google' | 'github')` existe, mas retorna `false` com log de aviso. Os botoes de Google e GitHub nao autenticam no modo atual.
- O componente aplica um lock client-side de 60 segundos depois de 5 falhas consecutivas na mesma instancia da tela.
- O tratamento de erro do login diferencia `401`, `422` e `429`, com mensagens especificas mapeadas no `AuthService`.

## Recuperacao de senha
- `recoverAccess()` chama `POST ${API_BASE_URL}/v1/auth/local/request-reset`.
- Se a API devolver `reset_token`, a tela exibe esse token ao usuario no bloco de aviso.
- `submitResetPassword()` chama `POST ${API_BASE_URL}/v1/auth/local/reset`.
- O frontend exige minimo de 8 caracteres no reset de senha.

## Cadastro local
- `RegisterComponent` chama `AuthService.registerLocal(...)`.
- O service envia `POST ${API_BASE_URL}/v1/auth/local/register`.
- Em sucesso, o frontend salva token com persistencia longa, marca a sessao como autenticada e popula `user`.
- A tela de cadastro nao redireciona automaticamente apos sucesso. Ela exibe mensagem de sucesso e faz `form.reset(...)`, mesmo com a sessao ja autenticada.

## Guards e redirecionamento
- `AuthGuard` espera `authReady$` ficar `true` antes de decidir. Isso evita bloquear a rota antes de a restauracao da sessao terminar.
- Se a sessao estiver autenticada, `AuthGuard` libera a navegacao.
- Se nao estiver autenticada, `AuthGuard` redireciona para `/login` com `queryParams: { returnUrl }` e mostra aviso de acesso negado.
- O `returnUrl` vem de `state.url` quando disponivel; fallback usa `route.url?.join('/')` e depois `/`.
- `RoleGuard` tambem espera `authReady$`. Sem usuario, ele navega para `/login`.
- Quando ha usuario, `RoleGuard` usa semantica OR: basta uma role requerida bater em `user.roles`.
- Se faltar role, o guard mostra erro e manda o usuario para `/`.
- `PermissionGuard` usa semantica AND: todas as permissoes declaradas na rota precisam existir em `user.permissions`.
- `PermissionGuard` nao espera `authReady$`; se for aplicado em uma rota no startup, ele pode decidir antes da restauracao da sessao terminar.
- `NoAuthGuard` existe para impedir acesso de usuario autenticado a telas publicas, mas nao esta ligado a `/login` nem a `/registro`.
- `SystemReadyGuard` existe, mas o check atual apenas espelha `isAuthenticated$`, o que nao caracteriza prontidao de sistema.

## Rotas protegidas hoje
- `''`, `conversations`, `conversations/:conversationId`, `tools` e `observability` usam `AuthGuard`.
- `admin/autonomia` usa `AuthGuard` e `RoleGuard` com `data.roles = ['admin']`.
- `login` e `registro` sao publicas.
- `**` redireciona para `login`.

## Roles no frontend
- `AuthService.isAdmin` deriva exclusivamente de `user.roles?.includes('admin')`.
- Elementos de UI e a rota `admin/autonomia` dependem dessa role do payload de usuario.
- Nao existe no frontend um refresh dedicado de roles separado da sessao; roles mudam quando `user` muda.

## Limitacoes e comportamentos visiveis
- O frontend depende do token estar valido no storage para restaurar sessao; nao existe refresh token nem renovacao automatica visivel neste escopo.
- O retorno pos-login ignora `returnUrl`, entao o usuario sempre cai na home autenticada.
- Login social esta exposto na UI, mas desativado na implementacao real.
- Cadastro autentica automaticamente, mas nao reposiciona a navegacao para uma area privada.
- Os guards `PermissionGuard`, `NoAuthGuard` e `SystemReadyGuard` parecem preparados para cenarios maiores do que o roteamento atual realmente usa.

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

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[03 - Frontend/Guards Interceptors e Estado]]
