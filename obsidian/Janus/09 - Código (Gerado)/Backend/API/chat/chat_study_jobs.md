---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/chat/chat_study_jobs.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat/chat_study_jobs

## Arquivos-fonte
- `backend/app/api/v1/endpoints/chat/chat_study_jobs.py`

## Rotas
- `GET /study-jobs/{job_id}`

## Dependências de código
- Serviços
  - `chat_service`

## Símbolos
- function: `get_study_job(job_id: str, service: ChatService = Depends(get_chat_service), http: Request = None)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
