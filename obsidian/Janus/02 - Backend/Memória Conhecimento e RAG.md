---
tipo: dominio
dominio: backend
camada: conhecimento
fonte-de-verdade: codigo
status: ativo
---

# Memória Conhecimento e RAG

## Objetivo
Descrever o comportamento real de memória, grafo, documentos e recuperação a partir do código atual.

## Responsabilidades
- Separar o que é armazenado em Qdrant do que é armazenado em Neo4j.
- Explicar indexação do codebase, consolidação de experiências e recuperação usada no chat.
- Registrar dependências externas e modo de falha observado no código.

## Entradas
- Mensagens de chat.
- Experiências persistidas via `MemoryCore` e `GenerativeMemoryService`.
- Documentos ingeridos pelo `DocumentIngestionService`.
- Resumos de autoestudo (`self_study`) do repositório.

## Saídas
- Contexto de prompt para o chat.
- Nós e relações no grafo Neo4j.
- Coleções vetoriais por usuário e coleção episódica global.
- Citações documentais e de código.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]
- [[04 - Fluxos End-to-End/Conversa e Chat]]

## Mapa real de armazenamento
### Qdrant
- `janus_episodic_memory` é a coleção canônica do `MemoryCore` (`VectorCollection.EPISODIC_MEMORY`).
- `MemoryCore.amemorize()` redige PII, tenta embedding, cifra `content`, normaliza `metadata`, gera `consolidation_hash` e grava na coleção episódica global.
- `user_chat_<user_id>` recebe mensagens brutas do chat via `MemoryService.index_interaction()`. Esse fluxo não passa por `MemoryCore`.
- `user_docs_<user_id>` recebe `doc_chunk` via `DocumentIngestionService._ingest_payload()`.
- `user_memory_<user_id>` recebe espelho de memórias gerativas por usuário via `GenerativeMemoryService._mirror_to_user_collection()`.
- `user_secret_<user_id>` recebe segredos cifrados e isolados via `SecretMemoryService.store_secret()`.

### Neo4j
- `GraphDatabase` inicializa constraints, índices e tipos de relacionamento do grafo.
- `KnowledgeGraphService.persist_experience_node()` cria nós `Experience` e encadeia o fluxo temporal do usuário com `(:Experience)-[:NEXT]->(:Experience)`.
- `KnowledgeGraphService.persist_extraction()` consolida entidades em nós `Entity` e relacionamentos extraídos a partir de experiências.
- `KnowledgeRepository.save_code_structure()` cria/atualiza `File:CodeFile`, `Function:CodeFunction` e `Class:CodeClass`.
- `SelfMemory` é nó de grafo voltado a autoestudo de código; ele não é criado por `KnowledgeService`, e sim pelo fluxo de `AutonomyAdminService.run_self_study()`.

## Papel exato de Neo4j e Qdrant
### Qdrant
- É o backend principal de recuperação semântica para chat, documentos, memórias de usuário e segredos.
- Mantém as coleções por usuário e a coleção global `janus_episodic_memory`.
- É a fonte usada por `RAGService.retrieve_context()` para contexto de prompt.
- É a fonte usada por `chat_citation_service` para citações de documentos.
- É a fila persistente implícita de consolidação: `KnowledgeConsolidator` lê somente pontos pendentes em `janus_episodic_memory`.

### Neo4j
- É o backend estrutural para entidades, relações, experiência consolidada, code graph e `SelfMemory`.
- É usado por `KnowledgeService.index_codebase()` e pelas consultas de citação estrutural de código (`KnowledgeRepository.find_code_citations()`).
- Sustenta o grafo de autoestudo e a auditoria/reparo de `SelfMemory`.
- Não é a fonte principal de contexto do chat normal. O chat geral usa Qdrant; Neo4j entra em fluxos de conhecimento/código e administração.

## Memória: captura e persistência
### Memória episódica/generativa
- `GenerativeMemoryService.add_memory()` calcula `importance`, grava a experiência em `janus_episodic_memory`, espelha em `user_memory_<user_id>` e tenta persistir um nó `Experience` no Neo4j.
- Preferências de usuário e regras procedurais são capturadas a partir da mensagem pelo `ActiveMemoryService`, mas persistidas via `GenerativeMemoryService`, portanto entram em Qdrant e também no fluxo `Experience` do Neo4j.
- Segredos seguem um caminho separado: `SecretMemoryService` grava apenas em `user_secret_<user_id>` com `recall_policy=explicit_only`.

### Chat raw memory
- `RAGService.maybe_index_message()` delega para `MemoryService.index_interaction()`.
- `index_interaction()` grava apenas em `user_chat_<user_id>`, com `type=chat_msg`, `memory_class=episodic`, `retention_policy=rolling_window` e `scope=session`.
- Essas mensagens de chat não entram em `janus_episodic_memory`; portanto não são consumidas pelo `KnowledgeConsolidator`.

### Contrato de metadata observado
- `MemoryCore._normalize_metadata_contract()` sempre força chaves como `origin`, `source_kind`, `content_kind`, `memory_class`, `consolidation_status`, `neo4j_sync_status`, `file_path`, `sha_after`, `memory_key`, `summary_version`, `retention_policy`, `recall_policy`, `sensitivity`, `stability_score` e `scope`.
- O contrato é importante porque os filtros de recall e a consolidação dependem dessas chaves.

## Consolidação: o que realmente vira conhecimento
### Fluxo confirmado em código
- `KnowledgeConsolidator.consolidate_batch()` lê de `janus_episodic_memory` apenas pontos com `metadata.consolidation_status` pendente/nulo/vazio.
- `consolidate_experience()` quebra o texto em chunks, exceto quando `content_kind == code_summary`.
- Cada chunk é enviado para `KnowledgeExtractionService.extract_from_text(...)`.
- O resultado é persistido em Neo4j por `KnowledgeGraphService.persist_extraction(...)`.
- Ao final, `_mark_as_consolidated()` atualiza no Qdrant `consolidated=True`, `consolidation_status=done`, `neo4j_sync_status=consolidated` e contadores de entidades/relações.

### Limite importante
- O worker consolida a coleção `janus_episodic_memory`.
- `user_chat_<user_id>` e `user_docs_<user_id>` não fazem parte desse loop.
- Quando `_mark_as_consolidated()` não encontra o ponto na coleção episódica, o próprio código assume que isso pode ocorrer com mensagens de chat indexadas em coleções `user_*`.

## Codebase indexing
### O que o indexador faz
- `KnowledgeService.index_codebase()` limpa símbolos de código no Neo4j com `KnowledgeRepository.clear_code_entities()`.
- Depois varre arquivos Python sob `CODEBASE_DIR = "/app"` usando `CodeAnalysisService.find_python_files()`.
- Cada arquivo é parseado por AST com `CodeAnalysisService.parse_python_file()`.
- `KnowledgeRepository.save_code_structure()` cria/atualiza:
  - `File:CodeFile`
  - `Function:CodeFunction`
  - `Class:CodeClass`
  - relações `CONTAINS`
- `KnowledgeRepository.bulk_merge_calls()` cria relações `CALLS` entre funções.

### O que o indexador não faz
- Não gera resumos de arquivo.
- Não grava embeddings no Qdrant.
- Não cria `SelfMemory`.
- Não consolida documentos.

## Self-memory
### Como é criado
- A criação real está em `AutonomyAdminService.run_self_study()`, não em `KnowledgeService`.
- O autoestudo resume arquivos do repositório e monta `summary_payload` com `summary`, `symbols`, `imports`, `touchpoints`, `domain_tags`, `risks`, `test_impact` e `summary_version`.
- `_memorize_self_study_summary()` grava uma experiência em `janus_episodic_memory` com:
  - `origin=self_study`
  - `source_kind=code_file`
  - `content_kind=code_summary`
  - `strong_memory=True`
  - `memory_key`
  - `sha_after`
  - `summary_version`
- `_ensure_self_study_experience_node()` cria/atualiza o nó `Experience` correspondente no Neo4j.
- `_persist_self_memory()` cria/atualiza o nó `SelfMemory` e tenta ligá-lo a `File/CodeFile`, símbolos e `Experience`.

### O que `KnowledgeService` faz com self-memory
- `repair_self_memory_graph()` repara vínculos de nós `SelfMemory` já existentes.
- `_repair_single_self_memory()` recalcula `memory_key`, ajusta `file_path`, `summary_version`, `sha_after`, marca `is_current`, remove links inválidos e recria:
  - `(:SelfMemory)-[:RELATES_TO]->(:File|:CodeFile)`
  - `(:SelfMemory)-[:DEFINES]->(:CodeFunction|:CodeClass)`
  - `(:SelfMemory)-[:EXTRACTED_FROM]->(:Experience)`
- `get_self_memory_neo4j_audit()` mede órfãos, ausência de proveniência e ausência de `sha_after`.

### Como é recuperado
- No fluxo administrativo de código, `AutonomyAdminService.ask_code_as_admin()` mistura:
  - citações estruturais vindas do Neo4j
  - `SelfMemory` atual do Neo4j
  - busca híbrida vetorial/lexical sobre memórias `self_study` em Qdrant (`CodeHybridSearchService`)

## Recuperação usada no chat
### `RAGService.retrieve_context()`
- Só segue adiante se existir `MemoryService`, `message`, `user_id` e a política de rota escolher `RouteTarget.QDRANT`.
- O contexto retornado é um bloco textual para prompt, não uma estrutura de citação.

### Fontes consultadas
- Contexto episódico: busca vetorial em `user_chat_<user_id>`, com reranker semântico opcional e score final que favorece mesma `conversation_id` e recência.
- Contexto semântico: `UserPreferenceMemoryService.list_preferences()` em `user_memory_<user_id>`.
- Contexto procedural: `ProceduralMemoryService.list_rules()` em `user_memory_<user_id>`.
- Contexto secreto: `SecretMemoryService.build_authorized_prompt_context()` em `user_secret_<user_id>`, apenas se a mensagem autorizar explicitamente recuperação.
- Contexto documental leve: se a mensagem mencionar arquivo/anexo/documento, `_conversation_document_context()` faz `scroll` em `user_docs_<user_id>` filtrando `doc_chunk` da conversa atual.

### O que não entra automaticamente
- O chat geral não consulta Neo4j para montar `relevant_memories`.
- O chat geral não usa `janus_episodic_memory` como fonte direta de prompt.
- `KnowledgeService.semantic_query()` existe, mas não faz parte do caminho normal de `RAGService.retrieve_context()`.

### Citações do chat
- `chat_citation_service.collect_document_citations()` consulta `user_docs_<user_id>` com embedding da pergunta.
- `collect_chat_citations()` também tenta `MemoryService.recall_filtered()`, ou seja, a coleção episódica por trás do repositório de memória.
- Contexto de prompt e citações são pipelines diferentes.

## Documentos: o que o código comprova
- `DocumentIngestionService` transforma o arquivo em texto, aplica enriquecimento semântico, quebra em chunks e grava `doc_chunk` em `user_docs_<user_id>`.
- O chat usa esses chunks para citações e para um resumo leve de anexos da conversa.
- O código lido não comprova uma consolidação de `doc_chunk` para Neo4j equivalente à consolidação de experiências episódicas.
- `KnowledgeService.consolidate_document()` delega para `knowledge_consolidator.consolidate_document(...)`, mas essa implementação não aparece em `knowledge_consolidator_worker.py` no estado atual do código.

## Dependências externas e impacto de falha
### Qdrant indisponível
- `QdrantProvider` entra em modo offline; `MemoryCore.health_check()` passa a falhar.
- `MemoryCore.amemorize()` ainda pode manter item no cache local do processo, mas perde persistência vetorial até a conexão voltar.
- `MemoryService.index_interaction()` não tem cache local; falha de Qdrant faz a indexação do chat ser perdida.
- `RAGService.retrieve_context()` degrada para `None` e o chat segue sem contexto adicional.
- Ingestão e citações de documentos degradam ou falham.
- `KnowledgeConsolidator` não consegue ler a coleção episódica.

### Neo4j indisponível
- `GraphDatabase.connect()` pode entrar em modo offline.
- `query()` passa a devolver `[]` e `execute()` vira no-op; o sistema tende a degradar para vazio em vez de sempre lançar erro.
- `KnowledgeService.index_codebase()` depende de sessão/transação real e deixa de indexar código.
- Persistência de entidades/relacionamentos e auditoria de `SelfMemory` ficam indisponíveis.
- `ask_code_with_citations()` perde a parte estrutural do code graph.

### Embeddings/LLM indisponíveis
- `MemoryCore` e vários serviços caem para vetor zero quando embedding falha.
- `GenerativeMemoryService` usa LLM para `importance`; sem LLM cai em defaults.
- `KnowledgeConsolidator` depende de extração por LLM; sem isso a consolidação não produz entidades/relações.
- `GraphRAGCore` depende de embedder compatível com OpenAI e de síntese LLM.

## Riscos/Lacunas
- `GraphRAGCore` espera índices `janus_vector_index` e `janus_fulltext_index`, mas `GraphDatabase._initialize_ontology()` cria `entity_embeddings`, `concept_embeddings`, `keyword_search` e `entity_keyword_search`. O código atual pode deixar o GraphRAG desabilitado mesmo com Neo4j saudável.
- O code graph e o self-memory são fluxos diferentes: indexar o codebase não cria resumos; rodar self-study não substitui a indexação estrutural.
- O chat normal usa Qdrant por usuário; conhecimento em Neo4j não é consultado automaticamente nesse caminho.
- O worker de consolidação atua sobre `janus_episodic_memory`; mensagens do chat e chunks de documentos ficam fora desse pipeline.

## Arquivos-fonte
- `backend/app/services/memory_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/core/memory/memory_core.py`
- `backend/app/core/memory/generative_memory.py`
- `backend/app/core/memory/graph_embeddings.py`
- `backend/app/core/memory/graph_rag_core.py`
- `backend/app/core/memory/providers/qdrant_provider.py`
- `backend/app/db/graph.py`
- `backend/app/db/vector_store.py`
- `backend/app/repositories/knowledge_repository.py`
- `backend/app/services/code_analysis_service.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/services/code_hybrid_search_service.py`
- `backend/app/services/user_preference_memory_service.py`
- `backend/app/services/procedural_memory_service.py`
- `backend/app/services/secret_memory_service.py`
- `backend/app/services/chat/chat_citation_service.py`
- `backend/app/services/document_service.py`
- `backend/app/core/workers/knowledge_consolidator_worker.py`
