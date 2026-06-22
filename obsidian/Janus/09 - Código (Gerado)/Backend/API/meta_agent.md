---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/meta_agent.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# meta_agent

## Arquivos-fonte
- `backend/app/api/v1/endpoints/meta_agent.py`

## Rotas
- `GET /health`
- `GET /heartbeat/status`
- `GET /report/latest`
- `POST /analyze`
- `POST /heartbeat/start`
- `POST /heartbeat/stop`

## Dependências de código
- Serviços
  - `meta_agent_service`

## Símbolos
- class: `StartHeartbeatRequest`
- function: `run_analysis(service: MetaAgentService = Depends(get_meta_agent_service))`
  - Delega a execução do ciclo de análise para o MetaAgentService.
- function: `get_latest_report(service: MetaAgentService = Depends(get_meta_agent_service))`
  - Delega a busca do último relatório para o MetaAgentService.
- function: `start_heartbeat(request: StartHeartbeatRequest, service: MetaAgentService = Depends(get_meta_agent_service))`
  - Delega o início do heartbeat para o MetaAgentService.
- function: `stop_heartbeat(service: MetaAgentService = Depends(get_meta_agent_service))`
  - Delega a parada do heartbeat para o MetaAgentService.
- function: `get_heartbeat_status(service: MetaAgentService = Depends(get_meta_agent_service))`
  - Delega a busca do status do heartbeat para o MetaAgentService.
- function: `health_check(service: MetaAgentService = Depends(get_meta_agent_service))`
  - Delega a verificação de saúde do meta-agente para o MetaAgentService.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
