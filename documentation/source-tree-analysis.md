# Janus Completo - Analise da Arvore de Codigo

**Data:** 2026-02-11

## Visao Geral

Repositorio monorepo com duas partes funcionais (`frontend`, `backend`) e camadas de suporte (`tooling`, `qa`, `_bmad`, `documentation`). O fluxo principal e: UI Angular -> API FastAPI -> servicos/workers -> armazenamento (Postgres/Redis/Neo4j/Qdrant).

## Estrutura Principal

```text
janus-completo/
|- frontend/                          # Frontend Angular 20
|  |- src/
|  |  |- app/
|  |  |  |- core/                 # auth, guards, interceptors, estado global
|  |  |  |- features/             # home, auth, conversations, tools
|  |  |  |- services/             # cliente API, stream SSE, auto-analysis
|  |  |  |- shared/               # componentes reutilizaveis
|  |  |- environments/            # environment.ts / environment.prod.ts
|  |- package.json
|  |- angular.json
|  |- docker/Dockerfile
|- backend/                          # Backend FastAPI e motor de agentes
|  |- app/
|  |  |- api/v1/endpoints/        # 39 modulos de endpoint, 229 operacoes HTTP
|  |  |- services/                # regras de negocio e orchestracao
|  |  |- repositories/            # persistencia e acesso a dados
|  |  |- core/                    # workers, llm, memory, infra, tools
|  |  |- models/                  # SQLAlchemy + Pydantic models
|  |  |- db/                      # configuracao Postgres/Neo4j/Qdrant
|  |  |- main.py                  # entrypoint FastAPI
|  |- docker/Dockerfile
|  |- pyproject.toml
|  |- qa/
|- docker-compose.pc1.yml          # stack oficial PC1 (api + dados leves)
|- docker-compose.pc2.yml          # stack oficial PC2 (neo4j/qdrant/ollama)
|- tooling/                        # automacao operacional no host
|- qa/                          # testes de integracao e validacoes extras
|- _bmad/                          # workflows BMAD instalados no projeto
|- documentation/                           # documentacao gerada neste workflow
```

## Diretorios Criticos

### `frontend/src/app/services`

Camada de comunicacao com backend. Destaques:

- `backend-api.service.ts` centraliza chamadas REST para `/api/v1/*`.
- `chat-stream.service.ts` implementa SSE com retry e backoff.
- `api.config.ts` controla base URL e flags de comportamento.

### `frontend/src/app/core`

Infra da SPA:

- interceptors (auth/base-url/erros)
- guards de rota
- store global via Angular Signals (`global-state.store.ts`)

### `backend/app/api/v1/endpoints`

Superficie de API do backend (autonomia, chat, memoria, llm, observabilidade, ferramentas, auth, etc.).

### `backend/app/services`

Implementa logica de negocio. Conecta endpoints a infraestrutura (LLMs, memoria, broker, tools, observabilidade).

### `backend/app/core/workers`

Workers assinc e orchestrador para ciclos autonomos, consolidacao de conhecimento, reflexion, red-team e agentes especializados.

### `backend/app/models`

Schema de dados para SQLAlchemy/Pydantic e contratos internos.

## Entry Points

- **Frontend:** `frontend/src/main.ts`
- **Backend:** `backend/app/main.py`
- **Infra local:** `docker-compose.pc1.yml` + `docker-compose.pc2.yml`

## Padroes de Organizacao

- Front separa `core`, `features`, `shared`, `services`.
- Backend separa `api`, `services`, `repositories`, `core`, `models`.
- Suporte operacional isolado em `tooling/` e `backend/docker/`.

## Arquivos de Configuracao Relevantes

- `docker-compose.pc1.yml`, `docker-compose.pc2.yml`
- `frontend/angular.json`, `frontend/package.json`, `frontend/proxy*.json`
- `backend/pyproject.toml`, `backend/requirements.txt`
- `backend/app/config.py`
- `backend/prometheus/prometheus.yml` e `backend/grafana/provisioning/*`

---

_Gerado pelo workflow BMAD `document-project`_
