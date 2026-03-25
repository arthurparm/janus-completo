---
tipo: dominio
dominio: frontend
camada: shell
fonte-de-verdade: codigo
status: ativo
---

# Shell e Navegação

## Objetivo
Descrever a casca Angular que organiza a experiência do operador.

## Responsabilidades
- Mapear rotas reais.
- Identificar áreas protegidas por auth.

## Entradas
- `app.routes.ts`
- `core/layout/*`
- `AuthGuard` e `RoleGuard`

## Saídas
- Mapa de navegação do frontend.

## Dependências
- [[03 - Frontend/Features e Experiência]]
- [[03 - Frontend/Guards Interceptors e Estado]]
- [[04 - Fluxos End-to-End/Login e Identidade]]

## Rotas
- `/login`
- `/conversations`
- `/conversations/:conversationId`
- `/tools`
- `/observability`
- `/admin/autonomia`
- `/` e `/home`
- `/registro`

## Leitura operacional
- Quase toda a aplicação é protegida por `AuthGuard`.
- Área administrativa depende também de `RoleGuard`.
- O shell visual é composto por header/sidebar e componentes compartilhados.

## Arquivos-fonte
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/core/layout/header/header.ts`
- `frontend/src/app/core/layout/sidebar/sidebar.ts`
- `frontend/src/app/core/guards/auth.guard.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[04 - Fluxos End-to-End/Autonomia]]

## Riscos/Lacunas
- O frontend atual é orientado ao operador; não há sinais de múltiplas experiências altamente separadas.
