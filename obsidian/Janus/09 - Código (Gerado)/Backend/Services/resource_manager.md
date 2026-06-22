---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/resource_manager.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# resource_manager

## Arquivos-fonte
- `backend/app/services/resource_manager.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/resources.py`
- `backend/app/repositories/learning_repository.py`

## Símbolos
- function: `can_schedule_training(user_id: str | None)` -> `bool`
- function: `record_training_usage(user_id: str | None, cost: float)` -> `None`
- function: `get_user_gpu_usage(user_id: str)` -> `dict[str, Any]`
- function: `compute_job_priority(user_id: str | None, model_type: str | None)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
