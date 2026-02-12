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
  - `cd front && npm run lint`
  - `cd front && npm run test`
  - `cd front && npm run build`
- Backend
  - `cd janus && pytest`

## Convencoes Tecnicas

- Front: manter logica de negocio fora de componentes quando possivel.
- Backend: preservar separacao endpoint -> service -> repository.
- Evitar introduzir configuracoes sensiveis hardcoded.

## Referencias Internas

- `front/CONTRIBUTING.md`
- `front/README.md`
- `docs/index.md`

---

_Gerado pelo workflow BMAD `document-project`_
