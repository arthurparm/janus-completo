---
tipo: fluxo
dominio: conhecimento
camada: end-to-end
fonte-de-verdade: codigo
status: ativo
---

# Documentos Conhecimento e Memória

## Objetivo
Explicar como conteúdo do usuário e do código vira contexto útil.

## Responsabilidades
- Cobrir ingestão, busca e uso em conversa.
- Relacionar documents, memory e RAG.

## Entradas
- Uploads e links de documentos.
- Memórias explícitas do usuário.
- Indexação do codebase.

## Saídas
- Resultados de busca.
- Contexto semântico para respostas.

## Dependências
- [[02 - Backend/Memória Conhecimento e RAG]]
- [[03 - Frontend/Features e Experiência]]

## Sequência
1. Usuário gerencia docs/memória a partir de `conversations`.
2. Frontend usa endpoints de documentos, memória e RAG.
3. Backend ingere, enriquece, indexa e relaciona conteúdo.
4. O chat consome esse material como citações e contexto recuperado.

## Arquivos-fonte
- `frontend/src/app/features/conversations/conversations.ts`
- `backend/app/api/v1/endpoints/documents.py`
- `backend/app/api/v1/endpoints/memory.py`
- `backend/app/api/v1/endpoints/rag.py`
- `backend/app/services/document_service.py`
- `backend/app/services/knowledge_service.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- O cockpit de conversa mistura CRUD e exploração de conhecimento em uma única tela.
