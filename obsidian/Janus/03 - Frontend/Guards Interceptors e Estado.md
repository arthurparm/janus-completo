---
tipo: dominio
dominio: frontend
camada: infraestrutura
fonte-de-verdade: codigo
status: ativo
---

# Guards Interceptors e Estado

## Objetivo
Explicar os mecanismos transversais do frontend.

## Responsabilidades
- Cobrir auth state.
- Cobrir guards e interceptors.
- Apontar shared UI/state relevantes.

## Entradas
- `core/auth`
- `core/guards`
- `core/interceptors`
- `core/state`

## Saídas
- Mapa de comportamento transversal da UI.

## Dependências
- [[03 - Frontend/Shell e Navegação]]
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[03 - Frontend/Auth Sessão Guards e Roles]]

## Componentes
- `AuthService`: inicializa sessao a partir do token local e resolve `/auth/local/me`.
- `AuthGuard`, `RoleGuard`, `PermissionGuard`, `NoAuthGuard`, `SystemReadyGuard`.
- Interceptors:
  - `auth.interceptor`
  - `base-url.interceptor`
  - `error-logger.interceptor`
  - `error-mapping.interceptor`
  - `http.interceptor` existe no codigo, mas nao esta registrado no `provideHttpClient()` atual
- Estado global:
  - `global-state.store`
  - serviços de loading e notifications

## Leitura real de auth transversal
- A cadeia HTTP ativa do app e `baseUrlInterceptor -> authInterceptor -> errorLoggerInterceptor -> errorMappingInterceptor`.
- `auth.interceptor` e a unica peca ativa que adiciona credenciais automaticamente nas requests.
- `http.interceptor.ts` contem classes de loading, timeout, retry e `401`, mas esse arquivo nao participa da configuracao atual do Angular.
- `AuthGuard` e `RoleGuard` esperam `authReady`, entao a decisao de rota aguarda a tentativa de restauracao via `/auth/local/me`.
- `PermissionGuard` nao espera `authReady`; se passar a ser usado, seu comportamento inicial precisa ser revisado.
- O estado de admin no frontend depende de `user.roles` e do computed `isAdmin` do `AuthService`.

## Arquivos-fonte
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/*.ts`
- `frontend/src/app/core/state/global-state.store.ts`

## Fluxos relacionados
- [[03 - Frontend/Auth Sessão Guards e Roles]]
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Riscos/Lacunas
- Parte dos guards parece preparada para cenarios mais amplos do que as rotas atuais.
- Existe codigo de interceptor HTTP para `401` que nao e executado no runtime atual, o que pode induzir leitura errada do fluxo de sessao.
