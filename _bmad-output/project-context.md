---
project_name: 'janus-completo'
user_name: 'Arthur'
date: '2026-02-11'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
existing_patterns_found: 14
status: 'complete'
rule_count: 40
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- Frontend runtime: Angular `^20.0.0`, RxJS `~7.8.0`, TypeScript `~5.9.2`.
- Frontend tooling: Vitest `^3.1.1`, ESLint `^8.57.0`, TailwindCSS `^3.4.0`, Prettier (config em `package.json`).
- Backend runtime: Python `>=3.11,<3.13`, FastAPI, Uvicorn, SQLAlchemy `>=2.0.0`.
- Backend AI stack: LangChain (core/community/openai/google/ollama/groq), Neo4j GraphRAG, pydantic-ai.
- Data/infra: PostgreSQL (+pgvector), Redis, RabbitMQ, Neo4j `>=5.19.0`, Qdrant `>=1.9.2`.
- Quality gates backend: Ruff + Ruff Format, Black (`line-length=100`), MyPy strict, pre-commit hooks.

## Critical Implementation Rules

### Language-Specific Rules

- TypeScript: sempre manter compatibilidade com `strict: true` e `strictTemplates: true`; nao introduzir `any` sem justificativa explicita.
- TypeScript: respeitar `noImplicitOverride`, `noImplicitReturns` e `noFallthroughCasesInSwitch`; corrigir causas, nao desabilitar flags.
- TypeScript: preservar imports com caminhos estaveis por feature/core/shared; evitar ciclos entre `features` e `core`.
- Python: manter tipagem consistente com MyPy strict; novas funcoes publicas devem ter tipos completos de entrada/retorno.
- Python: seguir padrao de formatacao e lint existente (Ruff + Black line-length 100); nao misturar estilos conflitantes.
- Python/FastAPI: manter separacao `endpoints -> services -> repositories`; evitar logica de negocio pesada direto em endpoint.

### Framework-Specific Rules

- Angular: manter componentes enxutos; mover orquestracao de API/estado para services e stores (`services/*`, `core/state/*`).
- Angular: preservar estrutura por responsabilidade (`core`, `features`, `shared`); novos artefatos devem seguir a pasta correta.
- Angular: para chamadas HTTP, preferir centralizacao no `JanusApiService`/servicos de dominio; evitar duplicacao de clientes.
- Angular + SSE: seguir padrao do `ChatStreamService` (eventos `partial/token/done/error`, retry com backoff); nao criar streams paralelos sem teardown explicito.
- FastAPI: novos endpoints devem entrar em `app/api/v1/endpoints/*` com roteador agregado em `app/api/v1/router.py`.
- FastAPI: em fluxo de request, manter contratos Pydantic e delegar regra de negocio para service layer; endpoint deve focar em validacao, autorizacao e resposta.
- Worker-based backend: tarefas longas/assincronas devem usar workers/broker existentes em vez de bloquear request sincrono.

### Testing Rules

- Frontend: novos fluxos em `features` e servicos criticos devem incluir ou atualizar `*.spec.ts` proximos ao codigo alterado.
- Frontend: para mudancas de UX/streaming, validar comportamento com testes que cubram estados (`loading`, `error`, `done`) e nao apenas caminho feliz.
- Frontend: manter compatibilidade com runner atual (`vitest.config.ts`); nao introduzir framework de teste paralelo sem necessidade.
- Backend: manter padrao `test_*.py` em `janus/tests` (unit/integration/e2e) conforme escopo da mudanca.
- Backend: mudancas em endpoint devem ter teste de contrato basico (status code, payload minimo e cenario de erro principal).
- Backend: mudancas em servicos/workers devem validar efeitos colaterais (fila, persistencia, eventos) com mocks/fakes controlados.
- Sempre evitar reduzir cobertura funcional existente sem justificativa explicita no PR.

### Code Quality & Style Rules

- Frontend: seguir ESLint do projeto (`front/.eslintrc.json`); warnings recorrentes devem ser tratados no codigo, nao ignorados em massa.
- Frontend: aplicar Prettier com padrao local (`printWidth 100`, `singleQuote true`, parser Angular para HTML).
- Frontend: manter organizacao por dominio e reuso em `shared`; evitar duplicar componentes utilitarios ja existentes.
- Backend: seguir `ruff` + `ruff-format` + `black` (`line-length=100`) conforme `.pre-commit-config.yaml`.
- Backend: manter imports ordenados e sem codigo morto; evitar funcoes muito longas quando podem ser quebradas em helpers claros.
- Tipagem e contratos: toda mudanca de payload deve refletir em schemas/interfaces correspondentes (Pydantic e TypeScript).
- Logging: preservar logs uteis para troubleshooting sem expor segredos/tokens.

### Development Workflow Rules

- Commits e PRs devem seguir Conventional Commits (padrao ja exigido no front e no fluxo BMAD).
- Antes de abrir PR, rodar checks minimos do front: `npm run lint`, `npm run test`, `npm run build`.
- Antes de abrir PR, rodar checks minimos do back: `pytest` + hooks de pre-commit aplicaveis.
- Mudancas de configuracao que impactam runtime (env, compose, provider de LLM, filas) devem atualizar documentacao tecnica correspondente em `docs/` quando aplicavel.
- Ao alterar contratos de API, sincronizar backend e frontend na mesma entrega para evitar quebra em `/api/v1/*`.
- Em mudancas de arquitetura/fluxo critico, registrar decisao de forma rastreavel (documento/PR description) para manter contexto de agentes futuros.

### Critical Don't-Miss Rules

- Nao quebrar a separacao de camadas: endpoint nao deve concentrar regra de negocio nem acesso direto a multiplas fontes sem service.
- Nao alterar contratos de `/api/v1/*` sem refletir imediatamente no frontend (interfaces e chamadas do `JanusApiService`).
- Nao introduzir bypass silencioso de auth/consent/audit em endpoints sensiveis; qualquer excecao deve ser explicita e rastreavel.
- Nao adicionar logs com segredos (tokens/chaves/credenciais) nem dados sensiveis brutos.
- Nao bloquear request HTTP com trabalho pesado quando existe padrao de worker/fila para execucao assincrona.
- Nao ignorar strict/type checks para "fazer passar"; corrigir a causa raiz.
- Nao duplicar componentes/servicos existentes em `shared`/`core`; preferir extensao ou composicao.
- Em SSE/chat, sempre garantir encerramento de stream e tratamento de erro/retry para evitar conexoes zumbis.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code in this repository.
- Follow all rules exactly as documented; prefer restrictive/safe choices when uncertain.
- Keep endpoint/service/repository boundaries and existing contracts intact.
- Update this file when introducing non-obvious new patterns.

**For Humans:**

- Keep this file lean and focused on non-obvious rules agents can miss.
- Update it whenever stack versions, architecture, or workflow gates change.
- Review periodically to remove obsolete rules and keep high signal.

Last Updated: 2026-02-11
