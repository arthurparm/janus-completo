# Contribution Guide

## Fluxo Recomendado

1. Criar branch de feature/fix.
2. Implementar alteracoes com foco em baixo acoplamento.
3. Rodar lint/test/build localmente.
4. Abrir PR com descricao objetiva e impactos.

## Convencao de Commits

Usar Conventional Commits:

- `feat(scope): ...`
- `fix(scope): ...`
- `refactor(scope): ...`
- `test(scope): ...`
- `docs(scope): ...`

## Checklist Minimo

- Frontend
  - `cd frontend && npm run lint`
  - `cd frontend && npm run test`
  - `cd frontend && npm run build`
- Backend
  - `cd backend && pytest`

## Convencoes Tecnicas

- Front: manter logica de negocio fora de componentes quando possivel.
- Backend: preservar separacao endpoint -> service -> repository.
- Evitar introduzir configuracoes sensiveis hardcoded.

## Referencias Internas

- `frontend/CONTRIBUTING.md`
- `frontend/README.md`
- `documentation/index.md`

---

_Gerado pelo workflow BMAD `document-project`_
