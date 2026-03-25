---
tipo: inventario
dominio: api
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Endpoints

## Objetivo
Listar os módulos de endpoint existentes para navegação rápida.

## Responsabilidades
- Servir de índice técnico da superfície API.

## Entradas
- `backend/app/api/v1/endpoints`

## Saídas
- Índice navegável de endpoints.

## Dependências
- [[02 - Backend/API por Bounded Context]]

## Módulos
- `admin_config`
- `admin_graph`
- `agent`
- `assistant`
- `auth`
- `auto_analysis`
- `autonomy`
- `autonomy_admin`
- `autonomy_history`
- `chat/chat_admin`
- `chat/chat_history`
- `chat/chat_message`
- `chat/chat_stream`
- `chat/chat_study_jobs`
- `collaboration`
- `consents`
- `context`
- `deployment`
- `documents`
- `evaluation`
- `feedback`
- `knowledge`
- `learning`
- `llm`
- `memory`
- `meta`
- `meta_agent`
- `observability`
- `optimization`
- `pending_actions`
- `productivity`
- `profiles`
- `rag`
- `reflexion`
- `resources`
- `sandbox`
- `system_overview`
- `system_status`
- `tasks`
- `tools`
- `users`
- `workers`
- `workspace`

## Arquivos-fonte
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/endpoints/**/*.py`

## Fluxos relacionados
- [[00 - Índice/Mapa por Domínio]]
- [[03 - Frontend/Serviços de Integração]]

## Riscos/Lacunas
- Este inventário lista presença de módulos, não a exaustão de cada rota individual.
