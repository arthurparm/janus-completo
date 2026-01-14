# Plano de Implementação: Sistema de Memória Generativa (Park et al. 2023)

Este plano detalha a implementação de um sistema de memória para agentes generativos no Janus, integrando Recência, Importância e Relevância, com persistência em Neo4j e Qdrant.

## 1. Atualização dos Schemas de Dados
- **Arquivo**: `app/models/schemas.py`
- **Ação**: Adicionar campos de suporte à memória generativa no `ExperienceMetadata`.
    - `importance`: `float` (0.0 a 10.0) - Nível de importância da memória.
    - `last_accessed_at`: `datetime` - Última vez que a memória foi recuperada.
    - `access_count`: `int` - Frequência de acesso.
    - `pointer_id`: `str` - ID do nó correspondente no Neo4j (para sincronização).

## 2. Criação do Serviço de Memória Generativa
- **Arquivo**: `app/core/memory/generative_memory.py` (Novo)
- **Classe**: `GenerativeMemoryService`
- **Responsabilidades**:
    1.  **Orquestração**: Coordenar `MemoryCore` (Vetorial) e `GraphDatabase` (Semântico).
    2.  **Cálculo de Score**: Implementar a fórmula de recuperação:
        $$Score = (\alpha \cdot Recency) + (\beta \cdot Importance) + (\gamma \cdot Relevance)$$
        *Onde Recency é um decaimento exponencial baseada na última data de acesso.*
    3.  **Inserção de Memória**:
        - Calcular `Importance` usando LLM (se não fornecido).
        - Salvar vetor no Qdrant (via `MemoryCore`).
        - Criar nó `Experience` no Neo4j e conectar ao anterior (`NEXT`) para formar o "Memory Stream".
    4.  **Manutenção (Decaimento)**:
        - Método `prune_memories()`: Identificar e arquivar/remover memórias com baixo score composto (antigas + irrelevantes + baixa importância).

## 3. Integração com Neo4j (Memory Stream)
- **Arquivo**: `app/services/knowledge_graph_service.py`
- **Ação**: Adicionar método `create_experience_node`.
    - Criar nó `:Experience` com propriedades (`content`, `importance`, `timestamp`).
    - Criar relacionamento `:NEXT` a partir da última experiência do usuário/agente.
    - Garantir que a consolidação existente (`persist_extraction`) conecte as entidades extraídas a este nó de Experiência.

## 4. Prompt de Avaliação de Importância
- **Arquivo**: `app/prompts/modules/memory_rating.py` (Novo)
- **Conteúdo**: Prompt para o LLM avaliar a importância de uma memória de 1 a 10, considerando o contexto do agente.

## 5. Rotinas de Manutenção
- **Arquivo**: `app/core/workers/memory_maintenance_worker.py` (Novo ou integrado ao existente)
- **Ação**: Job periódico que chama `GenerativeMemoryService.prune_memories()`.

## Detalhes Técnicos da Recuperação
Ao buscar memórias (`retrieve_relevant_memories`):
1.  **Candidatos**: Buscar top-k por similaridade vetorial (Qdrant).
2.  **Re-ranking**: Para cada candidato, buscar metadados (importância, data) e recalcular o score final combinando os 3 fatores.
3.  **Side-effect**: Atualizar `last_accessed_at` das memórias retornadas (reforço).

## Critérios de Sucesso (Validação)
- [ ] Inserção de memória gera score de importância via LLM.
- [ ] Memórias são recuperadas ordenadas pelo score composto (não apenas similaridade).
- [ ] O "Memory Stream" é visível no Neo4j (cadeia de nós `Experience`).
- [ ] Memórias antigas e irrelevantes perdem prioridade na recuperação ao longo do tempo.
