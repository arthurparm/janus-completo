---
tipo: visao
dominio: sistema
camada: integracoes
fonte-de-verdade: codigo
status: ativo
---

# Dependências Externas

## Objetivo
Consolidar os recursos externos realmente necessários para memória, conhecimento, documentos e RAG.

## Responsabilidades
- Separar dependência estrutural de dependência contextual.
- Registrar o papel técnico de Neo4j, Qdrant e provedores de embedding/LLM.
- Explicitar o efeito de falha observado no código.

## Entradas
- `backend/app/config.py`
- `backend/app/core/kernel.py`
- `backend/app/db/graph.py`
- `backend/app/db/vector_store.py`
- Serviços de memória, conhecimento, documentos e chat

## Saídas
- Mapa de integração externa por responsabilidade.

## Dependências
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Dependências estruturais
### Postgres
- Sustenta a fonte de verdade transacional do backend.
- Domínios observados:
  - identidade, consentimento, auditoria e OAuth
  - sessões e mensagens do chat
  - prompts, agent config e optimization history
  - pending actions, outbox e quotas diárias de tools
  - runs, steps, goals, leases e estado de self-study da autonomia
  - `document_manifests` e `knowledge_spaces`
- Também sustenta persistência do estado do `graph_orchestrator` via `AsyncPostgresSaver`.
- Não é a base principal de memória/RAG, mas sem ele o plano de controle do produto quebra.

### Redis
- Suporte infra e coordenação efêmera.
- Funções observadas:
  - rate limit HTTP com Lua token bucket
  - Pub/Sub de hot-reload de configuração
  - contabilidade de spend LLM por provider/tenant/objetivo
  - quotas temporárias por janela deslizante para tools
- Não é a base principal de memória/conhecimento.

### RabbitMQ
- Sustenta workers como `document_ingestion` e consolidação assíncrona.
- Sem broker, o backend perde processamento desacoplado, mas parte dos fluxos síncronos continua existindo.

### Qdrant
- É a dependência estrutural do armazenamento vetorial.
- Coleções observadas no código:
  - `janus_episodic_memory`
  - `user_chat_<user_id>`
  - `user_docs_<user_id>`
  - `user_memory_<user_id>`
  - `user_secret_<user_id>`
- Sustenta:
  - memória episódica persistida por `MemoryCore`
  - indexação do chat para `RAGService.retrieve_context()`
  - indexação de documentos
  - preferências/regras do usuário
  - segredos
  - busca híbrida de autoestudo no fluxo administrativo

### Neo4j
- É a dependência estrutural do grafo de conhecimento.
- Sustenta:
  - `Entity` e relações consolidadas
  - `Experience` no grafo
  - `File`, `CodeFile`, `Function`, `CodeFunction`, `Class`, `CodeClass`
  - `SelfMemory`
  - raiz e projeção estrutural de `KnowledgeSpace`, `Work`, `Section`, `Concept` e `Entity`
  - consultas estruturais de código e auditoria do autoestudo

## Mapa por domínio
- Chat transacional -> Postgres
- Contexto de chat e citações documentais -> Qdrant
- Knowledge space -> Postgres + Qdrant + Neo4j
- Autonomia operacional -> Postgres
- Self-study -> Postgres + Qdrant + Neo4j
- Governança de tráfego/custo -> Redis

## Dependências contextuais
### Provedor de embeddings
- `aembed_text()` e `aembed_texts()` são usados em memória, documentos, Qdrant recall e GraphRAG.
- Sem embeddings, vários fluxos caem para vetor zero ou deixam de recuperar resultado útil.

### LLM provider
- Necessário para:
  - extração de entidades/relações na consolidação
  - cálculo de `importance` em `GenerativeMemoryService`
  - síntese de `GraphRAGCore`
  - resumo de conversa em `RAGService.maybe_summarize()`
- Pode ser local ou cloud conforme a política de roteamento.

### Ollama
- Atua como opção de inferência local.
- É dependência contextual, não obrigatória para todas as rotas.

### OpenAI, Gemini, DeepSeek, xAI, OpenRouter
- São dependências contextuais do plano de inferência.
- O papel exato depende do roteamento do LLM e do provider configurado.

### LangSmith
- Dependência opcional de tracing.

### Firebase
- Dependência opcional por feature flag.

## Impacto de falha por dependência
### Postgres falha
- O boot do `janus-api` deixa de ficar saudável no deploy atual.
- Chat persistido, identidade, autonomia, manifests, knowledge spaces, outbox e quotas diárias deixam de ter fonte de verdade.
- O `graph_orchestrator` pode degradar para `MemorySaver`, mas isso não substitui a perda do SQL do produto.

### Redis falha
- O backend pode continuar servindo requests, dependendo do modo fail-open/fail-closed.
- Rate limit, hot-reload distribuído e quotas temporárias/spend perdem consistência.
- Dados persistidos em Postgres, Qdrant e Neo4j não desaparecem.

### Qdrant falha
- `MemoryCore` entra em comportamento degradado/offline.
- O recall do chat via `RAGService.retrieve_context()` deixa de enriquecer o prompt.
- `MemoryService.index_interaction()` perde persistência das mensagens do chat.
- Citações e contexto de documentos deixam de ser recuperáveis.
- O `KnowledgeConsolidator` não consegue ler a coleção episódica.

### Neo4j falha
- `GraphDatabase` pode entrar em modo offline.
- Consultas retornam vazio e parte das execuções vira no-op em vez de erro explícito.
- Indexação estrutural do codebase falha.
- Persistência de entidades, relações e `SelfMemory` fica indisponível.
- Consultas estruturais de código e auditoria do autoestudo degradam.

### Embeddings falham
- Memória e documentos podem ser gravados com vetor zero ou deixar de ranquear corretamente.
- Recall semântico perde qualidade.
- GraphRAG e busca vetorial em geral degradam fortemente.

### LLM falha
- Consolidação para Neo4j deixa de gerar entidades/relações úteis.
- `importance` cai para defaults.
- Resumo de conversa e síntese GraphRAG deixam de funcionar.

## Observações importantes do código
- `GraphDatabase._initialize_ontology()` cria índices vetoriais e full-text no Neo4j para labels como `Entity`, `Concept`, `Tool` e `Pattern`.
- `GraphRAGCore` procura por `janus_vector_index` e `janus_fulltext_index`, nomes que não são criados automaticamente nesse bootstrap.
- Portanto, Neo4j saudável não implica GraphRAG habilitado.
- Qdrant é a fonte dominante do chat normal; Neo4j é dominante para conhecimento estruturado e code graph.

## Arquivos-fonte
- `backend/app/config.py`
- `backend/app/core/kernel.py`
- `backend/app/db/graph.py`
- `backend/app/db/vector_store.py`
- `backend/app/core/memory/memory_core.py`
- `backend/app/core/memory/providers/qdrant_provider.py`
- `backend/app/core/memory/graph_rag_core.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/document_service.py`

## Riscos/Lacunas
- O sistema aparenta tolerar parte das falhas degradando silenciosamente para vazio/no-op, o que reduz previsibilidade operacional.
- Qdrant e Neo4j não são intercambiáveis no código atual; cada um sustenta um subconjunto diferente do comportamento cognitivo.
- Postgres também não é intercambiável com eles: ele segura o plano transacional e o estado de controle, não o plano semântico.
