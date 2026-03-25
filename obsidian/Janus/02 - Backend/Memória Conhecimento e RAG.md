---
tipo: dominio
dominio: backend
camada: conhecimento
fonte-de-verdade: codigo
status: ativo
---

# Memória Conhecimento e RAG

## Objetivo
Descrever como Janus armazena, indexa e recupera conhecimento.

## Responsabilidades
- Ligar Neo4j, Qdrant e memória operacional.
- Explicar indexação, consulta e consolidação.

## Entradas
- Código indexado.
- Mensagens e experiências.
- Documentos ingeridos.

## Saídas
- Recuperação semântica e estrutural.
- Estado de conhecimento para chat e autonomia.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[02 - Backend/Repositórios e Modelos]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Componentes
- `KnowledgeService`: fachada do grafo de conhecimento e indexação.
- `MemoryService`: memória de curto e longo prazo.
- `RAGService`: recuperação orientada ao chat.
- `knowledge_consolidator_worker`: consolida conhecimento em lote.
- `document_ingestion_worker`: processa ingestão assíncrona.

## Leitura operacional
- Neo4j guarda entidades, relações e auditoria do grafo.
- Qdrant sustenta recuperação vetorial e memória episódica.
- O serviço de conhecimento também cuida de auto-index de codebase.
- O backend possui reparos para `SelfMemory`, evidenciando manutenção estrutural do grafo.

## Arquivos-fonte
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
- A fronteira entre memória de produto, memória de operação e conhecimento de código é extensa.
- Falhas em Neo4j ou Qdrant degradam capacidades de contexto e explicabilidade.
