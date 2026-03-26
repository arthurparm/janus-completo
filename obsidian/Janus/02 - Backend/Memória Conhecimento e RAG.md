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
- `vector_store.py` não trata Qdrant como uma coleção única: ele infere tuning, payload indexes e naming por finalidade (`janus_episodic_memory`, `user_chat_*`, `user_docs_*`, `user_memory_*`, `user_secret_*`).

### Neo4j
- `GraphDatabase` inicializa constraints, índices e tipos de relacionamento do grafo.
- `GraphDatabase._initialize_ontology()` também tenta criar índices vetoriais e full-text no próprio Neo4j (`concept_embeddings`, `technology_embeddings`, `tool_embeddings`, `pattern_embeddings`, `entity_embeddings`, `keyword_search`, `entity_keyword_search`).
- `KnowledgeGraphService.persist_experience_node()` cria nós `Experience` e encadeia o fluxo temporal do usuário com `(:Experience)-[:NEXT]->(:Experience)`.
- `KnowledgeGraphService.persist_extraction()` consolida entidades em nós `Entity` e relacionamentos extraídos a partir de experiências.
- `KnowledgeRepository.save_code_structure()` cria/atualiza `File:CodeFile`, `Function:CodeFunction` e `Class:CodeClass`.
- `SelfMemory` é nó de grafo voltado a autoestudo de código; ele não é criado por `KnowledgeService`, e sim pelo fluxo de `AutonomyAdminService.run_self_study()`.

## Papel exato de Neo4j e Qdrant - Quando usar cada um

### Qdrant - Banco Vetorial Principal
**Use Qdrant quando precisar de:**
- **Recuperação semântica** e similaridade por embeddings
- **Memória episódica** e histórico de conversas
- **Contexto para RAG** no chat em tempo real
- **Citações de documentos** durante conversação
- **Preferências e regras** personalizadas por usuário
- **Segredos e informações sensíveis** isoladas por usuário

**Coleções principais e seus papéis:**
| Coleção | Tipo de Dados | Acesso | Latência Esperada | Fallback |
|---------|---------------|---------|-------------------|----------|
| `janus_episodic_memory` | Memórias consolidadas | Global | < 200ms | Cache local limitado |
| `user_chat_<user_id>` | Histórico de chat | Por usuário | < 150ms | SQL apenas |
| `user_docs_<user_id>` | Documentos chunkados | Por usuário | < 200ms | Nenhum |
| `user_memory_<user_id>` | Preferências/regras | Por usuário | < 100ms | Defaults do sistema |
| `user_secret_<user_id>` | Segredos cifrados | Por usuário | < 100ms | Nenhum (falha se não autorizado) |

**Características técnicas:**
- **Embeddings**: OpenAI Ada-002 (1536 dimensões)
- **Similaridade**: Cosseno por padrão
- **Indexação**: HNSW para busca aproximada
- **Criptografia**: AES-256 para conteúdo sensível
- **Isolamento**: Dados por usuário em coleções separadas

### Neo4j - Grafo de Conhecimento Estrutural  
**Use Neo4j quando precisar de:**
- **Relacionamentos complexos** entre entidades
- **Grafo de código** com dependências e chamadas
- **Ontologia de domínio** e taxonomias
- **Análise de impacto** e navegação de dependências
- **Consolidação de experiências** em estrutura semântica
- **Self-memory** e autoestudo de código

**Tipos de nós e relações principais:**
| Tipo | Exemplos | Uso Principal | Performance |
|------|----------|---------------|-------------|
| `Experience` | Eventos, memórias | Timeline do usuário | ~500ms para timeline completa |
| `Entity` | Conceitos, tecnologias | Grafo de conhecimento | < 200ms para busca por tipo |
| `CodeFile` | Arquivos Python | Indexação de código | ~2s para codebase completo |
| `CodeFunction` | Funções, métodos | Análise de dependências | < 100ms por arquivo |
| `SelfMemory` | Resumos de código | Autoestudo | < 500ms para consultas |

**Características técnicas:**
- **Query language**: Cypher
- **Índices**: Vetoriais e full-text integrados
- **Constraints**: Unique constraints em `memory_key`
- **Transações**: ACID para operações críticas
- **Cache**: Resultados em memória para queries frequentes

### Quando cada banco é usado no fluxo de chat

#### Fluxo normal de RAG no chat:
1. **Qdrant** → `RAGService.retrieve_context()` → Contexto para prompt
2. **Qdrant** → `chat_citation_service` → Citações para resposta
3. **PostgreSQL** → Histórico de mensagens → Estrutura da conversa

#### Fluxo de análise de código:
1. **Neo4j** → `KnowledgeRepository.find_code_citations()` → Estrutura de código
2. **Neo4j** → `CodeHybridSearchService` → Busca híbrida em código
3. **Qdrant** → Memórias de self-study → Contexto adicional

#### Fluxo de consolidação de conhecimento:
1. **Qdrant** → `janus_episodic_memory` → Memórias para consolidar
2. **Neo4j** → `KnowledgeGraphService.persist_extraction()` → Entidades e relações
3. **Qdrant** → Atualização com `consolidated=True` → Marca como processado

### Estratégias de Fallback

#### Qdrant indisponível:
- **Modo offline**: `QdrantProvider` detecta e entra em modo offline
- **Cache local**: `MemoryCore` mantém últimas memórias em cache por 5 minutos
- **Degradação gradual**: 
  - Chat perde contexto histórico mas mantém estrutura SQL
  - Documentos não são indexados nem recuperados
  - RAG retorna `None`, chat continua sem enriquecimento

#### Neo4j indisponível:
- **Modo offline**: `GraphDatabase.connect()` entra em modo offline
- **Queries vazias**: Retorna `[]` para consultas, não quebra o fluxo
- **Chat desimpedido**: Chat básico continua funcionando com Qdrant
- **Análise limitada**: Code analysis e knowledge graph ficam indisponíveis

#### Ambos indisponíveis:
- **Chat básico**: Apenas PostgreSQL para estrutura da conversa
- **Sem memória**: Sistema opera como chat stateless
- **Sem RAG**: Respostas baseadas apenas em contexto do prompt atual

### Performance e Latência

#### Targets de latência observados no código:
- **Qdrant busca**: < 200ms para recall de 10 itens
- **Neo4j queries**: < 500ms para consultas complexas  
- **Consolidação**: Processamento em lote a cada 30 segundos
- **Indexação**: Assíncrona via workers do RabbitMQ

#### Fatores que afetam performance:
- **Tamanho do embedding**: 1536 dimensões (OpenAI)
- **Quantidade de dados**: Milhares de memórias por usuário
- **Complexidade do grafo**: Dezenas de milhares de nós de código
- **Carga concorrente**: Múltiplos usuários simultâneos

### Postgres
- Não guarda embeddings nem relações semânticas, mas é parte do pipeline de persistência.
- Guarda o manifesto documental em `document_manifests`, o estado de `knowledge_spaces`, mensagens persistidas do chat e metadados que depois referenciam contexto vetorial/estrutural.
- Também guarda estado operacional de autonomia e o checkpointer do `graph_orchestrator`.

### Redis
- Não participa como backend de memória ou conhecimento.
- Atua apenas como coordenação efêmera para rate limit, hot-reload de configuração e quotas/spend temporários.

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
- Isso inclui memórias de `self_study` gravadas em `janus_episodic_memory`: elas entram no mesmo loop de consolidação, mas `code_summary` evita chunking adicional.

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
- Ao final do fluxo, `index_codebase()` chama `repair_self_memory_graph()` para religar `SelfMemory` existente ao code graph recém-indexado.

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
- A composição final do contexto segue esta ordem lógica: segredos autorizados, regras procedurais, preferências, contexto episódico recente e, quando aplicável, um bloco introdutório curto sobre documentos anexados na conversa.

### Assimetria importante entre REST e SSE
- O caminho REST do chat agenda `RAGService.maybe_index_message()` para mensagem do usuário e para a resposta do assistente.
- O caminho SSE do chat não agenda `maybe_index_message()`.
- Como a UI de conversa usa SSE por padrão, a coleção `user_chat_<user_id>` pode ficar menos atualizada do que o histórico SQL real.
- Na prática:
  - o histórico persistido em SQL continua crescendo
  - o prompt enriquecido por Qdrant pode refletir só turnos passados por REST ou legados
  - a sensação de “memória recente” pode divergir do que o operador vê na conversa

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

### Relação com o fluxo de conversa
- O chat usa RAG de duas formas diferentes:
  - enriquecimento de prompt via `retrieve_context()`
  - citação posterior via `collect_chat_citations()`
- Esses dois caminhos não compartilham necessariamente a mesma fonte final:
  - o prompt usa sobretudo `user_chat_<user_id>`, preferências, procedural e segredos
  - as citações podem vir de documentos, memórias ou fallback de study
- Isso explica por que uma resposta pode:
  - ter contexto relevante no prompt e ainda assim sair sem `citations`
  - ou ter `citations` documentais mesmo quando o prompt principal veio mais de memória episódica

## Documentos: o que o código comprova
- `DocumentIngestionService` transforma o arquivo em texto, aplica enriquecimento semântico, quebra em chunks e grava `doc_chunk` em `user_docs_<user_id>`.
- O mesmo service cria e atualiza `DocumentManifest` em Postgres antes, durante e depois da indexação.
- O chat usa esses chunks para citações e para um resumo leve de anexos da conversa.
- O código lido não comprova uma consolidação de `doc_chunk` para Neo4j equivalente à consolidação de experiências episódicas.
- `KnowledgeService.consolidate_document()` delega para `knowledge_consolidator.consolidate_document(...)`, mas essa implementação não aparece em `knowledge_consolidator_worker.py` no estado atual do código.

## Knowledge space: persistência composta
- `KnowledgeSpaceRepository` guarda em Postgres o espaço, seu estado de consolidação, contadores e resumo operacional.
- `DocumentManifestRepository` liga cada documento ao `knowledge_space_id`, também em Postgres.
- `KnowledgeSpaceService` reaproveita `user_docs_<user_id>` no Qdrant para persistir seções e frames canônicos do espaço consolidado.
- `_persist_structure_graph()` projeta esse mesmo espaço no Neo4j como `KnowledgeSpace`, `Work`, `Section`, `Concept`, `Entity` e encadeamento `NEXT_SECTION`.
- Portanto, `KnowledgeSpace` depende de três camadas:
  - Postgres para controle e status
  - Qdrant para recuperação textual/vetorial
  - Neo4j para estrutura navegável
- A falha de Neo4j nesse fluxo é parcial: o serviço atualiza o status em Postgres e mantém a consolidação vetorial, mas marca no sumário que a persistência de grafo ficou parcial.

## Circuit Breakers e Modos de Falha

### Implementação de Circuit Breakers

#### QdrantProvider
```python
# Detecção de falha e modo offline
if not self._client.health_check():
    logger.warning("Qdrant health check failed, entering offline mode")
    self._offline_mode = True
    self._last_offline_check = time.time()
```

**Comportamento em modo offline:**
- **Cache local**: Mantém últimas 100 memórias em memória por 5 minutos
- **Operações de leitura**: Retornam dados do cache ou `None` se não houver cache
- **Operações de escrita**: Falham silenciosamente com log de warning
- **Recuperação**: Verifica saúde a cada 30 segundos quando offline

#### GraphDatabase (Neo4j)
```python
# Modo offline sem exceções
except Exception as e:
    logger.warning(f"Neo4j connection failed, entering offline mode: {e}")
    self._offline_mode = True
    return  # Não propaga exceção
```

**Comportamento em modo offline:**
- **Queries**: Retornam listas vazias `[]`
- **Execute**: Torna-se no-op (não executa nada)
- **Transações**: Não são iniciadas
- **Recuperação**: Tenta reconectar a cada minuto

### Dependências externas e impacto de falha

#### Qdrant indisponível
- **Detecção**: `QdrantProvider` entra em modo offline via health check
- **Impacto imediato**: 
  - `MemoryCore.health_check()` falha
  - `MemoryCore.amemorize()` usa cache local por 5 minutos
  - `MemoryService.index_interaction()` falha sem cache (chat não indexado)
  - `RAGService.retrieve_context()` retorna `None` (sem contexto RAG)
- **Degradação gradual**:
  - Primeiros 5 minutos: Cache local pode salvar algumas operações
  - Após 5 minutos: Todas operações vetoriais falham
  - Documentos não são indexados nem recuperados
  - `KnowledgeConsolidator` não consegue ler `janus_episodic_memory`

#### Neo4j indisponível
- **Detecção**: `GraphDatabase.connect()` entra em modo offline
- **Impacto imediato**:
  - `query()` retorna `[]` para qualquer consulta
  - `execute()` vira no-op (não executa)
  - Chat básico continua funcionando normalmente
- **Funcionalidades perdidas**:
  - `KnowledgeService.index_codebase()` para de indexar código
  - Persistência de entidades/relacionamentos falha silenciosamente
  - `ask_code_with_citations()` perde estrutura de code graph
  - Auditoria de `SelfMemory` fica indisponível
- **Vantagem**: Falha silenciosa preserva UX do chat

#### Postgres indisponível
- **Impacto crítico**: Sistema não inicializa (health check falha no boot)
- **Se falhar após boot**:
  - Chat persistido: Mensagens novas não são salvas
  - Identidade: Login e autenticação falham
  - Knowledge spaces: Metadados e status perdidos
  - Autonomia: Estado de execução comprometido
- **Fallback limitado**:
  - `graph_orchestrator` degrada para `MemorySaver` (perde durabilidade)
  - Mas perde controle transacional do sistema

#### Redis indisponível
- **Impacto moderado**: 
  - Rate limit: Fail-open ou fallback local em endpoints específicos
  - Configurações: Hot-reload para de funcionar (requer reinício)
  - Quotas: Tracking vira best-effort
- **Preservação**: Não afeta memórias ou documentos já persistidos

#### Embeddings/LLM indisponíveis
- **Cascata de falhas**:
  - `MemoryCore`: Vetor zero quando embedding falha
  - `GenerativeMemoryService`: Usa defaults quando LLM falha
  - `KnowledgeConsolidator`: Não produz entidades sem extração LLM
  - `GraphRAGCore`: Requer embedder OpenAI compatível
- **Impacto**: Perda de qualidade, não quebra funcionalidade básica

### Estratégias de Recuperação

#### Ordem de recuperação recomendada:
1. **PostgreSQL** (mais crítico - sistema não funciona sem)
2. **Qdrant** (RAG e memória essenciais para UX)
3. **Neo4j** (funcionalidades avançadas mas chat básico funciona)
4. **Redis** (performance e quotas)
5. **RabbitMQ** (processamento assíncrono)
6. **Ollama** (provedor local opcional)

#### Métricas de monitoramento:
- **Qdrant**: Latência de busca < 200ms, recall > 0.8
- **Neo4j**: Tempo de query < 500ms, conexões ativas
- **PostgreSQL**: Latência < 100ms, taxa de erro < 1%
- **Redis**: Hit ratio > 0.9, latência < 5ms

## Riscos/Lacunas
- `GraphRAGCore` espera índices `janus_vector_index` e `janus_fulltext_index`, mas `GraphDatabase._initialize_ontology()` cria `entity_embeddings`, `concept_embeddings`, `keyword_search` e `entity_keyword_search`. O código atual pode deixar o GraphRAG desabilitado mesmo com Neo4j saudável.
- O code graph e o self-memory são fluxos diferentes: indexar o codebase não cria resumos; rodar self-study não substitui a indexação estrutural.
- O chat normal usa Qdrant por usuário; conhecimento em Neo4j não é consultado automaticamente nesse caminho.
- O worker de consolidação atua sobre `janus_episodic_memory`; mensagens do chat e chunks de documentos ficam fora desse pipeline.
- `DataRetentionService` tenta limpar Qdrant em coleções hardcoded que não batem com as coleções realmente usadas pelos fluxos atuais, então a política de retenção cross-store não está coerente com a persistência observada.

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
