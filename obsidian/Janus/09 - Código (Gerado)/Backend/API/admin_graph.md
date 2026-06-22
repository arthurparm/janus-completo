---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/admin_graph.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# admin_graph

## Arquivos-fonte
- `backend/app/api/v1/endpoints/admin_graph.py`

## Rotas
- `GET /contextual`
- `POST /purge_incompatible`

## Dependências de código
- Serviços
  - `knowledge_graph_service`

## Símbolos
- class: `CleanupResult`
- function: `_purge_incompatible_threads_task()`
  - Background task to find and delete threads incompatible with current schema version.
In a real implementation, this would deserialize blobs.
Here we implement a simplified SQL logic assuming we can check metadata or just purge everything for safety if flag is set.
- function: `purge_incompatible_threads(force: bool = False, background_tasks: BackgroundTasks = None)`
  - Purges threads that are incompatible with the current graph schema version.
This is critical after deployments that change the state structure.
- function: `get_contextual_graph(query: str | None = None, conversation_id: str | None = None, limit: int = 50, hops: int = 1)`
  - Retorna um subgrafo otimizado para visualização no frontend.
Pode usar uma 'query' (busca por similaridade ou exata de nós)
ou 'conversation_id' (busca contexto relevante da conversa).

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
