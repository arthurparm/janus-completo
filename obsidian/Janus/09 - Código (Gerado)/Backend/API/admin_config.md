---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/admin_config.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# admin_config

## Arquivos-fonte
- `backend/app/api/v1/endpoints/admin_config.py`

## Rotas
- `PATCH /admin/config`

## Dependências de código
- Serviços
  - `config_service`

## Símbolos
- class: `ConfigUpdateRequest`
  - Modelo flexível para atualização de configuração.
- class: `ConfigUpdateResponse`
- function: `update_config(request: ConfigUpdateRequest, service: ConfigService = Depends(get_config_service))`
  - Recebe atualizações de configuração e as propaga via Redis Pub/Sub 
para todas as instâncias do serviço.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
