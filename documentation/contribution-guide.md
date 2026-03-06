# Contribution Guide

## Fluxo Recomendado

1. Criar branch de feature/fix.
2. Implementar alteracoes com foco em baixo acoplamento.
3. Rodar lint/test/build localmente.
4. Abrir PR usando o template de risco e evidencia em `.github/pull_request_template.md`.

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
- `.github/pull_request_template.md`
- `documentation/index.md`

---

_Gerado pelo workflow BMAD `document-project`_
