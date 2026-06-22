---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/data_governance_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# data_governance_service

## Arquivos-fonte
- `backend/app/services/data_governance_service.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/governance.py`

## Símbolos
- class: `DataGovernanceServiceError`
- class: `DataGovernanceService`
- method: `DataGovernanceService.__init__(self, repo: DataGovernanceRepository | None = None)`
- method: `DataGovernanceService._compute_retention_until(retention_days: int | None)` -> `datetime | None`
- method: `DataGovernanceService.register_auto(self, *, user_id: int | None, resource_type: str, resource_id: str, sample_text: str | None, metadata: dict[str, Any] | None = None)` -> `int`
- method: `DataGovernanceService.register_manual(self, *, user_id: int | None, resource_type: str, resource_id: str, classification: str, retention_policy: str, retention_days: int | None, metadata: dict[str, Any] | None = None)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
