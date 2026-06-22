---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/ab_testing_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# ab_testing_service

## Arquivos-fonte
- `backend/app/services/ab_testing_service.py`

## Dependências de código
- Repositórios
  - `ab_experiment_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/evaluation.py`

## Símbolos
- class: `ABTestingService`
- method: `ABTestingService.__init__(self, repo: ABExperimentRepository | None = None)`
- method: `ABTestingService.compute_winner(self, experiment_id: int, metric_name: str = 'accuracy')` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
