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
- Estrutura de `KnowledgeSpace` quando a consolidação desse domínio é disparada.

## Dependências
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[01 - Visão do Sistema/Dependências Externas]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Superfície frontend real dentro de `conversations`
- O fluxo documental não vive numa tela dedicada; ele aparece no rail avançado `Cliente` de `frontend/src/app/features/conversations/conversations.ts`.
- A aba `Docs` expõe quatro operações distintas na mesma conversa:
  - upload de arquivo via `file` input com progresso reportado via callback de evento (`selectedUploadFile`, `docUploadInFlight`, `docUploadProgress`)
  - vínculo remoto por URL via `linkUrl(conversation_id, url, user_id)`
  - busca manual de trechos via `searchDocuments(query, ..., userId)`
  - exclusão da biblioteca da conversa via `deleteDocument(docId, userId)`
  - Status `file_too_large` e `quota_exceeded` tratados explicitamente no callback de upload
- Ao selecionar uma conversa, `loadContext(conversationId)` recarrega em paralelo:
  - `listDocuments(conversationId, userId)` para a biblioteca documental
  - `getMemoryTimeline(..., conversation_id=conversationId)` para memória associada
- A aba `Memória` suporta criação de memórias generativas (`addGenerativeMemory`) com definição explícita de `importance` (0-10) e `type` (episodic, semantic, procedural), comunicando-se com a API `/memory/generative`.
- A aba `RAG` permite consultas manuais roteadas para diferentes modos suportados pela UI: `search`, `user_chat`, `hybrid_search` e `productivity`.
- A UI coloca `Docs`, `Memória` e `RAG` lado a lado por desenho de produto. Isso é importante porque o operador valida o efeito do documento no mesmo painel em que:
  - grava memória generativa
  - consulta memória existente
  - roda RAG manual para inspeção

Ponto importante:
- O frontend trata documentos como contexto da conversa ativa, não como um acervo global genérico. A biblioteca exibida no rail é scoped pelo `conversation_id` selecionado.

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
4. `vector_store.py` garante que `user_docs_<user_id>` seja criada com payload indexes específicos para filtros documentais recorrentes, como `doc_id`, `knowledge_space_id`, `source_type`, `doc_role`, `conversation_id`, `file_name`, `status` e `timestamp`.
5. Antes do upsert, `_delete_doc_points()` remove chunks antigos do mesmo `doc_id`.
6. Ao final, o manifesto é marcado como `completed` com `chunks_total`, `chunks_indexed` e resumo semântico.

## Persistência por etapa
- Stage:
  - disco local para arquivo staged
  - Postgres para `DocumentManifest`
- Indexação:
  - Qdrant para `user_docs_<user_id>`
  - Postgres continua como fonte do estado do processamento
- Uso no chat:
  - Qdrant para chunks e citações
  - Postgres apenas para saber quais documentos/manifests estão associados à conversa
- Knowledge space:
  - Postgres para `knowledge_spaces` e associação dos manifests
  - Qdrant para seções canônicas
  - Neo4j para raiz e estrutura navegável do space quando `_persist_structure_graph()` roda

## Como documentos entram no chat
### Citações
- `chat_citation_service.collect_document_citations()` consulta `user_docs_<user_id>` por embedding da pergunta.
- Se não houver hits e a pergunta mencionar material enviado, `_recent_document_citations()` faz `scroll` recente na mesma coleção.
- As citações vêm exclusivamente de `doc_chunk` em Qdrant no fluxo lido aqui.

### Branch documental no fluxo de conversa
- Em `MessageOrchestrationService.generate_document_grounded_reply()`, a existência de manifests documentais já basta para o serviço tentar grounding.
- No estado atual do código, `_should_use_document_grounding()` devolve `True` para qualquer conversa com manifests.
- Isso significa que, na conversa principal, anexar um documento muda o branch prioritário da conversa inteira:
  - primeiro knowledge space, se resolvível
  - depois grounding documental
  - só depois fluxo geral de chat, se o grounding não se aplicar
- A nota [[04 - Fluxos End-to-End/Conversa e Chat]] detalha o efeito disso sobre REST e SSE.

Reflexo direto na UI:
- Depois de upload, link ou exclusão, `refreshConversationContext()` recarrega o contexto da conversa.
- O operador percebe esse branch dominante no mesmo lugar em que conversa com o Janus; não existe separação entre “módulo de documentos” e “módulo de chat”.

### Contexto de prompt
- `RAGService.retrieve_context()` não injeta chunks completos.
- Se a mensagem mencionar arquivo/anexo/documento, `_conversation_document_context()` faz `scroll` em `user_docs_<user_id>` filtrando:
  - `metadata.type = doc_chunk`
  - `metadata.user_id = <user>`
  - `metadata.conversation_id = <conversa>`
- Esse passo é um `scroll` filtrado por conversa, não uma busca vetorial nova.
- O resultado é um bloco textual curto com nome do arquivo e `semantic_summary` ou preview do chunk.

### Busca e Recuperação RAG
Além do contexto injetado automaticamente, o sistema expõe endpoints explícitos de RAG que roteiam a intenção do usuário (`get_knowledge_routing_policy().resolve()`) para as bases apropriadas (Qdrant e/ou Neo4j):
- `/rag/search`: Busca geral baseada em fatos consultando a memória vetorial.
- `/rag/user_chat` (e `v2`): Busca semântica restrita a mensagens pessoais em `user_chat_<user_id>`.
- `/rag/productivity`: Busca focada em itens de calendário, e-mails e notas do usuário.
- `/rag/hybrid_search`: Busca híbrida de código que combina recuperação lexical/grafo (Neo4j) com vetorial (Qdrant).

## Relação com memória
- `user_docs_<user_id>` é uma coleção vetorial isolada das coleções de memória (`user_memory_<user_id>`, `user_chat_<user_id>`, `user_secret_<user_id>`) e da coleção global `janus_episodic_memory`.
- `doc_chunk` não passa por `MemoryCore.amemorize()`.
- A recuperação documental do chat é separada do recall de `user_chat_<user_id>` e `user_memory_<user_id>`.
- `collect_chat_citations()` pode combinar documentos e memórias, mas são pipelines distintos.
- O frontend reforça essa separação: a aba `Memória` usa endpoints próprios que refletem os namespaces de conhecimento:
  - `/memory/generative`: gerencia memória episódica, semântica e procedural.
  - `/memory/preferences`: consulta preferências do usuário.
  - `/memory/secrets`: consulta segredos autorizados.
  - `/memory/timeline`: exibe a linha do tempo consolidada.
- `generativeMemoryMetaLine()` formata a visualização de cada item de memória generativa como: tipo (episodic/semantic/procedural), importância numérica (0-10), score e timestamp de criação/atualização.
- Ao mesmo tempo, o desenho da tela faz as três coisas parecerem vizinhas operacionais:
  - documentos enriquecem grounding e citações
  - memória generativa guarda fatos/preferências
  - RAG manual serve para inspecionar o que cada pipeline está devolvendo

## Relação com conhecimento/Neo4j
### O que o código comprova
- A ingestão documental mostrada aqui termina em Qdrant + manifesto.
- `process_document_ingestion_task()` pode tentar auto-consolidação:
  - `KnowledgeSpaceService.consolidate_space(...)` quando existe `knowledge_space_id`
  - `KnowledgeService.consolidate_document(...)` quando não existe
- No caminho de `KnowledgeSpaceService.consolidate_space(...)`, a persistência comprovada é composta:
  - lê manifests em Postgres
  - lê chunks em Qdrant
  - pode gravar estrutura em Neo4j

### O que o código não comprova neste estado
- O código lido não mostra implementação de `knowledge_consolidator.consolidate_document(...)`.
- Portanto, a existência de uma rota de chamada não é evidência suficiente de que `doc_chunk` esteja sendo transformado em entidades Neo4j por esse worker.
- A documentação desta área deve assumir como garantido apenas:
  - manifesto
  - indexação vetorial em `user_docs_<user_id>`
  - uso em citações/contexto de conversa
- Em outras palavras: `doc_chunk` não entra no mesmo pipeline observado de `janus_episodic_memory` usado pelo `KnowledgeConsolidator.consolidate_batch()`.

## Dependências externas e impacto de falha
### Qdrant indisponível
- O documento pode ser parseado localmente, mas a indexação vetorial falha.
- Citações documentais e o resumo contextual de anexos deixam de aparecer no chat.
- A recuperação posterior depende de reprocessar o documento ou da existência prévia dos pontos.

### Postgres indisponível
- Não há manifesto confiável para acompanhar o documento nem para ligá-lo à conversa/knowledge space.
- Mesmo que o arquivo exista em disco, o fluxo perde rastreabilidade operacional.

### Neo4j indisponível
- A ingestão básica documental segue em manifesto + Qdrant.
- Apenas a parte estrutural de `KnowledgeSpace` fica parcial.

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
- O domínio documental é multi-store: olhar só manifesto SQL ou só Qdrant não basta para entender o estado real do documento.
- Como a existência de manifests já empurra a conversa para o branch documental, qualquer desvio ou imprecisão nesse fluxo impacta diretamente a conversa principal, não apenas um submódulo de documentos.
- Como a UI concentra docs, memória e RAG no mesmo rail, qualquer inconsistência de sincronização pós-upload aparece imediatamente como ruído na experiência da conversa, não só como problema de “gestão documental”.

## Arquivos-fonte
- `backend/app/services/document_service.py`
- `backend/app/core/workers/document_ingestion_worker.py`
- `backend/app/services/chat/chat_citation_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/db/vector_store.py`
- `backend/app/services/knowledge_service.py`
- `frontend/src/app/features/conversations/conversations.ts`
- `frontend/src/app/features/conversations/admin-code-qa.util.ts`
