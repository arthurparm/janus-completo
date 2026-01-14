# Implementação de Melhorias Arquiteturais no Janus

Este plano detalha a implementação das melhorias solicitadas no arquivo `Melhorias possiveis.md`, focando em modernizar a arquitetura de agentes, o pipeline RAG e o mecanismo de aprovação humana.

## 1. Preparação e Dependências

### 1.1 Atualizar `pyproject.toml`
- **Adicionar**:
  - `pydantic-ai`: Para workers type-safe.
  - `neo4j-graphrag`: Para pipeline RAG nativo.
- **Ação**: Atualizar o arquivo e garantir compatibilidade de versões.

## 2. Hybrid Agent Architecture (LangGraph + PydanticAI)

### 2.1 Criar Orquestrador com LangGraph
- **Novo Arquivo**: `janus/app/core/agents/graph_orchestrator.py`
- **Componentes**:
  - `AgentState`: TypedDict definindo o estado do grafo (mensagens, next_step, erros).
  - `SupervisorNode`: Agente roteador que decide qual worker chamar ou se finaliza.
  - `StateGraph`: Definição do fluxo de trabalho (Supervisor -> Worker -> Supervisor).
- **Integração**: Substituir a lógica manual de `MultiAgentSystem.execute_project` pela execução deste grafo.

### 2.2 Implementar Workers com PydanticAI
- **Novo Arquivo**: `janus/app/core/agents/leaf_worker.py`
- **Funcionalidade**:
  - Criar classes de agentes baseadas em `pydantic_ai.Agent`.
  - Definir ferramentas como funções tipadas com Pydantic, garantindo validação de entrada/saída.
  - Expor uma interface unificada para ser chamada pelos nós do LangGraph.

## 3. Native GraphRAG Pipelines

### 3.1 Refatorar `graph_rag_core.py`
- **Substituição**: Remover a lógica customizada de geração de Cypher (`_extract_cypher`, prompts manuais).
- **Implementação**:
  - Instanciar `Neo4jGraphRAG` (ou componentes equivalentes da biblioteca oficial).
  - Configurar retrievers para busca híbrida (vetorial + grafo).
  - Atualizar a função `query_knowledge_graph` para usar o novo pipeline.

## 4. Centralized HITL (Human-in-the-Loop)

### 4.1 Configurar Persistência (Checkpointers)
- **Backend**: Utilizar `PostgresSaver` do `langgraph.checkpoint.postgres` (usando a conexão existente do SQLAlchemy).
- **Configuração**: Adicionar o checkpointer ao `StateGraph` criado na etapa 2.

### 4.2 Implementar Interrupções
- **Lógica**: Configurar `interrupt_before=["human_approval"]` no grafo.
- **Fluxo**:
  1. Agente solicita ação sensível.
  2. Grafo pausa e salva estado no Postgres.
  3. API retorna ID da thread e status "aguardando aprovação".

### 4.3 Atualizar API de Aprovação
- **Refatoração**: Atualizar `pending_actions.py` (ou criar endpoints compatíveis) para:
  - Listar threads pausadas.
  - Retomar execução (`graph.stream(..., command="resume")`) após aprovação do usuário.

## 5. Testes e Validação

### 5.1 Testes Unitários
- Testar o fluxo do `StateGraph` (mocks para LLM).
- Testar validação de tipos dos workers PydanticAI.

### 5.2 Testes de Integração
- Validar conexão e queries com `neo4j-graphrag`.
- Simular fluxo completo de HITL: Pausa -> Persistência -> Aprovação -> Retomada.

### 5.3 Documentação
- Atualizar docstrings e gerar documentação da nova arquitetura.
