# Janus Completo - Analise da Arvore de Codigo

**Data:** 2026-02-11

## Visao Geral

Repositorio monorepo com duas partes funcionais (`front`, `janus`) e camadas de suporte (`scripts`, `tests`, `_bmad`, `docs`). O fluxo principal e: UI Angular -> API FastAPI -> servicos/workers -> armazenamento (Postgres/Redis/Neo4j/Qdrant).

## Estrutura Principal

```text
janus-completo/
|- front/                          # Frontend Angular 20
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
|- janus/                          # Backend FastAPI e motor de agentes
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
|  |- tests/
|- docker-compose.yml              # stack local completa
|- scripts/                        # automacao operacional no host
|- tests/                          # testes de integracao e validacoes extras
|- _bmad/                          # workflows BMAD instalados no projeto
|- docs/                           # documentacao gerada neste workflow
```

## Diretorios Criticos

### `front/src/app/services`

Camada de comunicacao com backend. Destaques:

- `janus-api.service.ts` centraliza chamadas REST para `/api/v1/*`.
- `chat-stream.service.ts` implementa SSE com retry e backoff.
- `api.config.ts` controla base URL e flags de comportamento.

### `front/src/app/core`

Infra da SPA:

- interceptors (auth/base-url/erros)
- guards de rota
- store global via Angular Signals (`global-state.store.ts`)

### `janus/app/api/v1/endpoints`

Superficie de API do backend (autonomia, chat, memoria, llm, observabilidade, ferramentas, auth, etc.).

### `janus/app/services`

Implementa logica de negocio. Conecta endpoints a infraestrutura (LLMs, memoria, broker, tools, observabilidade).

### `janus/app/core/workers`

Workers assinc e orchestrador para ciclos autonomos, consolidacao de conhecimento, reflexion, red-team e agentes especializados.

### `janus/app/models`

Schema de dados para SQLAlchemy/Pydantic e contratos internos.

## Entry Points

- **Frontend:** `front/src/main.ts`
- **Backend:** `janus/app/main.py`
- **Infra local:** `docker-compose.yml`

## Padroes de Organizacao

- Front separa `core`, `features`, `shared`, `services`.
- Backend separa `api`, `services`, `repositories`, `core`, `models`.
- Suporte operacional isolado em `scripts/` e `janus/docker/`.

## Arquivos de Configuracao Relevantes

- `docker-compose.yml`
- `front/angular.json`, `front/package.json`, `front/proxy*.json`
- `janus/pyproject.toml`, `janus/requirements.txt`
- `janus/app/config.py`
- `janus/prometheus/prometheus.yml` e `janus/grafana/provisioning/*`

---

_Gerado pelo workflow BMAD `document-project`_
