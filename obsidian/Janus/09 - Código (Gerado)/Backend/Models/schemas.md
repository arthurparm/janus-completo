---
tipo: codigo
dominio: backend
camada: models
gerado: true
origem: "backend/app/models/schemas.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# schemas

## Arquivos-fonte
- `backend/app/models/schemas.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/memory.py`
- `backend/app/api/v1/endpoints/tasks.py`
- `backend/app/core/agents/agent_actor.py`
- `backend/app/core/agents/meta_agent_cycle.py`
- `backend/app/core/agents/multi_agent_system.py`
- `backend/app/core/infrastructure/message_broker.py`
- `backend/app/core/knowledge/distillation_service.py`
- `backend/app/core/memory/generative_memory.py`
- `backend/app/core/memory/local_cache.py`
- `backend/app/core/memory/memory_core.py`
- `backend/app/core/memory/providers/qdrant_provider.py`
- `backend/app/core/memory/working_memory.py`
- `backend/app/core/monitoring/auto_healer.py`
- `backend/app/core/monitoring/health_monitor.py`
- `backend/app/core/optimization/self_optimization.py`
- `backend/app/core/tools/sandbox_executor.py`
- `backend/app/core/workers/agent_tasks_worker.py`
- `backend/app/core/workers/async_consolidation_worker.py`
- `backend/app/core/workers/auto_scaler.py`
- `backend/app/core/workers/code_agent_worker.py`
- `backend/app/core/workers/codex_worker.py`
- `backend/app/core/workers/debate_critic_worker.py`
- `backend/app/core/workers/debate_proponent_worker.py`
- `backend/app/core/workers/distillation_worker.py`
- `backend/app/core/workers/document_ingestion_worker.py`
- `backend/app/core/workers/google_productivity_worker.py`
- `backend/app/core/workers/knowledge_consolidator_worker.py`
- `backend/app/core/workers/meta_agent_worker.py`
- `backend/app/core/workers/neural_training_system.py`
- `backend/app/core/workers/neural_training_worker.py`
- `backend/app/core/workers/professor_agent_worker.py`
- `backend/app/core/workers/red_team_agent_worker.py`
- `backend/app/core/workers/reflexion_worker.py`
- `backend/app/core/workers/router_worker.py`
- `backend/app/core/workers/sandbox_agent_worker.py`
- `backend/app/core/workers/thinker_agent_worker.py`
- `backend/app/db/graph.py`
- `backend/app/repositories/knowledge_repository.py`
- `backend/app/repositories/memory_repository.py`
- `backend/app/services/autonomy_admin_service.py`
- `backend/app/services/autonomy_service.py`
- `backend/app/services/collaboration_service.py`
- `backend/app/services/knowledge_graph_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/outbox_service.py`
- `backend/app/services/task_service.py`

## Símbolos
- class: `ExperienceMetadata`
- method: `ExperienceMetadata.get(self, key: str, default: Any | None = None)` -> `Any | None`
- method: `ExperienceMetadata.__getitem__(self, key: str)` -> `Any`
- class: `Experience`
  - Representa uma única experiência ou evento a ser memorizado.
- class: `ScoredExperience`
  - Experience enriquecida com score de similaridade/busca.
- class: `GraphLabel`
  - Labels para nós no Grafo de Conhecimento (Neo4j).
- class: `GraphRelationship`
  - Tipos de relacionamento no Grafo de Conhecimento (Neo4j).
- class: `VectorCollection`
  - Nomes das coleções no Banco de Dados Vetorial (Qdrant).
- class: `MemoryClass`
- class: `QueueName`
  - Nomes das filas no Message Broker (RabbitMQ).
- class: `EntityType`
  - Tipos de Entidade (reflete GraphLabel).
- class: `RelationType`
  - Tipos de Relacionamento (reflete GraphRelationship).
- class: `KnowledgeEntity`
  - Representa uma entidade extraída para o Knowledge Graph.
- class: `KnowledgeRelationship`
  - Representa um relacionamento extraído para o Knowledge Graph.
- class: `TaskMessage`
  - Representa uma mensagem de tarefa para o message broker.
- method: `TaskMessage.to_msgpack(self)` -> `bytes`
- method: `TaskMessage.from_msgpack(data: bytes)` -> `'TaskMessage'`
- class: `TaskStateEvent`
  - Evento de histórico de um TaskState.
- class: `SystemStatusResponse`
- class: `ServiceStatusResponse`
- class: `WorkerStatusResponse`
- class: `SystemOverviewResponse`
- class: `AgentPayload`
  - Payload estruturado para TaskState.
- class: `TaskState`
  - Objeto de colaboração rico compartilhado entre agentes.
- method: `TaskState.to_msgpack(self)` -> `bytes`
- method: `TaskState.from_msgpack(data: bytes)` -> `'TaskState'`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
