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

## Componentes
- `AuthService`: inicializa sessão a partir do token local e resolve `/auth/local/me`.
- `AuthGuard`, `RoleGuard`, `PermissionGuard`, `NoAuthGuard`, `SystemReadyGuard`.
- Interceptors:
  - `auth.interceptor`
  - `base-url.interceptor`
  - `error-logger.interceptor`
  - `error-mapping.interceptor`
  - `http.interceptor`
- Estado global:
  - `global-state.store`
  - serviços de loading e notifications

## Arquivos-fonte
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `frontend/src/app/core/interceptors/*.ts`
- `frontend/src/app/core/state/global-state.store.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Riscos/Lacunas
- Parte dos guards parece preparada para cenários mais amplos do que as rotas atuais.
