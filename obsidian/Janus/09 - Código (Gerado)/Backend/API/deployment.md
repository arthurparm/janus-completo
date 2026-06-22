---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/deployment.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# deployment

## Arquivos-fonte
- `backend/app/api/v1/endpoints/deployment.py`

## Rotas
- `POST /precheck`
- `POST /publish`
- `POST /rollback`
- `POST /stage`

## Símbolos
- function: `_safe_model_file_path(model_id: str, filename: str)` -> `str`
- function: `get_inference_facade(request: Request)`
- class: `StageRequest`
- function: `stage(req: StageRequest, request: Request, inference = Depends(get_inference_facade))`
- function: `publish(model_id: str, request: Request, inference = Depends(get_inference_facade))`
- function: `precheck(model_id: str, request: Request, inference = Depends(get_inference_facade))`
- function: `rollback(model_id: str, request: Request, inference = Depends(get_inference_facade))`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
