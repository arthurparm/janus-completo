# Data Models - Frontend (`front`)

## Escopo

O frontend nao possui banco de dados local persistente no repositorio; os modelos sao contratos TypeScript para consumo de API e estado de UI.

## Fontes Principais de Modelo

- `front/src/app/services/janus-api.service.ts`
- `front/src/app/core/types/*`
- `front/src/app/core/state/global-state.store.ts`

## Categorias de Modelos

### Contratos de API

Interfaces para respostas e requests dos dominios:

- `SystemStatus`, `ServiceHealthResponse`, `WorkersStatusResponse`
- `ChatStartRequest/Response`, `ChatMessageRequest/Response`, `ChatHistoryResponse`
- `Goal`, `AutonomyStatusResponse`, `AutonomyPlanResponse`
- `KnowledgeStats`, `DocListResponse`, `DocSearchResponse`

### Modelos de Stream (SSE)

- `StreamStatus`
- `StreamDone`
- `StreamError`
- parcial de tokens via `{ text: string }`

### Estado Global (Signals)

- `loading`, `apiHealthy`, `systemStatus`, `services`, `workers`

## Persistencia no Cliente

- Token e preferencia de modo visitante via chaves locais (`AUTH_TOKEN_KEY`, `VISITOR_MODE_KEY`).
- Sem schema relacional no frontend.

## Observacoes

- Recomenda-se separar contratos por modulo para reduzir o tamanho de `janus-api.service.ts`.
- Contract tests frontend-backend sao importantes para manter estabilidade de tipos.

---

_Gerado pelo workflow BMAD `document-project`_
