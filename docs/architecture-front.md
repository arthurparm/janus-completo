# Arquitetura - Frontend (`front`)

## Escopo

Aplicacao Angular 20 responsavel por autenticacao, conversa com o assistente, dashboards de status e operacao de ferramentas.

## Stack

- Angular 20 + TypeScript
- RxJS
- Angular Material + TailwindCSS
- Vitest para testes
- Build via Angular CLI (`@angular/build`)

## Estrutura Arquitetural

### 1. Camada de Apresentacao

- `features/`: paginas e fluxos de negocio (`home`, `auth`, `conversations`, `tools`)
- `shared/components/`: biblioteca reutilizavel de UI (badges, toasts, dialogs, tabelas, loading etc.)

### 2. Camada de Aplicacao

- `services/janus-api.service.ts`: cliente REST principal
- `services/chat-stream.service.ts`: stream SSE para tokens/respostas
- `core/state/global-state.store.ts`: estado global com Angular Signals

### 3. Camada de Infra Front

- `core/interceptors/*`: auth, base URL, logging de erro
- `core/guards/*`: controle de acesso
- `environments/*`: variacao por ambiente (incluindo Tailscale)

## Fluxo de Requisicao

1. Usuario interage com componente em `features/*`.
2. Componente dispara chamadas via `JanusApiService`.
3. Interceptors aplicam token/headers e normalizacao de URL.
4. Backend responde via REST (`/api/v1/*`) ou SSE (`/api/v1/chat/stream/{id}`).
5. Estado reativo e UI atualizam por Signals/Subjects.

## Estado e Sessao

- Estado global concentrado em `GlobalStateStore`.
- Estado transiente de stream em `ChatStreamService`.
- Token de auth persistido por chave (`JANUS_AUTH_TOKEN` por padrao).

## Integracoes Externas

- API Janus (REST + SSE)
- Firebase (configurado em environments)
- Tailscale endpoint para acesso remoto

## Riscos e Observacoes

- `environment.ts` contem credenciais e URLs sensiveis; recomenda-se externalizar por variaveis seguras em pipeline.
- `JanusApiService` e extenso; pode ser dividido por dominios (chat, observabilidade, autonomy, tools) para manter evolucao.

## Decisoes Arquiteturais

- SPA componentizada para alta produtividade de UX.
- Cliente API centralizado para padronizar contratos e telemetria.
- SSE para reduzir latencia percebida em respostas de IA.

---

_Gerado pelo workflow BMAD `document-project`_
