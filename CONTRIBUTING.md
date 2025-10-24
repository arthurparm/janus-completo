# Contribuindo para o Janus

Obrigado por contribuir! Este guia define convenções, ferramentas e o fluxo de trabalho para manter o projeto organizado, consistente e saudável.

## Pré-requisitos
- Python `3.11` e `pip`
- Node.js `>=18` para o frontend Angular
- Docker/Compose (opcional, para ambiente de serviços)
- Variáveis `.env` configuradas (veja `docs/Configuration.md`)

## Setup de Desenvolvimento
- Backend (Python):
  - Crie o ambiente: `py -3.11 -m venv .venv && .venv\\Scripts\\activate`
  - Instale deps: `pip install -r Janus/requirements.txt`
  - (Opcional) Instale ferramentas de dev: `pip install ruff black pytest pre-commit`
  - Ative hooks: `pre-commit install`
- Frontend (Angular):
  - Instale deps: `npm install` dentro de `front/`
  - Rodar dev: `npm start`

## Convenções de Commits (Conventional Commits)
Use mensagens de commit descritivas seguindo o padrão:
```
<tipo>(escopo opcional): descrição curta

[corpo opcional]
[rodapé opcional]
```
Tipos comuns: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, `revert`.
Exemplos:
- `feat(api): adicionar endpoint /api/v1/tools`
- `fix(memory): corrigir cache nulo em Qdrant`
- `docs(readme): alinhar doc/ para docs/`

### Branches
- `feature/<slug>` para novas funcionalidades
- `fix/<slug>` para correções
- `chore/<slug>` para manutenção

### Pull Requests
Inclua na descrição:
- Motivação, escopo e impacto
- Screenshots (se aplicável)
- Checklist:
  - [ ] Passa em linters e formatação
  - [ ] Testes executam localmente (`pytest`) quando aplicável
  - [ ] Mantém compatibilidade com `docker-compose`
  - [ ] Atualiza documentação quando necessário

## Padrões de Código e Ferramentas
- Python:
  - Lint: `ruff` — `ruff check Janus/app`
  - Formatação: `black` — `black Janus/app`
  - Hooks: `pre-commit` (ver `.pre-commit-config.yaml`)
- Angular:
  - Lint: `eslint` — `npm run lint`
  - Formatação: `prettier` (config em `package.json`)

## Estrutura de Pastas
- Código fonte:
  - Backend: `Janus/app/...`
  - Frontend: `front/src/...`
- Documentação: `docs/`
- Configuração: `config/` (`.env.example`, Prometheus/Grafana/Compose)
- Testes: `Janus/tests/`
- Recursos estáticos (dashboards, assets): `grafana/`, `front/public/`

## Dicas
- Mantenha mudanças pequenas e focadas
- Evite refatorações amplas sem necessidade
- Use logs e métricas quando relevante
- Respeite validações em `app/config.py`

Obrigado por manter o projeto saudável e bem organizado!