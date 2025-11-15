## Objetivo
- Entregar valor imediato com busca baseada em fatos pessoais, usando o que já existe (memória vetorial e Graph RAG), e evoluir para upload/parsing de PDFs/DOCX/HTML com enriquecimento no grafo.

## Estado Atual
- Memória vetorial pronta para ingestão/consulta textual via Qdrant, exposta por API.
- Recuperação híbrida e síntese via Graph RAG já disponível.
- Chunking robusto disponível no consolidator.
- Endpoints existentes: `POST /api/v1/memory/memorize` e variações de `recall`.

## Entregáveis do MVP (Valor Imediato)
1. Ingestão textual de documentos (conteúdo + metadados) usando o endpoint atual.
2. Chunking leve e indexação por usuário/origem, tipo `doc_chunk` com citações.
3. Endpoint de busca RAG mínima que combina memória vetorial com síntese simples e referências.
4. Filtros por `type`, `origin`, `doc_id` opcionais; latência e métricas básicas.

## Design Técnico do MVP
### Ingestão textual
- Usar `POST /api/v1/memory/memorize` para inserir o texto do documento.
- Metadados mínimos: `origin=user_id|project_id`, `type="doc_chunk"`, `doc_id`, `file_path` (quando houver), `section`/`chunk_index`.
- Onde: `janus/app/api/v1/endpoints/memory.py:29-46` (assinatura atual de ingestão).

### Chunking
- Aplicar chunking no cliente ou serviço antes do `memorize`, reaproveitando a lógica existente como referência.
- Função de referência para comportamento: `janus/app/core/workers/knowledge_consolidator_worker.py:134-152`.

### Indexação e metadados
- Persistência: `MemoryCore.amemorize` monta payload e faz upsert em Qdrant com criptografia opcional.
- Onde: `janus/app/core/memory/memory_core.py:85-156,159-170`.
- Campos úteis para filtros já suportados: `type`, `metadata.origin`, `ts_ms`. Planejar índice futuro para `metadata.doc_id`.

### Busca e resposta
- Consulta vetorial: `MemoryService.recall_experiences` e variantes.
- Onde: `janus/app/api/v1/endpoints/memory.py:48-63` (recall), `67-88` (recall filtrado), `100-116` (timeframe), `117-128` (falhas).
- Resposta RAG mínima: compor texto com trechos retornados + citações (`id`, `doc_id`, `file_path`). Para perguntas de conhecimento, opcionalmente `Graph RAG` via `query_knowledge_graph(...)`.
- Onde (Graph RAG): `janus/app/core/memory/graph_rag_core.py:179-254`.

### Segurança e cotas
- Reusar quotas por origem e PII masking.
- Onde: `janus/app/core/memory/memory_core.py:95-114` (cotas), `115-121` (PII), `135-147` (criptografia).

## Endpoint de Busca RAG (MVP)
- Novo endpoint leve: `GET /api/v1/rag/search` (sem upload) que:
  - Aceita `query`, `limit`, `min_score`, e filtros (`type`, `origin`, `doc_id` se já inserido em metadata).
  - Executa `MemoryService.recall_filtered` e sintetiza resposta curta com citações.
- Onde adicionar: `janus/app/api/v1/endpoints/knowledge.py` (ou novo `rag.py`) para focar em consulta/síntese sem alterar `memory.py`.

## Fase 2 — Upload de Arquivos (PDF/DOCX/HTML)
### Endpoints
- `POST /api/v1/docs/upload` com `UploadFile` + metadados (user/project, doc_id opcional).
- `GET /api/v1/docs/status/{doc_id}` para acompanhar ingestão assíncrona.

### Serviço de Ingestão
- `DocumentIngestionService`: extrai texto por tipo de arquivo, gera chunks, chama `MemoryService.add_experience` para cada chunk com `type="doc_chunk"` e metadados (`doc_id`, `file_path`, `page|section`).
- Parsing inicial:
  - PDF: `pdfminer.six` (se presente) ou fallback simples.
  - DOCX: `python-docx` (se presente).
  - HTML: `html.parser`/leitura básica, com limpeza.
- Observação: não presumir libs; detectar e usar quando disponíveis, senão armazenar conteúdo bruto enviado.

### Ingestão Assíncrona
- Worker leve que processa arquivos grandes em lote, registra métricas e erros.
- Reusar chunking e consolidator como referência.

### Índices e filtros adicionais
- Adicionar índices de payload para `metadata.doc_id` e `metadata.file_path` (utilitário existente suporta criação de índices adicionais).
- Onde: `janus/app/db/vector_store.py` (funções `get_or_create_collection`, `aget_or_create_collection`).

### Enriquecimento no Grafo
- Opcional: criar nós `Document` e relacionar trechos a entidades por `MENTIONS` durante consolidação.
- Reusar consolidator: `janus/app/core/workers/knowledge_consolidator_worker.py:248-470`.

## Critérios de Aceitação
- Inserção de textos/documentos com metadados por usuário/projeto.
- Busca retorna trechos relevantes com pontuação e citações.
- Latência aceitável (<2s para consultas com até 10 resultados, ambiente saudável).
- Logs/métricas de ingestão e busca visíveis.

## Métricas
- Vetorial: `memory_short_cache_*`, operações `qdrant_search` (latência) já instrumentadas.
- RAG: `rag_stage_latency_seconds`, `rag_events_total` (Graph RAG).
- Consolidação: `knowledge_consolidation_*`, `knowledge_relationships_created_total`.

## Impacto e Riscos
- Parsing de arquivos depende de libs externas; começar com texto direto garante valor imediato.
- Índices adicionais em Qdrant podem exigir manutenção em coleções existentes.
- Cotas e criptografia já mitigam riscos de carga/privacidade.

## Referências de Código
- Ingestão/recall (API): `janus/app/api/v1/endpoints/memory.py:29-46,48-63,67-88,100-128`.
- Memória vetorial/Qdrant: `janus/app/core/memory/memory_core.py:39-47,65-83,85-156,159-170,194-304,306-381`.
- Embeddings: `janus/app/core/embeddings/embedding_manager.py:63-92,123-160,163-185`.
- Graph RAG: `janus/app/core/memory/graph_rag_core.py:31-41,43-48,81-95,97-134,179-254`.
- Chunking de referência: `janus/app/core/workers/knowledge_consolidator_worker.py:134-152`. 
