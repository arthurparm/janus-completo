---
tipo: dominio
dominio: backend
camada: conhecimento
fonte-de-verdade: codigo
status: ativo
---

# Memória Conhecimento e RAG

## Objetivo
Descrever os acoplamentos reais do chat com memória, grounding documental, knowledge space e RAG.

## Responsabilidades
- Explicar captura de memória a partir da conversa.
- Explicar recuperação de contexto, citações e consolidação pós-resposta.

## Entradas
- Código indexado.
- Mensagens e experiências.
- Documentos ingeridos.
- Manifestos de documentos ligados à conversa.

## Saídas
- Recuperação semântica e estrutural.
- `relevant_memories`, `citations`, `citation_status`, `knowledge_space_id`.
- Consolidação assíncrona de experiências de resposta.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[02 - Backend/Repositórios e Modelos]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Acoplamentos do chat
### Captura de memória ao receber a mensagem
- `MessageOrchestrationService.schedule_active_memory_capture()` chama `active_memory_service.maybe_capture_from_message()`.
- `active_memory_service` delega para `procedural_memory_service.maybe_capture_from_message()` para regras reutilizáveis.
- O REST agenda também `RAGService.maybe_index_message()` para a mensagem do usuário.

### Recuperação de contexto para resposta geral
- No REST, `MessageOrchestrationService` usa `get_knowledge_routing_policy().resolve(RouteIntent.CHAT_CONTEXT_RETRIEVAL, ...)` antes de `RAGService.retrieve_context()`.
- No SSE, `StreamingService` chama `RAGService.retrieve_context()` sem essa decisão explícita de rota.
- O prompt final recebe `relevant_memories` junto do histórico recente e do summary da conversa.

### Grounding documental e knowledge space
- `generate_document_grounded_reply()` primeiro tenta `KnowledgeSpaceService.query_space()` quando existe `knowledge_space_id` ativo ou dedutível a partir de `DocumentManifestRepository`.
- Se não houver knowledge space ativo, o serviço busca `collect_document_citations()` no Qdrant por `doc_chunk`.
- O fluxo aplica política de fonte principal/secundária e pode responder em modo operacional ou explicativo.
- Se só houver manifestos em `queued/processing`, a resposta vira placeholder de processamento.

### Citações do chat
- `collect_chat_citations()` combina:
  - documentos da conversa via Qdrant
  - hits da `MemoryService.recall_filtered()`
- `build_citation_status()` marca quando a citação é obrigatória ou opcional.
- Para mensagens sobre arquivo/código/doc, ausência de citação pode forçar `missing_required`.

### Fallback de estudo
- No REST, `missing_required` sem knowledge space pronto pode virar `delivery_status=pending_study`.
- O endpoint cria `ChatStudyJobService`, persiste placeholder e a UI passa a fazer polling em `/api/v1/chat/study-jobs/{job_id}`.
- `ChatStudyService` tenta:
  - conhecimento já indexado
  - documentos anexados
  - self-study / scan do repositório local
  - síntese final com citações rastreáveis

### Memórias especiais pós-resposta
- `generate_secret_recall_reply()` pode devolver segredo autorizado quando a mensagem libera esse tipo de recuperação.
- `apply_response_memory_policies()` lê `procedural_memory_service.list_rules()` e pode anexar fechamento com "Próximos passos".
- `trigger_post_response_events()` sempre tenta enfileirar consolidação da experiência via `OutboxService` ou `publish_consolidation_task()`.
- No REST, há também `RAGService.maybe_summarize()` após algumas respostas.

## Leitura operacional
- Qdrant é o backend visível no código de citações documentais do chat.
- O chat grounded em documento não usa "memória" como fonte principal; ele primeiro tenta knowledge space/manifests e depois vetores de documentos.
- O REST está mais acoplado ao ciclo completo de memória/RAG do que o SSE.

## Arquivos-fonte
- `backend/app/services/chat/message_orchestration_service.py`
- `backend/app/services/chat/chat_citation_service.py`
- `backend/app/services/chat_study_service.py`
- `backend/app/services/active_memory_service.py`
- `backend/app/services/procedural_memory_service.py`
- `backend/app/services/secret_memory_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/core/memory/*`
- `backend/app/db/graph.py`
- `backend/app/db/vector_store.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- REST e SSE não atualizam memória/RAG do mesmo jeito; isso cria deriva de contexto entre transportes.
- `ChatStudyJobService` é volátil em memória de processo.
- A resposta grounded depende de manifestos, vector store e às vezes de uma varredura local do repositório, o que mistura fontes operacionais distintas dentro do mesmo fluxo de chat.
- Falhas em Qdrant ou no mecanismo de memória degradam tanto citações quanto explicabilidade da resposta.
