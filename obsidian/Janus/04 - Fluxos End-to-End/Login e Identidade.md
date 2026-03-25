---
tipo: fluxo
dominio: identidade
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Login e Identidade

## Objetivo
Registrar como sessão e identidade percorrem frontend e backend.

## Responsabilidades
- Cobrir login local e sessão persistida.
- Relacionar auth com roles e guards.

## Entradas
- Credenciais do usuário.
- Token armazenado localmente.

## Saídas
- Sessão autenticada na UI.
- JWT válido para API.

## Dependências
- [[03 - Frontend/Guards Interceptors e Estado]]
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[02 - Backend/Segurança e Infra]]

## Bootstrap da sessao
1. O app instancia `AuthService` e chama `initializeAuth()`.
2. O service marca `authReady = false` e procura `JANUS_AUTH_TOKEN` em `localStorage` e depois em `sessionStorage`.
3. Se houver token, `GET /api/v1/auth/local/me` e disparado.
4. O `authInterceptor` anexa `Authorization: Bearer <token>` na chamada de perfil.
5. Se `/auth/local/me` responder com usuario, a sessao sobe autenticada.
6. Se `/auth/local/me` falhar, o frontend apaga o token local e conclui o bootstrap como anonimo.
7. `authReady = true` libera os guards que esperam essa flag.

## Fluxo de login local
1. Usuario envia email e senha em `/login`.
2. `LoginComponent` chama `AuthService.loginWithPassword(...)`.
3. O service envia `POST /api/v1/auth/local/login`.
4. Se a resposta trouxer token, o frontend salva o token em `localStorage` ou `sessionStorage` conforme `remember`.
5. O service remove `JANUS_VISITOR_MODE`, marca `isAuthenticated = true` e salva `user` com o payload da resposta.
6. A tela espera 100 ms e navega sempre para `/`.

## Fluxo de cadastro local
1. Usuario envia dados em `/registro`.
2. `RegisterComponent` chama `AuthService.registerLocal(...)`.
3. O service envia `POST /api/v1/auth/local/register`.
4. Em sucesso, o frontend salva token com persistencia longa, marca sessao autenticada e guarda `user`.
5. A tela nao navega; apenas mostra sucesso e limpa o formulario.

## Protecao de rotas
- `AuthGuard` protege home, conversations, tools e observability.
- `RoleGuard` protege `admin/autonomia` e exige a role `admin`.
- Quando `AuthGuard` bloqueia acesso, ele redireciona para `/login?returnUrl=<rota-original>`.
- O login bem-sucedido nao usa `returnUrl`; o retorno vai sempre para `/`.
- `RoleGuard` manda usuario sem sessao para `/login`.
- `RoleGuard` manda usuario autenticado sem a role exigida para `/`, com notificacao de acesso negado.

## Roles e permissoes no frontend
- O frontend considera admin apenas quando `user.roles` contem `admin`.
- `PermissionGuard` existe e usa comparacao por `every()`, mas nao aparece em nenhuma rota atual.
- Nao ha refresh especifico de roles; elas mudam apenas quando o objeto `user` e trocado.

## Observacoes relevantes do codigo
- Os botoes de Google e GitHub aparecem na UI, mas `loginWithProvider()` retorna `false`.
- O frontend nao exibe uso real de refresh token nem renovacao automatica de sessao.
- O endpoint `/auth/local/me` e o passo central de restauracao da sessao entre reloads.
- O `NoAuthGuard` existe, mas nao esta ligado a `/login` nem `/registro`.

## Arquivos-fonte
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/auth.interceptor.ts`
- `frontend/src/app/features/auth/login/login.ts`
- `frontend/src/app/features/auth/register/register.ts`

## Fluxos relacionados
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[03 - Frontend/Shell e Navegação]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Riscos/Lacunas
- O `returnUrl` gerado pelo guard nao e consumido pelo login.
- A UI exibe login social, mas a implementacao local nao autentica por provider.
- O cadastro autentica, mas nao redireciona para area privada.
