# Development Guide - Frontend (`frontend`)

## Pre-requisitos

- Node.js 20
- npm
- Angular CLI (`npm i -g @angular/cli`)

## Setup Local

```bash
cd frontend
npm install
npm start
```

Servidor dev padrao: `http://localhost:4200`

## Scripts Principais

- `npm start` - sobe app com proxy `proxy.conf.json`
- `npm run start:tailscale` - sobe com proxy tailscale
- `npm run build` - build de producao
- `npm run test` - executa vitest
- `npm run e2e` - executa a suite Playwright
- `npm run e2e:chat-runtime` - valida sessao autenticada, UI, stream, persistencia e metadados reais do chat
- `npm run e2e:chat-sse` - executa o smoke Playwright focado em SSE do chat
- `npm run lint` - lint em `src`
- `npm run format` - prettier em `src/**/*.{ts,html,scss}`

## Ambiente e Config

- `src/environments/environment.ts`
- `src/environments/environment.prod.ts`
- `src/app/services/api.config.ts` (base API e flags)

## Testes

- Unit/spec files em `src/**/*.spec.ts`
- Runner principal: Vitest
- E2E/browser/API runtime em `e2e/**/*.spec.ts`

### Smoke real do chat SSE

O smoke autenticado `e2e/auth-session-runtime.smoke.spec.ts` registra uma conta sintetica, restaura a sessao apos reload, abre as telas principais, envia uma mensagem pela UI, exige stream HTTP 200, resposta persistida, `provider`/`model`, `delivery_status=completed` e ausencia de erros inesperados de API/console:

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_CHAT_RUNTIME_E2E_MAX_MS='60000'
npm run e2e:chat-runtime
```

O frontend Docker local pode ser acessado por `localhost:4300` ou `127.0.0.1:4300`; ambos devem constar em `CORS_ALLOW_ORIGINS`. Os smokes usam diretorios separados em `test-results/chat-runtime` e `test-results/chat-sse` para preservar as duas evidencias quando executados em sequencia.

O smoke `e2e/chat-sse-runtime.smoke.spec.ts` valida o caminho real do streaming:

- registra usuario sintetico pela API;
- inicia conversa;
- chama `/api/v1/chat/stream/{conversation_id}`;
- exige eventos SSE `token` e `done`;
- falha se houver `event: error`;
- confirma `provider`, `model` e `citation_status=not_applicable` para `Ola`.

Execucao contra o frontend Docker/local ja exposto:

```bash
cd frontend
E2E_BASE_URL=http://localhost:4300 JANUS_RUN_REAL_CHAT_E2E=true npm run e2e:chat-sse
```

No PowerShell:

```powershell
cd frontend
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
npm run e2e:chat-sse
```

O limite da chamada SSE pode ser ajustado com `JANUS_LIGHT_CHAT_E2E_MAX_MS`. O timeout total do teste adiciona margem operacional de 15s sobre esse valor para cobrir preflight, registro de usuario, criacao de conversa e escrita do artefato.

Pre-requisitos: `janus-frontend`, `janus-api`, Ollama e dependencias PC2 saudaveis. Sem `JANUS_RUN_REAL_CHAT_E2E=true`, o teste e registrado mas pulado para nao quebrar ambientes sem runtime completo.

## Boas Praticas

- Evitar logica de negocio pesada em componentes.
- Centralizar chamadas HTTP em servicos.
- Preferir Signals/RxJS para estado observavel.

---

_Gerado pelo workflow BMAD `document-project`_
