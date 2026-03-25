---
tipo: fluxo
dominio: conhecimento
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Documentos Conhecimento e Memória

## Objetivo
Explicar o caminho comprovado em código entre upload de documento, indexação vetorial, uso no chat e eventual consolidação.

## Responsabilidades
- Descrever ingestão e indexação de documentos.
- Separar uso documental no chat de consolidação semântica.
- Registrar onde documentos encostam em memória e onde não encostam.

## Entradas
- Arquivo enviado pelo usuário.
- `user_id`, `conversation_id`, `knowledge_space_id` e metadados de origem.
- Perguntas do chat que pedem contexto documental.

## Saídas
- `DocumentManifest` atualizado com progresso e resumo semântico.
- Chunks `doc_chunk` em `user_docs_<user_id>`.
- Citações documentais no chat.
- Resumo leve de anexos da conversa para `RAGService.retrieve_context()`.

## Dependências
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[01 - Visão do Sistema/Dependências Externas]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Sequência real
### 1. Stage do upload
1. `DocumentIngestionService.stage_upload()` cria `doc_id`, resolve caminho em disco e cria o manifesto.
2. O arquivo é escrito em `DOC_UPLOAD_STORAGE_DIR`.
3. O manifesto nasce em `queued`.
4. O serviço publica `document_ingestion` via outbox ou `publish_document_ingestion_task()`.

### 2. Processamento do arquivo
1. `document_ingestion_worker.process_document_ingestion_task()` chama `DocumentIngestionService.process_staged_document(doc_id=...)`.
2. O serviço lê o arquivo staged e executa `_ingest_payload(...)`.
3. `DocumentParserService.parse()` extrai texto.
4. `DocumentSemanticEnrichmentService.enrich()` calcula `doc_type`, `entities`, `summary` e `confidence`.
5. O texto é quebrado em chunks com `_chunk_text(...)`.

### 3. Indexação no Qdrant
1. O destino é `user_docs_<user_id>`, criado por `build_user_docs_collection_name()` e `aget_or_create_collection()`.
2. Cada chunk recebe embedding via `aembed_texts(...)`.
3. Cada ponto é gravado com `type=doc_chunk` e metadados como:
   - `doc_id`
   - `file_name`
   - `knowledge_space_id`
   - `source_type`
   - `source_id`
   - `doc_role`
   - `edition_or_version`
   - `language`
   - `parent_collection_id`
   - `conversation_id`
   - `semantic_doc_type`
   - `semantic_entities`
   - `semantic_summary`
   - `semantic_confidence`
   - `content_hash`
4. Antes do upsert, `_delete_doc_points()` remove chunks antigos do mesmo `doc_id`.
5. Ao final, o manifesto é marcado como `completed` com `chunks_total`, `chunks_indexed` e resumo semântico.

## Como documentos entram no chat
### Citações
- `chat_citation_service.collect_document_citations()` consulta `user_docs_<user_id>` por embedding da pergunta.
- Se não houver hits e a pergunta mencionar material enviado, `_recent_document_citations()` faz `scroll` recente na mesma coleção.
- As citações vêm exclusivamente de `doc_chunk` em Qdrant no fluxo lido aqui.

### Contexto de prompt
- `RAGService.retrieve_context()` não injeta chunks completos.
- Se a mensagem mencionar arquivo/anexo/documento, `_conversation_document_context()` faz `scroll` em `user_docs_<user_id>` filtrando:
  - `metadata.type = doc_chunk`
  - `metadata.user_id = <user>`
  - `metadata.conversation_id = <conversa>`
- O resultado é um bloco textual curto com nome do arquivo e `semantic_summary` ou preview do chunk.

## Relação com memória
- `user_docs_<user_id>` não é a mesma coleção de memória episódica.
- `doc_chunk` não passa por `MemoryCore.amemorize()`.
- A recuperação documental do chat é separada do recall de `user_chat_<user_id>` e `user_memory_<user_id>`.
- `collect_chat_citations()` pode combinar documentos e memórias, mas são pipelines distintos.

## Relação com conhecimento/Neo4j
### O que o código comprova
- A ingestão documental mostrada aqui termina em Qdrant + manifesto.
- `process_document_ingestion_task()` pode tentar auto-consolidação:
  - `KnowledgeSpaceService.consolidate_space(...)` quando existe `knowledge_space_id`
  - `KnowledgeService.consolidate_document(...)` quando não existe

### O que o código não comprova neste estado
- O código lido não mostra implementação de `knowledge_consolidator.consolidate_document(...)`.
- Portanto, a existência de uma rota de chamada não é evidência suficiente de que `doc_chunk` esteja sendo transformado em entidades Neo4j por esse worker.
- A documentação desta área deve assumir como garantido apenas:
  - manifesto
  - indexação vetorial em `user_docs_<user_id>`
  - uso em citações/contexto de conversa

## Dependências externas e impacto de falha
### Qdrant indisponível
- O documento pode ser parseado localmente, mas a indexação vetorial falha.
- Citações documentais e o resumo contextual de anexos deixam de aparecer no chat.
- A recuperação posterior depende de reprocessar o documento ou da existência prévia dos pontos.

### Disco/local storage indisponível
- `stage_upload()` e `process_staged_document()` falham antes da indexação.
- `process_staged_document()` tenta recuperação parcial apenas se o manifesto já indicar chunks indexados no Qdrant.

### Embeddings indisponíveis
- `_ingest_payload()` depende de `aembed_texts(...)`.
- Sem embeddings não há `doc_chunk` consultável por similaridade.

## Riscos/Lacunas
- O manifesto e os pontos vetoriais podem divergir; o código já tem caminho de recuperação quando o arquivo staged some, mas os chunks ainda existem.
- O fluxo documental do chat depende de `conversation_id`; anexos fora da conversa ativa não entram no bloco resumido de `RAGService.retrieve_context()`.
- O código atual sugere uma consolidação documental para conhecimento, mas a implementação efetiva não aparece no worker inspecionado.

## Arquivos-fonte
- `backend/app/services/document_service.py`
- `backend/app/core/workers/document_ingestion_worker.py`
- `backend/app/services/chat/chat_citation_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/db/vector_store.py`
- `backend/app/services/knowledge_service.py`
