# Story 1.1: Set up initial project from starter template

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a engenheiro de plataforma,  
I want inicializar o monorepo com Nx incremental sobre a base atual e preparar o modulo inicial de tenant,  
so that o time tenha fundacao tecnica e escopo multi-tenant prontos para evoluir com seguranca.

## Acceptance Criteria

1. Inicializacao incremental Nx sem rebootstrap dos apps existentes.
2. CI valida build/test/lint por projetos afetados.
3. Modulo base de tenant no backend com `tenant_id` explicito no contexto de requisicao.
4. Evidencia de execucao e auditoria do setup inicial registrada.

### BDD (fonte canonica)

Scenario 1:
- **Given** o repositorio atual com frontend e backend existentes
- **When** a inicializacao incremental do Nx e executada e validada em CI
- **Then** o workspace fica configurado sem rebootstrap dos apps existentes
- **And** comandos de build/test/lint podem ser executados por projetos afetados

Scenario 2:
- **Given** a fundacao inicial criada
- **When** o modulo base de tenant e provisionado no backend
- **Then** a aplicacao passa a operar com contexto explicito de `tenant_id`
- **And** o setup inicial fica registrado com evidencia de execucao e auditoria

## Tasks / Subtasks

- [ ] T1 - Baseline tecnico e seguranca de mudanca (AC: 1, 2)
  - [ ] Mapear estado atual do repo (root sem `package.json`/`nx.json`, apps `front` e `janus` ja existentes).
  - [ ] Definir estrategia incremental Nx sem mover diretios de app existentes.
  - [ ] Criar plano de rollback simples (remocao dos arquivos Nx adicionados) antes da alteracao.

- [ ] T2 - Inicializar Nx incremental no root (AC: 1)
  - [ ] Executar `npx nx@latest init` no root com configuracao minima.
  - [ ] Manter `front/` e `janus/` intactos (sem rebootstrap).
  - [ ] Criar/alinhar arquivos de workspace Nx (`nx.json`, `package.json` root e configuracoes relacionadas).

- [ ] T3 - Registrar projetos e targets do workspace (AC: 1, 2)
  - [ ] Declarar `front` e `janus` como projetos Nx com targets de `build`, `test`, `lint`.
  - [ ] Garantir comandos afetados operacionais (`nx affected -t build,test,lint`).
  - [ ] Incluir wrappers npm na raiz para execucao padrao de CI.

- [ ] T4 - Fortalecer pipeline CI com gate por impacto (AC: 2)
  - [ ] Adicionar workflow de CI para PR/push com `lint`, `test`, `build` por projetos afetados.
  - [ ] Preservar deploy existente (`action-locaweb.yml`) sem regressao.
  - [ ] Publicar resumo de jobs e status no log de CI.

- [ ] T5 - Provisionar modulo base de tenant no backend (AC: 3)
  - [ ] Criar modulo base para contexto de tenant em `janus/app/core/infrastructure/` (ex.: resolver de `tenant_id` por header/contexto).
  - [ ] Integrar `tenant_id` ao ciclo de request (middleware/context vars), sem quebrar auth atual.
  - [ ] Expor contrato minimo de uso para endpoints/services subsequentes.

- [ ] T6 - Observabilidade e auditoria do setup (AC: 4)
  - [ ] Registrar evento tecnico de bootstrap (run/setup id, timestamp, actor, escopo).
  - [ ] Garantir que logs de setup referenciem correlacao (request/setup id) e tenant quando aplicavel.
  - [ ] Documentar evidencias de execucao no artefato da story.

- [ ] T7 - Validacao final e documentacao de handoff (AC: 1, 2, 3, 4)
  - [ ] Validar comandos locais e em CI.
  - [ ] Atualizar notas de arquitetura/operacao com decisoes de Nx + tenant foundation.
  - [ ] Registrar riscos remanescentes e proximos passos para Story 1.2.

## Dev Notes

- FRs vinculados: `FR1`, `FR2`, `FR3`, `FR4`, `FR5`, `FR6`.
- NFRs de suporte para esta story: `NFR9`, `NFR13`, `NFR21`, `NFR22`, `NFR23`.
- Escopo desta story e de fundacao tecnica. Nao implementar RBAC completo nem fluxos OAuth finais aqui.

### Technical Requirements

- Nx deve ser adotado de forma incremental, sem recriar apps existentes.
- `front` continua Angular 20 + Vitest; `janus` continua FastAPI/Python 3.11 + pytest.
- `tenant_id` deve existir no contexto de request para permitir enforcement nas stories seguintes.
- CI deve bloquear regressao basica (lint/test/build) com foco em tarefas afetadas.

### Architecture Compliance

- Respeitar fronteiras arquiteturais: backend em fluxo `endpoint -> service -> repository`.
- Reusar infraestrutura existente de correlacao (`correlation_middleware`) para propagar contexto.
- Evitar acoplamento de tenant somente em LLM usage tracking; criar base transversal de request context.
- Preservar padrao de observabilidade com correlacao por actor/acao/fluxo.

### Library / Framework Requirements

- Frontend: Angular `^20.0.0`, Vitest (`front/package.json`).
- Backend: FastAPI e Python `>=3.11,<3.13` (`janus/pyproject.toml`).
- Nx: inicializacao com `npx nx@latest init`; fixar versoes no root apos bootstrap para reproducibilidade.
- CI Node: manter Node 20 no pipeline front e alinhar com execucao Nx no root.

### File Structure Requirements

- Nao mover diretorios existentes `front/` e `janus/`.
- Artefatos esperados no root apos bootstrap Nx:
  - `nx.json`
  - `package.json` (workspace)
  - possiveis configs auxiliares Nx/TS conforme init
- Modulo de tenant inicial no backend sob `janus/app/core/infrastructure/` com API interna clara.

### Testing Requirements

- Validar localmente:
  - `nx affected -t lint`
  - `nx affected -t test`
  - `nx affected -t build`
- Validar fallback de execucao completa quando necessario:
  - front: `npm run lint && npm run test && npm run build` em `front/`
  - back: `pytest` em `janus/`
- Cobrir ao menos:
  - teste unitario do resolvedor/contexto de `tenant_id`
  - teste de middleware/context propagation basico
  - teste de pipeline CI executando targets Nx sem rebootstrap

### UX and Product Alignment

- Mesmo sendo story de fundacao, nao quebrar o fluxo UX definido:
  - base web responsiva com foco desktop
  - suporte a estados claros e rastreabilidade
  - aderencia futura a fluxos criticos WCAG 2.1 AA
- Referenciar `ux-design-specification.md` como insumo para nao divergir contratos de experiencia.

### Project Structure Notes

- Repositorio e monorepo multi-part (`front` + `janus`) sem workspace manager no root atualmente.
- CI atual (`.github/workflows/action-locaweb.yml`) esta orientado a build/deploy do front; ampliar com CI de qualidade sem remover deploy.
- Ja existe correlacao de request em backend (`correlation_middleware.py`), que pode ser estendida para `tenant_id`.

### References

- `_bmad-output/planning-artifacts/epics/epic-1-tenant-identidade-e-controle-de-acesso.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `.github/workflows/action-locaweb.yml`
- `front/package.json`
- `front/angular.json`
- `janus/pyproject.toml`
- `janus/app/core/infrastructure/correlation_middleware.py`
- `janus/app/core/infrastructure/auth.py`
- `docs/project-overview.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/.create-story-discovery-1-1.json`
- `_bmad-output/implementation-artifacts/.create-story-context-1-1.json`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- UX content existente localizado e incorporado via `ux-design-specification.md`.
- Story preparada para `dev-story` com foco em fundacao Nx + tenant context.

### File List

- `_bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-starter-template.md`
