---
tipo: fluxo
dominio: autonomia
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Autonomia

## Objetivo
Explicar o ciclo de metas, plano e execução autônoma.

## Responsabilidades
- Cobrir controle de loop.
- Cobrir CRUD de goals e execução assíncrona.

## Entradas
- Configuração de risco.
- Plano de passos.
- Metas criadas pelo usuário.

## Saídas
- Loop ativo/inativo.
- Metas atualizadas.
- Workers processando ações.

## Dependências
- [[02 - Backend/Autonomia e Workers]]
- [[03 - Frontend/Features e Experiência]]

## Sequência
1. Usuário entra em `admin/autonomia` ou no rail de autonomia em `conversations`.
2. Frontend chama `/api/v1/autonomy/status`, `/start`, `/stop`, `/plan`, `/policy`.
3. Backend valida steps contra `action_registry`, allowlist, blocklist e schema.
4. `AutonomyService` controla ciclo e lock de execução.
5. Scheduler e workers processam o plano e tarefas derivadas.

## Arquivos-fonte
- `frontend/src/app/features/admin/autonomia/admin-autonomia.ts`
- `frontend/src/app/features/conversations/conversations.ts`
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/core/autonomy/goal_manager.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]

## Riscos/Lacunas
- A experiência de autonomia está espalhada entre admin e cockpit de conversa.
- O comportamento final depende de políticas de risco e disponibilidade de ferramentas.
