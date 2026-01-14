# Janus — Organização do Projeto (Atualizado)

Este documento descreve a estrutura, nomenclatura e convenções adotadas, alinhadas ao estado atual do repositório. Para a visão consolidada, veja o [README.md](../README.md) principal.

## Visão Geral

```
/ (raiz)
├─ README.md
├─ docker-compose.yml
├─ front/                         # Aplicação Angular (UI)
├─ janus/                         # Backend (FastAPI, serviços, workers, core)
│  ├─ app/                        # Código da aplicação
│  │  ├─ api/                     # Endpoints REST (/api/v1)
│  │  ├─ core/                    # LLM, memória, infra, tools, workers
│  │  ├─ db/                      # Conectores (Neo4j/Qdrant/MySQL)
│  │  ├─ services/                # Orquestração e regras de negócio
│  │  ├─ models/                  # Modelos Pydantic/ORM
│  │  ├─ repositories/            # Persistência e integrações
│  │  ├─ config.py                # Configurações (Pydantic Settings)
│  │  └─ main.py                  # FastAPI app / lifecycle
│  ├─ tests/                      # Testes (unit/integration/e2e)
│  ├─ docker/                     # Dockerfiles (base e Ollama)
│  ├─ grafana/                    # Dashboards prontos
│  ├─ observability/              # Compose e configs (otel/promtail)
│  ├─ http/                       # Coleções de requisições (.http)
│  └─ pyproject.toml              # Dependências e ferramentas (Poetry/uv)
├─ docs/                          # Documentação Markdown (manual e guias)
│  ├─ Janus-Manual.md
│  ├─ Project-Structure.md
│  ├─ qdrant_resilience_improvements.md
│  └─ guides/
│     └─ tailscale-security-comparison.md
├─ docker/                       # Imagens Docker base
│  ├─ Dockerfile
│  └─ ollama.Dockerfile
├─ scripts/                      # Utilitários e automações
│  └─ init-ollama.sh
├─ http/                         # Coleções de requisições para teste manual
├─ grafana/                      # Dashboards e provisionamento
└─ prometheus/                   # Configuração do Prometheus
```

## Princípios de Organização

- Separação por domínio e responsabilidade:
  - `front/` contém exclusivamente o código de interface (Angular).
  - `janus/` concentra o backend e serviços core.
  - `docs/` serve de fonte única de verdade para documentação.
  - `docker/` guarda Dockerfiles; `docker-compose.yml` permanece na raiz para orquestração.
  - `scripts/` mantém utilitários independentes do app (instalação, setup, manutenção).
- Nomenclatura consistente e explícita:
  - Prefira nomes descritivos (`documentacao`, `arquitetura`, `dashboard`) ao invés de abreviações obscuras.
  - Use minúsculas e hífens/underscores de acordo com o ecossistema (Angular vs Python).
- Caminhos estáveis para CI/CD:
  - Evite mover arquivos sem ajustes correspondentes no `docker-compose.yml` e pipelines.
- Documentação próxima do código:
  - Manual consolidado em `docs/Janus-Manual.md`.
  - Referencie `docs/` na UI (página Documentação em `front/src/app/pages/documentacao`).

## Estrutura Interna do Backend (`/janus`)

- `app/` — Código da aplicação:
  - `api/` (routers) em `janus/app/api/v1/endpoints/*`
  - `core/` (LLM, memória, resiliência, workers)
  - `services/` (orquestração e lógica de domínio)
  - `models/`, `repositories/`, `db/`
- `tests/` — testes unitários e de integração
- `pyproject.toml` — dependências e metadados

## Estrutura Interna do Frontend (`/front`)

- `src/app/pages/` — páginas (Documentação, Arquitetura, Sprints)
- `src/app/features/` — features (chat, knowledge, operations, overview)

- `src/app/services/` — consumo das APIs do Janus
- `proxy.conf.json` — mapeamento de rotas do backend durante o desenvolvimento

## Convenções de Nomenclatura

- Angular:
  - Componentes: `PascalCase` para classes (ex.: `ChatComponent`), kebab-case para paths.
  - Pastas por feature/página com `html/scss/ts` co-localizados.
- Python:
  - Módulos e pacotes em `snake_case`.
  - Classes em `PascalCase`.

## Boas Práticas Complementares

- Servir documentação (`/docs`) via backend ou web server no deploy.
- Utilizar coleções `http/` para validação rápida de endpoints (ex.: `janus/http/E2E-Production-Scenario.http`).
- Adotar versionamento semântico e changelogs em `docs/Release-Notes-*`.

## Próximas Melhorias Sugeridas

- Consolidar `grafana/` e `prometheus/` sob `infra/observability/` (se preferir) e ajustar `docker-compose.yml`.
- Documentar rotas estáticas no backend para servir `docs/` e `http/`.
- Adicionar arquivos de configuração a `/config` (ex.: `config/app.example.yaml`).

---

Dúvidas ou sugestões: veja `README.md` e abra uma issue descrevendo a proposta de melhoria de organização.
