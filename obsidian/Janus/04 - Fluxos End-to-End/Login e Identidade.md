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
- [[02 - Backend/Segurança e Infra]]

## Sequência
1. Usuário acessa `/login`.
2. `AuthService.loginWithPassword()` chama `/api/v1/auth/local/login`.
3. Token é salvo em storage.
4. `AuthService` passa a expor `isAuthenticated` e `user`.
5. `AuthGuard` libera rotas privadas.
6. `RoleGuard` restringe `/admin/autonomia`.

## Arquivos-fonte
- `frontend/src/app/core/auth/auth.service.ts`
- `frontend/src/app/core/guards/auth.guard.ts`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/core/infrastructure/auth.py`

## Fluxos relacionados
- [[03 - Frontend/Shell e Navegação]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Riscos/Lacunas
- Existem caminhos de troca com Supabase/Firebase além do login local.
- A política real de admin depende de role e também de allowlist/consentimento por CPF em partes do backend.
