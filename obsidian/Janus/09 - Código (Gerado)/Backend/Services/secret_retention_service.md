---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/secret_retention_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# secret_retention_service

## Arquivos-fonte
- `backend/app/services/secret_retention_service.py`

## Dependências de código
- Repositórios
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/services/scheduler_service.py`

## Símbolos
- class: `SecretRetentionService`
- method: `SecretRetentionService.purge_expired_batch(self, *, limit: int = 200, active_only: bool = True)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
