## Visão Geral
- Implementar anexos (arquivos/imagens/URLs) no chat, citações no RAG, busca/filtragem avançada e controles de sessão (persona/role/priority) com persistência.
- Alinhar com arquitetura atual: Frontend Angular (front/) e Backend FastAPI (janus/app/), vetorial (Qdrant) e grafo (Neo4j), chat persistido em MySQL.

## Frontend
### Upload de Anexos
- Componente de upload com arrastar/soltar, validações (tamanho/tipos), barra de progresso e preview.
- Local de integração: `src/app/features/chat/chat/chat.html` e `chat.ts`.
- Serviço: adicionar métodos em `src/app/services/janus-api.service.ts` para `uploadAttachment`, `listAttachments`, `deleteAttachment` (multipart, `FormData`).
- Associação: incluir `conversation_id` nos uploads e armazenar estado por conversa; exibir miniaturas/links.
- Headers: propagar `X-Project-Id`, `X-Persona`, `X-Role`, `X-Priority` via util central (ex.: `headersFor` em `src/app/services/api.config.ts`).

### Renderização de Rich Messages
- Componente de mensagem com suporte a Markdown, highlight de código, blocos colapsáveis e botão “copiar código”.
- Citações: painel por mensagem com cards (fonte/título/label, confiança, link), recebendo `citations: { id, title, url, snippet, score }[]` do backend.
- Streaming: se SSE ativo (`FEATURE_SSE`), tratar metadados parciais de citações em `src/app/services/chat-stream.service.ts`; fallback para REST.

### Busca/Filtragem de Conversas
- UI em `src/app/features/chat/conversations/*`: campos de texto, período, filtros por persona/projeto e paginação.
- Integração com `GET /api/v1/chat/conversations` adicionando parâmetros (`q`, `persona`, `project_id`, `start_ts_ms`, `end_ts_ms`, `page`, `pageSize`, `sortKey`, `sortDir`).

### Controles de Sessão
- Dropdown de persona; toggles de role/priority; armazenamento em `localStorage` e inclusão nos headers.
- UI no topo do chat e lista de conversas; persistência por conversa/sessão.

## Backend
### Endpoints de Anexos
- `POST /api/v1/documents/upload`: aceitar `file`, `conversation_id`, `user_id`, `project_id`; sanitização e DLP opcional; limites de tamanho; chunking.
- `GET /api/v1/documents/list?conversation_id&user_id&project_id&page&page_size`.
- `DELETE /api/v1/documents/{doc_id}` com checagens de escopo/consentimento.
- `POST /api/v1/documents/link-url`: anexar URLs (fetch/parse com limites e robots) como documentos.
- Integração: extrair texto, criar embeddings, salvar metadados em Qdrant e relacionar conversa em MySQL.

### RAG com Citações
- Padronizar formato: `{ id, title, url, snippet, score, source_type, doc_id, file_path, origin }`.
- Retornar citações em respostas de chat (REST e SSE). Locais:
  - `janus/app/api/v1/endpoints/chat.py` (enriquecer payload de resposta com `citations`).
  - `janus/app/api/v1/endpoints/rag.py` (garantir campos e normalizar híbrido vetor+grafo).
- Re-ranking e thresholds configuráveis em `janus/app/config.py`.

### Busca com Filtros e Paginação
- Conversas: ampliar `GET /api/v1/chat/conversations` para `q`, período, `persona`, `project_id`, paginação e ordenação (SQL em `janus/app/repositories/chat_repository_sql.py`).
- Documentos: ampliar `GET /api/v1/documents/search` com `conversation_id`, `file_path`, `content_hash`, `status`, `min_score`, janela temporal; índices de payload em `janus/app/db/vector_store.py`.
- RAG: manter `rag.search`, `rag.user_chat(_v2)` com filtros consistentes e normalização de resultados (incluir campo `confidence`/`score`).

## Indexação e Metadados
- Qdrant: estender `payload.metadata` com `{ conversation_id, user_id, project_id, source_type, file_name, content_hash, status, timestamp, confidence }` e criar índices (`create_payload_index`).
- Deduplicação por `content_hash`; estados (`processing/ready/failed`).
- Neo4j: opcionalmente criar arestas `CONVERSATION->DOCUMENT` e atributos para filtros semânticos.

## Segurança e Privacidade
- Lista de tipos permitidos (PDF, DOCX, TXT, PNG/JPEG/GIF, URL); bloquear executáveis; sanitização de HTML.
- Malware scanning opcional e redaction de PII; quotas por usuário/projeto.
- CORS e validação de escopo (`user_id/project_id`) nos endpoints.

## Testes e Aceite
- Carga: testes de upload/indexação com arquivos grandes (chunked), limites e validações.
- Segurança: verificação de tipos e sanitização; testes de DLP/redaction.
- Critérios: citações completas e clicáveis; anexos indexados e buscáveis; controles de persona persistem e afetam contexto (headers).

## Entregáveis
- UI de upload com validações e gerenciamento.
- Painel de citações na resposta (fonte, trecho, confiança, link).
- Busca/filtragem avançada nas conversas e documentos.
- Controles de persona/role/priority no UI e headers.

## Fases de Entrega
1) Backend de anexos (upload/list/delete/link-url) e metadados; Frontend upload básico e previews.
2) Citações no RAG e renderização em rich messages; streaming SSE.
3) Busca/filtragem avançada (conversas/documentos) com paginação e índices; controles de sessão.
4) Testes de carga/segurança, thresholds/re-ranking e ajustes de UX.

## Arquivos‑Chave
- Frontend: `src/app/features/chat/chat/chat.{ts,html,scss}`, `src/app/services/janus-api.service.ts`, `src/app/services/chat-stream.service.ts`, `src/app/services/api.config.ts`, `src/app/features/chat/conversations/*`.
- Backend: `janus/app/api/v1/endpoints/{chat.py, documents.py, rag.py}`, `janus/app/services/{document_service.py, memory_service.py}`, `janus/app/repositories/{chat_repository_sql.py, memory_repository.py, knowledge_repository.py}`, `janus/app/db/{vector_store.py, graph.py}`, `janus/app/config.py`.

Confirme para eu iniciar a implementação seguindo esta ordem e escopo.