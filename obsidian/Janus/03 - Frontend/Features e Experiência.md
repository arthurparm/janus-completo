---
tipo: dominio
dominio: frontend
camada: features
fonte-de-verdade: codigo
status: ativo
---

# Features e Experiência

## Objetivo
Registrar o papel de cada feature Angular na experiência do produto.

## Responsabilidades
- Separar jornada por tela.
- Ligar features às capacidades backend.

## Entradas
- `frontend/src/app/features/*`

## Saídas
- Mapa funcional do frontend.

## Dependências
- [[03 - Frontend/Shell e Navegação]]
- [[03 - Frontend/Serviços de Integração]]
- [[03 - Frontend/Observability Frontend]]

## Features
- `home`: landing autenticada com atalhos e widgets.
- `conversations`: centro operacional do produto; concentra chat, docs, memória, RAG, autonomia e feedback.
- `observability`: dashboard protegido por `AuthGuard` com operator view (workers + 4 filas fixas) e tres widgets (`system status`, `database validation`, `knowledge health`).
- `tools`: gerenciamento/exploração de ferramentas.
- `auth/login` e `auth/register`: entrada e criação de sessão.
- `admin/autonomia`: controle administrativo de autonomia.

## Leitura operacional
- `conversations` é a feature mais densa e funciona quase como cockpit.
- `home` é um lançador de intenções e histórico recente.
- `observability` usa `BackendApiService` diretamente, sem facade dedicada.
- `observability` tem polling proprio em todos os blocos a cada 5s, mas o toggle da tela pausa apenas o painel do operador.
- O nome da feature sugere profundidade de observabilidade maior do que a UI realmente entrega; a maior parte da superficie de `api/v1/observability/*` nao aparece aqui.

## Arquivos-fonte
- `frontend/src/app/features/home/home.ts`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/features/observability/observability.ts`
- `frontend/src/app/features/tools/tools.ts`
- `frontend/src/app/features/admin/autonomia/admin-autonomia.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[03 - Frontend/Observability Frontend]]

## Riscos/Lacunas
- A feature de conversas agrega muitos subfluxos e concentra complexidade de UX e integração.
- A feature de observability expoe so um subconjunto curto do estado operacional real do backend.
