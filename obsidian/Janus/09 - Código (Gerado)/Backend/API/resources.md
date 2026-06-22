---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/resources.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# resources

## Arquivos-fonte
- `backend/app/api/v1/endpoints/resources.py`

## Rotas
- `GET /gpu/usage/`
- `POST /gpu/budget`

## Dependências de código
- Serviços
  - `resource_manager`

## Símbolos
- function: `gpu_usage(request: Request, user_id: str = Query(..., min_length=1))`
  - Consulta uso de GPU por usuário.
- class: `BudgetSetRequest`
- function: `set_gpu_budget(req: BudgetSetRequest, request: Request)`
  - Define orçamento de GPU por usuário (admin-only).

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
