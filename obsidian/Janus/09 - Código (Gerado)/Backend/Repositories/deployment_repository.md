---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/deployment_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# deployment_repository

## Arquivos-fonte
- `backend/app/repositories/deployment_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/planes/inference/facade.py`

## Símbolos
- class: `ModelDeployment`
- class: `DeploymentRepository`
- method: `DeploymentRepository.__init__(self, session: Session | None = None)`
- method: `DeploymentRepository._get_session(self)` -> `Session`
- method: `DeploymentRepository.stage(self, model_id: str, percent: int)` -> `dict[str, Any]`
- method: `DeploymentRepository.publish(self, model_id: str)` -> `dict[str, Any]`
- method: `DeploymentRepository.rollback(self, model_id: str)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
