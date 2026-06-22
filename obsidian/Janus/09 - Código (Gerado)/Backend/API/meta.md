---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/meta.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# meta

## Arquivos-fonte
- `backend/app/api/v1/endpoints/meta.py`

## Rotas
- `GET /status`
- `POST /run-analysis`

## Símbolos
- class: `MetaAgentStatusResponse`
  - Resposta com o status atual do Meta-Agente.
- function: `get_status()`
  - Retorna o status operacional do Meta-Agente, incluindo se seu ciclo
de 'heartbeat' está ativo e o conteúdo do seu último relatório de estado.
- function: `run_analysis_cycle()`
  - Solicita que o Meta-Agente execute um ciclo de análise do sistema sob demanda.
Esta é uma operação assíncrona. A resposta imediata contém o relatório
gerado pelo ciclo de análise recém-concluído.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
