# Janus 1.0 — Organização do Projeto

Este documento descreve a estrutura, nomenclatura e convenções adotadas, alinhadas ao estado atual do repositório. Para a visão consolidada, veja `docs/Janus-Manual.md`.

## Visão Geral

```
/ (raiz)
├─ README.md
├─ docker-compose.yml
├─ front/                        # Aplicação Angular (UI)
├─ Janus/                        # Backend (Python/FastAPI, workers, serviços)
│  ├─ app/
│  ├─ sql/
│  ├─ tests/
│  ├─ requirements.txt
│  └─ pyproject.toml
├─ docs/                         # Documentação em Markdown
│  ├─ Architecture.md
│  ├─ Usage.md
│  ├─ Configuration.md
│  ├─ Troubleshooting.md
│  └─ Release-Notes-1.0.0.md
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
  - `Janus/` concentra o backend e serviços core.
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

## Estrutura Interna do Backend (`/Janus`)

- `app/` — Código da aplicação:
  - `api/` (routers) em `janus/app/api/v1/endpoints/*`
  - `core/` (LLM, memória, resiliência, workers)
  - `services/` (orquestração e lógica de domínio)
  - `models/`, `repositories/`, `db/`
- `sql/` — scripts e migrações
- `tests/` — testes unitários e de integração
- `requirements.txt`, `pyproject.toml` — dependências e metadados

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
