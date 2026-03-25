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

## Arquivos-fonte
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/tools.py`
- `backend/app/api/v1/endpoints/chat/*`

## Fluxos relacionados
- [[07 - Glossário e Inventários/Inventário de Endpoints]]
- [[03 - Frontend/Serviços de Integração]]

## Riscos/Lacunas
- A API cresceu por acumulação de sprints, então há contextos administrativos e contextos de produto misturados no mesmo namespace.
