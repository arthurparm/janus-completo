---
tipo: dominio
dominio: backend
camada: api
fonte-de-verdade: codigo
status: ativo
---

# API por Bounded Context

## Objetivo
Agrupar a superfície `/api/v1` por contexto funcional.

## Responsabilidades
- Substituir leitura por arquivo por leitura por intenção.
- Ligar grupos de endpoints a serviços e fluxos.

## Entradas
- `backend/app/api/v1/router.py`
- módulos em `backend/app/api/v1/endpoints`

## Saídas
- Mapa de contratos da API.

## Dependências
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Contextos
- Sistema e status:
  - `system_status`, `system_overview`, `workers`
- Identidade e acesso:
  - `auth`, `users`, `profiles`, `consents`, `pending_actions`
- Chat e interação:
  - `chat/chat_message`, `chat/chat_stream`, `chat/chat_history`, `chat/chat_admin`, `chat/chat_study_jobs`
  - recorte operacional principal:
    - `POST /api/v1/chat/start`: abre conversa e retorna só `conversation_id`
    - `POST /api/v1/chat/message`: turno síncrono REST com enriquecimento de `citations`, `understanding`, `confirmation`, `agent_state` e, quando necessário, `study_job`
    - `GET /api/v1/chat/stream/{conversation_id}`: turno SSE com `start/protocol/ack/token|partial/done|error`
    - `GET /api/v1/chat/{conversation_id}/history` e `/history/paginated`: histórico com reconciliação de confirmações já resolvidas
    - `GET /api/v1/chat/{conversation_id}/trace` e `/events`: observabilidade pós-fato e stream de eventos de agente
    - `GET /api/v1/chat/study-jobs/{job_id}`: polling do fallback assíncrono de estudo disparado pelo REST
- Autonomia e coordenação:
  - `autonomy`, `autonomy_admin`, `autonomy_history`, `collaboration`, `tasks`
- Conhecimento e memória:
  - `knowledge`, `rag`, `memory`, `documents`, `learning`, `workspace`
- Execução e ferramentas:
  - `tools`, `sandbox`, `agent`, `assistant`, `context`, `resources`
- Operação e análise:
  - `observability`, `optimization`, `evaluation`, `feedback`, `deployment`, `auto_analysis`, `meta_agent`

## Leitura operacional
- O modo `PUBLIC_API_MINIMAL` reduz a superfície exposta.
- Chat, autonomia e auth são a trilha principal voltada ao uso diário.
- O bounded context de chat cruza dois contratos adjacentes:
  - `pending_actions`: aprovação/rejeição humana quando o chat produz uma pendência estruturada
  - `documents`/`knowledge`: manifests e `knowledge_space_id` podem dominar o pipeline da conversa antes do ramo geral de LLM
- No recorte de tools, a superfície HTTP relevante se divide em:
  - `tools`: catálogo, filtros, estatísticas e criação/remoção dinâmica
  - `sandbox`: execução Python controlada por endpoint dedicado
  - `pending_actions`: aprovação humana para fluxos SQL e LangGraph

## Arquivos-fonte
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/tools.py`
- `backend/app/api/v1/endpoints/sandbox.py`
- `backend/app/api/v1/endpoints/pending_actions.py`
- `backend/app/api/v1/endpoints/chat/*`

## Fluxos relacionados
- [[07 - Glossário e Inventários/Inventário de Endpoints]]
- [[03 - Frontend/Serviços de Integração]]

## Riscos/Lacunas
- A API cresceu por acumulação de sprints, então há contextos administrativos e contextos de produto misturados no mesmo namespace.
