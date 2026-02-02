# System Inventory & Tasks

This document contains detailed inventories of the system components, API routes, and task batches for technical improvements.

## 🧱 Task Batches (Levantamentos)

* [x] **Batch 1 — Boot & Kernel** (inventory closed)
* [x] **Batch 2 — API & Endpoints** (inventory closed)
* [ ] **Batch 3 — Services (LLM, Chat, RAG, Observability, Autonomy)** (inventory + corrections)
* [ ] **Batch 4 — Repositories and Persistence** (inventory + corrections)
* [ ] **Batch 5 — Agents, Tools and Sandbox** (inventory + corrections)
* [ ] **Batch 6 — TBD** (define scope)
* [ ] **Structural Infra — Processes & Resilience** (new)
  * [ ] **Separate planes**: move workers (Parliament, meta-agent, consolidator, auto-healer, autonomy) to own processes/containers; flags per environment to disable in dev/CI.
  * [ ] **Robust messaging**: guarantee effective DLX/DLQ and publish fail-fast (retry/backoff + alert) instead of silent drop when RabbitMQ is offline; health gating on dependent routes.
  * [ ] **Lightweight Startup**: remove heavy auto-index/warm-up from HTTP boot; make it opt-in via scheduled job and healthy readiness before serving traffic.
  * [ ] **Security by profile**: production mode with restricted CORS, mandatory API-Key/Bearer, and blocking of DANGEROUS tools outside allowlist; document dev vs prod profile.
  * [ ] **Worker supervision**: add monitor/restart/backoff for tasks created via `asyncio.create_task` (MAS actors, autonomy/lifecycle loops), avoiding silent failures.
  * [ ] **Resilient Broker**: complete DLX/DLQ configuration (fanout bindings) and replace silent drop with retry + alert when `_connection` is None; add dead-letter for all critical queues.
  * [ ] **Neo4j reconnect**: implement reconnect/health gating when the driver goes offline, avoiding getting stuck until restart.
  * [ ] **Duplicate metrics**: fix duplicate counters in `productivity.py` (repeated declaration of `_PROD_REQUESTS_TOTAL`/noop), ensuring unique names and consistent exports.
  * [ ] **Dangerous Tools**: reinforce policy for `execute_shell`/`write_file .py` (require explicit allowlist per environment and log/audit) to avoid inadvertent use in production.
  * [ ] **Secure Endpoints**: create "prod" profile with restricted CORS and mandatory authentication (API-Key/Bearer) and consistent sanitization of free payloads (prompts/URLs/markdown) before processing.
  * [ ] **Scheduled Warm-up/index**: move LLM warm-up and auto-indexing to opt-in asynchronous jobs (scheduler), maintaining healthy readiness in HTTP.

---

## 📎 Detailed Inventories (Annexes)

### ✅ Batch 1 — Boot & Kernel (CLOSED)

**Scope covered**: application lifecycle (lifespan), Kernel initialization, critical infrastructure, manual DI, warm-up, auto-indexing, workers, and shutdown.

**Completed Deliverables**:

1) **Startup Flow Map (textual pipeline and criticality)**
   - FastAPI Lifespan initializes the Kernel and maps services in `app.state` compatible with old routes.
   - The Kernel executes: infrastructure → MAS agents → DI → OS tools → workers → auto-index → warm-up → senses.
   - Critical steps (failures interrupt): infrastructure and MAS agents; "best-effort" steps: workers, warm-up, voice.

2) **Infra Inventory and Operational Impact**
   - Infra initialized in parallel: GraphDB (Neo4j), MemoryDB (Qdrant), Broker (RabbitMQ), Redis.
   - Firebase is optional and does not block boot (non-critical failure).

3) **Coupling Analysis (Manual DI)**
   - Kernel concentrates the creation of repositories and services, increasing coupling and hindering isolated testing.
   - The injection flow is "eager" and not lazy, raising startup cost.

4) **Workers and Scheduler**
   - Workers start globally (consolidator, harvester, lifecycle, meta-agent, scheduler, neural training).
   - No global flags to disable per environment, raising cost in dev/CI.

5) **Warm-up and Auto-indexing**
   - `AUTO_INDEX_ON_STARTUP=True` can cause high cost on large bases.
   - LLM warm-up in background is asynchronous, but still consumes resources at boot.

**Technical Recommendations (focusing on cost and performance)**

- [ ] Parallelize prompt loading (reduce cold start latency).
- [ ] Incremental indexing based on hash/commit (avoid unnecessary O(N)).
- [ ] Create feature flags for workers per environment (reduce operational cost).
- [ ] Introduce lightweight DI container (reduce coupling and improve testability).

---

### 🔍 Batch 2 — API & Endpoints (CLOSED)

**Objective**: map contracts, endpoints, validations, and performance impacts of the HTTP layer (FastAPI), including route governance and security.

#### Results (Core Rigor)

1) **Complete V1 Route Inventory**
   - Total (Full API): 212 unique routes; 65 with Pydantic request model; 2 with File/Form upload.
   - Routes defined but not exposed in v1 router: admin_graph, meta, resources.
   - Real duplications (same method/path): /optimization/* and /productivity/* (detail in inventory).
   - PUBLIC_API_MINIMAL mode exposed: /chat, /users, /profiles, /autonomy, /assistant, /autonomy/history, /consents, /pending_actions, /evaluation, /deployment, /auth, /auto-analysis, /feedback.

#### Full Route Inventory (Full API)
Note: listed paths already include the `/api/v1` prefix.

##### /admin
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| PATCH | /api/v1/admin/config | admin_config.update_config | ConfigUpdateRequest | ConfigUpdateResponse | ConfigService | no |

##### /agent
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/agent/execute | agent.agent_execute | AgentExecutionRequest | AgentResponse | AgentService | no |

##### /assistant
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/assistant/execute | assistant.assistant_execute | AssistantExecuteRequest | AssistantExecutionResult | AssistantService | no |

##### /auth
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/auth/supabase/exchange | auth.supabase_exchange | SupabaseExchangeRequest | TokenResponse | UserRepository | no |
| POST | /api/v1/auth/token | auth.issue_token | TokenRequest | TokenResponse | UserRepository | no |

##### /auto-analysis
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/auto-analysis/health-check | auto_analysis.auto_analyze | query/path | AutoAnalysisResponse | LLMRepository, LLMService, ObservabilityService | no |

##### /autonomy
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/autonomy/goals | autonomy.list_goals | query/path | list[GoalResponse] | GoalManager | no |
| POST | /api/v1/autonomy/goals | autonomy.create_goal | GoalCreateRequest | GoalResponse | GoalManager | no |
| DELETE | /api/v1/autonomy/goals/{goal_id} | autonomy.delete_goal | query/path | raw/dict | GoalManager | no |
| GET | /api/v1/autonomy/goals/{goal_id} | autonomy.get_goal | query/path | GoalResponse | GoalManager | no |
| PATCH | /api/v1/autonomy/goals/{goal_id}/status | autonomy.update_goal_status | GoalStatusUpdateRequest | GoalResponse | GoalManager | no |
| GET | /api/v1/autonomy/history/runs | autonomy_history.list_runs | query/path | list[RunSummary] | AutonomyRepository | no |
| GET | /api/v1/autonomy/history/runs/{run_id} | autonomy_history.get_run | query/path | RunSummary | AutonomyRepository | no |
| GET | /api/v1/autonomy/history/runs/{run_id}/steps | autonomy_history.list_steps | query/path | list[StepItem] | AutonomyRepository | no |
| GET | /api/v1/autonomy/plan | autonomy.get_autonomy_plan | query/path | raw/dict | AutonomyService | no |
| PUT | /api/v1/autonomy/plan | autonomy.update_autonomy_plan | PlanUpdateRequest | raw/dict | AutonomyService | no |
| PUT | /api/v1/autonomy/policy | autonomy.update_policy | PolicyUpdateRequest | raw/dict | AutonomyService | no |
| POST | /api/v1/autonomy/start | autonomy.start_autonomy | AutonomyStartRequest | raw/dict | AutonomyService | no |
| GET | /api/v1/autonomy/status | autonomy.autonomy_status | query/path | AutonomyStatusResponse | AutonomyService | no |
| POST | /api/v1/autonomy/stop | autonomy.stop_autonomy | query/path | raw/dict | AutonomyService | no |

##### /chat
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/chat/conversations | chat.list_conversations | query/path | list[ChatListResponse] | ChatService | no |
| GET | /api/v1/chat/health | chat.chat_health | query/path | raw/dict | ChatService | no |
| POST | /api/v1/chat/message | chat.send_message | ChatMessageRequest | ChatMessageResponse | ChatService, MemoryService | no |
| POST | /api/v1/chat/start | chat.start_chat | ChatStartRequest | ChatStartResponse | ChatService | no |
| GET | /api/v1/chat/stream/{conversation_id} | chat.stream_message | query/path | raw/dict | ChatService | no |
| DELETE | /api/v1/chat/{conversation_id} | chat.delete_conversation | query/path | raw/dict | ChatService | no |
| GET | /api/v1/chat/{conversation_id}/events | chat.stream_agent_events | query/path | raw/dict | ChatService | no |
| GET | /api/v1/chat/{conversation_id}/history | chat.chat_history | query/path | ChatHistoryResponse | ChatService | no |
| GET | /api/v1/chat/{conversation_id}/history/paginated | chat.chat_history_paginated | query/path | ChatHistoryPaginatedResponse | ChatService | no |
| PUT | /api/v1/chat/{conversation_id}/rename | chat.rename_conversation | ChatRenameRequest | raw/dict | ChatService | no |

##### /collaboration
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/collaboration/agents | collaboration.list_agents | query/path | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/agents/create | collaboration.create_agent | CreateAgentRequest | CreateAgentResponse | CollaborationService | no |
| GET | /api/v1/collaboration/agents/{agent_id} | collaboration.get_agent_details | query/path | raw/dict | CollaborationService | no |
| GET | /api/v1/collaboration/health | collaboration.health_check | query/path | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/projects/execute | collaboration.execute_project | ExecuteProjectRequest | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/system/shutdown | workspace.shutdown_system | query/path | raw/dict | CollaborationService | no |
| GET | /api/v1/collaboration/tasks | collaboration.list_tasks | query/path | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/tasks/create | collaboration.create_task | CreateTaskRequest | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/tasks/execute | collaboration.execute_task | ExecuteTaskRequest | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/tasks/execute_parallel | collaboration.execute_tasks_parallel | ExecuteTasksParallelRequest | raw/dict | CollaborationService | no |
| GET | /api/v1/collaboration/tasks/{task_id} | collaboration.get_task_details | query/path | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/workspace/artifacts/add | workspace.add_artifact | AddArtifactRequest | raw/dict | CollaborationService | no |
| GET | /api/v1/collaboration/workspace/artifacts/{key} | workspace.get_artifact | query/path | raw/dict | CollaborationService | no |
| POST | /api/v1/collaboration/workspace/messages/send | workspace.send_message | SendMessageRequest | raw/dict | CollaborationService | no |
| GET | /api/v1/collaboration/workspace/messages/{agent_id} | workspace.get_messages_for | query/path | raw/dict | CollaborationService | no |
| GET | /api/v1/collaboration/workspace/status | collaboration.get_workspace_status | query/path | raw/dict | CollaborationService | no |

##### /consents
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/consents/ | consents.list_consents | query/path | list[ConsentResponse] | - | no |
| POST | /api/v1/consents/ | consents.grant_consent | ConsentRequest | ConsentResponse | - | no |
| POST | /api/v1/consents/{consent_id}/revoke | consents.revoke_consent | query/path | ConsentResponse | - | no |

##### /context
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/context/current | context.get_current_context | query/path | ContextInfo | ContextService | no |
| POST | /api/v1/context/enriched | context.get_enriched_context | EnrichedContextRequest | raw/dict | ContextService | no |
| GET | /api/v1/context/format-prompt | context.format_context_for_prompt | query/path | raw/dict | ContextService | no |
| POST | /api/v1/context/web-cache/invalidate | context.invalidate_web_cache | InvalidateCacheRequest | raw/dict | ContextService | no |
| GET | /api/v1/context/web-cache/status | context.get_web_cache_status | query/path | raw/dict | ContextService | no |
| GET | /api/v1/context/web-search | context.search_web | query/path | WebSearchResult | ContextService | no |

##### /deployment
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/deployment/precheck | deployment.precheck | query/path | raw/dict | DeploymentRepository | no |
| POST | /api/v1/deployment/publish | deployment.publish | query/path | raw/dict | DeploymentRepository | no |
| POST | /api/v1/deployment/rollback | deployment.rollback | query/path | raw/dict | DeploymentRepository | no |
| POST | /api/v1/deployment/stage | deployment.stage | StageRequest | raw/dict | DeploymentRepository | no |

##### /documents
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/documents/link-url | documents.link_url | Form | LinkUrlResponse | DocumentIngestionService | no |
| GET | /api/v1/documents/list | documents.list_documents | query/path | DocListResponse | - | no |
| GET | /api/v1/documents/search | documents.search_documents | query/path | DocSearchResponse | - | no |
| GET | /api/v1/documents/status/{doc_id} | documents.document_status | query/path | DocStatusResponse | - | no |
| POST | /api/v1/documents/upload | documents.upload_document | File, Form | UploadResponse | DocumentIngestionService, KnowledgeService | no |
| DELETE | /api/v1/documents/{doc_id} | documents.delete_document | query/path | raw/dict | - | no |

##### /evaluation
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/evaluation/experiments | evaluation.list_experiments | query/path | list[ExperimentResponse] | ABExperimentRepository | no |
| POST | /api/v1/evaluation/experiments | evaluation.create_experiment | ExperimentCreateRequest | ExperimentResponse | ABExperimentRepository | no |
| POST | /api/v1/evaluation/experiments/{experiment_id}/arms | evaluation.add_arm | ArmCreateRequest | ArmResponse | ABExperimentRepository | no |
| POST | /api/v1/evaluation/experiments/{experiment_id}/results | evaluation.add_result | ResultCreateRequest | raw/dict | ABExperimentRepository | no |
| GET | /api/v1/evaluation/experiments/{experiment_id}/winner | evaluation.experiment_winner | query/path | raw/dict | - | no |

##### /feedback
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/feedback/ | feedback.record_feedback | FeedbackRequest | FeedbackResponse | - | no |
| GET | /api/v1/feedback/conversation/{conversation_id} | feedback.get_conversation_feedback | query/path | raw/dict | - | no |
| GET | /api/v1/feedback/report | feedback.get_satisfaction_report | query/path | SatisfactionReportResponse | - | no |
| GET | /api/v1/feedback/stats | feedback.get_feedback_stats | query/path | FeedbackStatsResponse | - | no |
| GET | /api/v1/feedback/suggestions | feedback.get_improvement_suggestions | query/path | raw/dict | - | no |
| POST | /api/v1/feedback/thumbs-down | feedback.thumbs_down | QuickFeedbackRequest | FeedbackResponse | - | no |
| POST | /api/v1/feedback/thumbs-up | feedback.thumbs_up | QuickFeedbackRequest | FeedbackResponse | - | no |

##### /knowledge
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/knowledge/classes/implementations | knowledge.classes_implementations | query/path | list[CodeEntity] | KnowledgeService | no |
| DELETE | /api/v1/knowledge/clear | knowledge.clear_knowledge_graph | query/path | ClearGraphResponse | KnowledgeService | no |
| POST | /api/v1/knowledge/concepts/reindex | knowledge.reindex_concepts | ReindexRequest | ReindexResponse | KnowledgeService | no |
| POST | /api/v1/knowledge/concepts/related | knowledge.related_concepts | RelatedConceptsRequest | RelatedConceptsResponse | KnowledgeService | no |
| POST | /api/v1/knowledge/consolidate | knowledge.publish_consolidation | ConsolidationRequest | ConsolidationResponse | - | no |
| POST | /api/v1/knowledge/consolidate/document | knowledge.consolidate_document | DocConsolidationRequest | ConsolidationResponse | KnowledgeService | no |
| GET | /api/v1/knowledge/entities | knowledge.get_code_entities | query/path | list[CodeEntity] | KnowledgeService | no |
| GET | /api/v1/knowledge/entity/{entity_name}/relationships | knowledge.get_entity_relationships | query/path | EntityRelationshipsResponse | KnowledgeService | no |
| GET | /api/v1/knowledge/files/importing | knowledge.files_importing | query/path | list[CodeEntity] | KnowledgeService | no |
| GET | /api/v1/knowledge/functions/calling | knowledge.functions_calling | query/path | list[CodeEntity] | KnowledgeService | no |
| GET | /api/v1/knowledge/health | knowledge.knowledge_health | query/path | KnowledgeHealthResponse | KnowledgeService | no |
| GET | /api/v1/knowledge/health/detailed | knowledge.detailed_health_check | query/path | raw/dict | KnowledgeService | no |
| POST | /api/v1/knowledge/health/reset-circuit-breaker | knowledge.reset_circuit_breaker | query/path | raw/dict | - | no |
| POST | /api/v1/knowledge/index | knowledge.trigger_indexing | query/path | IndexResponse | KnowledgeService | no |
| GET | /api/v1/knowledge/node-types | knowledge.get_node_types | query/path | NodeTypesResponse | KnowledgeService | no |
| GET | /api/v1/knowledge/quarantine | knowledge.list_quarantine | query/path | QuarantineListResponse | KnowledgeService | no |
| POST | /api/v1/knowledge/quarantine/promote | knowledge.promote_quarantine | PromoteQuarantineRequest | PromoteQuarantineResponse | KnowledgeService | no |
| POST | /api/v1/knowledge/query | knowledge.query_knowledge | KnowledgeQueryRequest | KnowledgeQueryResponse | KnowledgeService | no |
| POST | /api/v1/knowledge/relationship-types/register | knowledge.register_relationship_type | RegisterRelTypeRequest | RegisterRelTypeResponse | KnowledgeService | no |
| GET | /api/v1/knowledge/stats | knowledge.get_knowledge_stats | query/path | raw/dict | KnowledgeService | no |

##### /learning
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/learning/dataset/preview | learning.preview_dataset | query/path | raw/dict | LearningService | no |
| GET | /api/v1/learning/dataset/version | learning.get_dataset_version | query/path | DatasetVersionResponse | LearningService | no |
| POST | /api/v1/learning/evaluate | learning.evaluate_model | EvaluateRequest | EvaluationResponse | LearningService | no |
| GET | /api/v1/learning/experiments | learning.list_experiments | query/path | ExperimentListResponse | LearningService | no |
| GET | /api/v1/learning/experiments/{experiment_id} | learning.get_experiment_details | query/path | ExperimentInfo | LearningService | no |
| POST | /api/v1/learning/harvest | learning.trigger_harvesting | HarvestRequest | LearningResponse | LearningService | no |
| GET | /api/v1/learning/health | learning.learning_health | query/path | raw/dict | LearningService | no |
| GET | /api/v1/learning/models | learning.list_models | query/path | ModelListResponse | LearningService | no |
| GET | /api/v1/learning/models/{model_id} | learning.get_model_details | query/path | ModelInfo | LearningService | no |
| GET | /api/v1/learning/stats | learning.get_learning_stats | query/path | raw/dict | LearningService | no |
| POST | /api/v1/learning/train | learning.trigger_training | TrainRequest | TrainingAckResponse | LearningService | no |
| GET | /api/v1/learning/training/status | learning.get_training_status | query/path | TrainingStatusResponse | LearningService | no |

##### /llm
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/llm/ab/set-experiment | llm.set_ab_experiment | ABExperimentSetRequest | raw/dict | - | no |
| GET | /api/v1/llm/budget/summary | llm.get_budget_summary | query/path | raw/dict | - | no |
| POST | /api/v1/llm/cache/invalidate | llm.invalidate_llm_cache | query/path | raw/dict | LLMService | no |
| GET | /api/v1/llm/cache/status | llm.get_cache_status | query/path | LLMCacheStatusResponse | LLMService | no |
| GET | /api/v1/llm/circuit-breakers | llm.get_circuit_breaker_status | query/path | list[CircuitBreakerStatus] | LLMService | no |
| POST | /api/v1/llm/circuit-breakers/{provider}/reset | llm.reset_circuit_breaker | query/path | raw/dict | LLMService | no |
| GET | /api/v1/llm/health | llm.llm_health | query/path | raw/dict | LLMService | no |
| POST | /api/v1/llm/invoke | llm.invoke_llm | LLMInvokeRequest | LLMInvokeResponse | LLMService | no |
| GET | /api/v1/llm/pricing/providers | llm.get_provider_pricing | query/path | raw/dict | - | no |
| GET | /api/v1/llm/providers | llm.list_llm_providers | query/path | raw/dict | LLMService | no |
| POST | /api/v1/llm/response-cache/invalidate | llm.invalidate_response_cache | InvalidateResponseCacheRequest | raw/dict | LLMService | no |
| GET | /api/v1/llm/response-cache/status | llm.get_response_cache_status | query/path | LLMCacheStatusResponse | LLMService | no |

##### /memory
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/memory/generative | memory.get_generative_memories | query/path | list[ScoredExperience] | - | no |
| POST | /api/v1/memory/generative | memory.add_generative_memory | query/path | Experience | - | no |
| GET | /api/v1/memory/timeline | memory.get_memories_timeline | query/path | list[ScoredExperience] | MemoryService | no |

##### /meta-agent
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/meta-agent/analyze | meta_agent.run_analysis | query/path | raw/dict | MetaAgentService | no |
| GET | /api/v1/meta-agent/health | meta_agent.health_check | query/path | raw/dict | MetaAgentService | no |
| POST | /api/v1/meta-agent/heartbeat/start | meta_agent.start_heartbeat | StartHeartbeatRequest | raw/dict | MetaAgentService | no |
| GET | /api/v1/meta-agent/heartbeat/status | meta_agent.get_heartbeat_status | query/path | raw/dict | MetaAgentService | no |
| POST | /api/v1/meta-agent/heartbeat/stop | meta_agent.stop_heartbeat | query/path | raw/dict | MetaAgentService | no |
| GET | /api/v1/meta-agent/report/latest | meta_agent.get_latest_report | query/path | raw/dict | MetaAgentService | no |

##### /observability
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/observability/activity/user | observability.user_activity | query/path | UserActivityResponse | ObservabilityService | no |
| GET | /api/v1/observability/graph/audit | observability.graph_audit | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/graph/quarantine | observability.graph_quarantine_list | query/path | raw/dict | ObservabilityService | no |
| POST | /api/v1/observability/graph/quarantine/promote | observability.graph_quarantine_promote | PromoteQuarantineRequest | raw/dict | ObservabilityService | no |
| POST | /api/v1/observability/health/check-all | observability.check_all_components | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/health/components/llm_manager | observability.health_llm_manager | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/health/components/multi_agent_system | observability.health_multi_agent | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/health/components/poison_pill_handler | observability.health_poison_pill_handler | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/health/system | observability.get_system_health | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/llm/usage | observability.llm_usage | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/metrics/summary | observability.get_metrics_summary | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/metrics/user | observability.user_metrics | query/path | UserMetricsResponse | ObservabilityService | no |
| POST | /api/v1/observability/metrics/ux | observability.record_ux_metric | UxMetricItem | raw/dict | ObservabilityService | no |
| POST | /api/v1/observability/poison-pills/cleanup | observability.cleanup_quarantine | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/poison-pills/quarantined | observability.get_quarantined_messages | query/path | raw/dict | ObservabilityService | no |
| POST | /api/v1/observability/poison-pills/release | observability.release_from_quarantine | ReleaseQuarantineRequest | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/poison-pills/stats | observability.get_poison_pill_stats | query/path | raw/dict | ObservabilityService | no |
| GET | /api/v1/observability/user_summary | observability.user_summary | query/path | UserSummaryResponse | - | no |

##### /optimization
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/optimization/analyze | optimization.analyze_system | query/path | SystemAnalysisResponse | OptimizationService | yes |
| GET | /api/v1/optimization/health | optimization.get_system_health | query/path | SystemHealthResponse | OptimizationService | yes |
| GET | /api/v1/optimization/issues | optimization.get_detected_issues | query/path | list[DetectedIssueResponse] | OptimizationService | yes |
| GET | /api/v1/optimization/metrics/history | optimization.get_metrics_history | query/path | raw/dict | OptimizationService | yes |
| POST | /api/v1/optimization/run-cycle | optimization.run_optimization_cycle | OptimizationCycleRequest | OptimizationCycleResponse | OptimizationService | yes |
| GET | /api/v1/optimization/status | optimization.get_optimization_status | query/path | raw/dict | OptimizationService | yes |

##### /pending_actions
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/pending_actions/ | pending_actions.list_pending | query/path | List[PendingActionDTO] | - | no |
| POST | /api/v1/pending_actions/{thread_id}/approve | pending_actions.approve | query/path | PendingActionDTO | - | no |
| POST | /api/v1/pending_actions/{thread_id}/reject | pending_actions.reject | query/path | PendingActionDTO | - | no |

##### /productivity
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/productivity/calendar/events | productivity.calendar_list_events | query/path | raw/dict | ConsentRepository | yes |
| POST | /api/v1/productivity/calendar/events/add | productivity.calendar_add_event | CalendarAddRequest | raw/dict | ConsentRepository | yes |
| GET | /api/v1/productivity/limits/status | productivity.limits_status | query/path | raw/dict | - | yes |
| GET | /api/v1/productivity/mail/messages | productivity.mail_list | query/path | raw/dict | ConsentRepository | yes |
| POST | /api/v1/productivity/mail/messages/send | productivity.mail_send | MailSendRequest | raw/dict | ConsentRepository | yes |
| GET | /api/v1/productivity/notes | productivity.notes_list | query/path | raw/dict | ConsentRepository | yes |
| POST | /api/v1/productivity/notes/add | productivity.notes_add | NoteAddRequest | raw/dict | ConsentRepository | yes |
| POST | /api/v1/productivity/oauth/google/callback | productivity.google_oauth_callback, productivity.oauth_google_callback | GoogleOAuthCallbackRequest, OAuthCallbackRequest | raw/dict | - | yes |
| POST | /api/v1/productivity/oauth/google/refresh | productivity.google_oauth_refresh, productivity.oauth_google_refresh | OAuthRefreshRequest | raw/dict | - | yes |
| GET | /api/v1/productivity/oauth/google/start | productivity.google_oauth_start | query/path | raw/dict | - | yes |
| POST | /api/v1/productivity/oauth/google/start | productivity.oauth_google_start | OAuthStartRequest | raw/dict | - | yes |

##### /profiles
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/profiles/ | profiles.upsert_profile | UpsertProfileRequest | ProfileResponse | ProfileRepository | no |
| GET | /api/v1/profiles/{user_id} | profiles.get_profile | query/path | ProfileResponse | ProfileRepository | no |

##### /rag
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/rag/hybrid_search | rag.rag_hybrid_search | query/path | RAGHybridResponse | MemoryService | no |
| GET | /api/v1/rag/productivity | rag.rag_productivity_search | query/path | RAGProductivityResponse | - | no |
| GET | /api/v1/rag/search | rag.rag_search | query/path | RAGSearchResponse | MemoryService | no |
| GET | /api/v1/rag/user-chat | rag.rag_user_chat_search | query/path | RAGUserChatResponse | - | no |
| GET | /api/v1/rag/user_chat | rag.rag_user_chat_search_v2 | query/path | RAGUserChatResponseV2 | - | no |

##### /reflexion
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/reflexion/config | reflexion.get_reflexion_config | query/path | raw/dict | ReflexionService | no |
| POST | /api/v1/reflexion/execute | reflexion.execute_with_reflexion | ReflexionRequest | ReflexionResponse | ReflexionService | no |
| GET | /api/v1/reflexion/health | reflexion.reflexion_health | query/path | raw/dict | ReflexionService | no |
| POST | /api/v1/reflexion/reset-circuit-breaker | reflexion.reset_circuit_breaker | query/path | raw/dict | ReflexionService | no |
| GET | /api/v1/reflexion/summary/post_sprint | reflexion.get_post_sprint_summary | query/path | PostSprintSummaryResponse | MemoryService, MetaAgentService | no |

##### /sandbox
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/sandbox/capabilities | sandbox.get_sandbox_capabilities | query/path | raw/dict | SandboxService | no |
| POST | /api/v1/sandbox/evaluate | sandbox.evaluate_expression | ExpressionRequest | raw/dict | SandboxService | no |
| POST | /api/v1/sandbox/execute | sandbox.execute_code | CodeExecutionRequest | raw/dict | SandboxService | no |

##### /system
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/system/db/migrate | system_status.migrate_db_schema | query/path | raw/dict | - | no |
| GET | /api/v1/system/db/validate | system_status.validate_db_schema | query/path | raw/dict | - | no |
| GET | /api/v1/system/health/services | system_status.get_services_health | query/path | ServiceHealthResponse | KnowledgeService, LLMService, ObservabilityService, OptimizationService | no |
| GET | /api/v1/system/overview | system_overview.get_system_overview | query/path | SystemOverviewResponse | KnowledgeService, LLMService, ObservabilityService, OptimizationService | no |
| GET | /api/v1/system/status | system_status.get_system_status | query/path | StatusResponse | - | no |
| GET | /api/v1/system/status/user | system_status.get_user_status | query/path | UserStatusResponse | ObservabilityService | no |

##### /tasks
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/tasks/consolidation | tasks.create_consolidation_task | ConsolidationTaskRequest | TaskResponse | TaskService | no |
| GET | /api/v1/tasks/health/rabbitmq | tasks.check_rabbitmq_health | query/path | raw/dict | TaskService | no |
| GET | /api/v1/tasks/queue/{queue_name} | tasks.get_queue_info | query/path | QueueInfoResponse | TaskService | no |
| GET | /api/v1/tasks/queue/{queue_name}/policy | tasks.get_queue_policy | query/path | QueuePolicyResponse | TaskService | no |
| POST | /api/v1/tasks/queue/{queue_name}/policy/reconcile | tasks.reconcile_queue_policy | ReconcilePolicyRequest | ReconcilePolicyResponse | TaskService | no |
| GET | /api/v1/tasks/queue/{queue_name}/policy/validate | tasks.validate_queue_policy | query/path | QueuePolicyValidationResponse | TaskService | no |

##### /tools
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/tools/ | tools.list_tools | query/path | ToolListResponse | ToolService | no |
| GET | /api/v1/tools/categories/list | tools.list_categories | query/path | raw/dict | ToolService | no |
| POST | /api/v1/tools/create/from-api | tools.create_tool_from_api | CreateToolFromApiRequest | ToolInfo | ToolService | no |
| POST | /api/v1/tools/create/from-function | tools.create_tool_from_function | CreateToolFromFunctionRequest | ToolInfo | ToolService | no |
| GET | /api/v1/tools/permissions/list | tools.list_permissions | query/path | raw/dict | ToolService | no |
| GET | /api/v1/tools/stats/usage | tools.get_tool_statistics | query/path | ToolStatsResponse | ToolService | no |
| DELETE | /api/v1/tools/{tool_name} | tools.delete_tool | query/path | raw/dict | ToolService | no |
| GET | /api/v1/tools/{tool_name} | tools.get_tool_details | query/path | ToolInfo | ToolService | no |

##### /users
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/users/ | users.create_user | CreateUserRequest | UserResponse | UserRepository | no |
| GET | /api/v1/users/{user_id} | users.get_user | query/path | UserResponse | UserRepository | no |
| GET | /api/v1/users/{user_id}/consents | users.list_consents | query/path | raw/dict | ConsentRepository | no |
| POST | /api/v1/users/{user_id}/consents | users.add_consent | ConsentRequest | ConsentResponse | ConsentRepository | no |
| DELETE | /api/v1/users/{user_id}/consents/{scope} | users.revoke_consent | query/path | raw/dict | ConsentRepository | no |
| POST | /api/v1/users/{user_id}/roles | users.assign_role | AssignRoleRequest | raw/dict | UserRepository | no |

##### /workers
| Method | Path | Handler | Payload | Response | Services/Repos | Duplicate |
| --- | --- | --- | --- | --- | --- | --- |
| POST | /api/v1/workers/start-all | workers.start_workers | query/path | raw/dict | - | no |
| GET | /api/v1/workers/status | workers.workers_status | query/path | raw/dict | - | no |
| POST | /api/v1/workers/stop-all | workers.stop_workers | query/path | raw/dict | - | no |


2) **Contracts and Validations (Pydantic)**
   - models/schemas.py used only in memory (Experience, ScoredExperience) and tasks (QueueName); the rest defines local DTOs.
   - Free/sensitive inputs without clear limits:
     - /llm/invoke, /chat/message, /assistant/execute: prompt/message without max_length (risk of cost/abuse).
     - /tools/create/from-function: code without limit/syntax validation; /tools/create/from-api without URL/headers validation.
     - /sandbox/execute and /sandbox/evaluate: arbitrary code/expression (requires hard gate and limits).
     - /documents/upload: limited size, but without MIME/extension whitelist and no scan.
     - /tasks/consolidation: free metadata (dict) without strict schema.
     - /rag/* and /knowledge/*: free query; lack of sanitization and limits per user.
   - Positive point: Autonomy validates plan steps and AgentExecutionRequest has max_length.

3) **HTTP Performance and Middlewares**
   - Global middlewares: SecurityHeadersMiddleware, CorrelationMiddleware, RateLimitMiddleware, CORS, msgpack negotiation, Prometheus instrumentator.
   - RateLimit: token-bucket in Redis, fail-open if Redis falls; bypass only for /metrics, /healthz, /livez, /readyz.
   - msgpack negotiation does JSON decode/encode when Accept=application/msgpack; extra cost in large responses.
   - /system/overview and /system/health/services make sequential calls; can parallelize to reduce latency.
   - SSE (/chat/stream, /chat/{id}/events) does not pass through msgpack, OK.

4) **Governance and Versioning**
   - Routes outside /api/v1: /, /health, /healthz, /metrics, /static.
   - Endpoints with code, but not registered: admin_graph, meta, resources.
   - Duplication of include_router in /optimization and /productivity (duplicates routes and OpenAPI).
   - Naming inconsistency: /rag/user-chat vs /rag/user_chat; /pending_actions; /auto-analysis.

5) **API Security (Keys and Headers)**
   - X-API-Key is optional; when absent, entire API is exposed.
   - actor_user_id accepts X-User-Id without verification; allows impersonation if API key is shared.
   - Critical endpoints without auth/admin:
     /system/db/migrate, /system/db/validate, /workers/start-all, /workers/stop-all,
     /collaboration/system/shutdown, /sandbox/execute, /tools/create/*, /knowledge/clear,
     /knowledge/index, /observability/poison-pills/*, /optimization/analyze/run-cycle,
     /llm/ab/set-experiment, /llm/cache/*, /llm/response-cache/*, /tasks/queue/*/policy/reconcile.
   - Recommendation: separate admin routes, require JWT/role, remove X-User-Id fallback, apply allowlist per method.

6) **Cost Checklist for LLM Endpoints**
   - Core LLM has budgets, but user_id/project_id comes from payload; without authenticating identity, limits can be bypassed.
   - RateLimitMiddleware is per IP/API key, not per cost/tenant.
   - Chat/Assistant/Agent use LLM path; need to inherit authenticated identity for real cost.
   - /llm/budget/summary and /llm/pricing/providers exposed; ideal to restrict to admin.

#### Tasks

* [ ] Remove route duplications (/optimization/* and /productivity/*)
* [ ] Decide destination of routes not exposed in v1 router (admin_graph/meta/resources)
* [ ] Standardize route naming and stabilize compatibility (e.g., /rag/user-chat → /rag/user_chat)
* [ ] Define size limits for free inputs (prompt/message/code/query) per endpoint
* [ ] Validate URL/headers in /tools/create/from-api and impose limits in /tools/create/from-function
* [ ] Hard gate of critical endpoints with JWT/role (admin) and remove X-User-Id fallback
* [ ] Make X-API-Key mandatory when there is no JWT (remove default exposed mode)
* [ ] Restrict administrative cost and cache endpoints (/llm/budget/summary, /llm/pricing/providers, /llm/*cache*)
* [ ] Add MIME/extension allowlist and scan in /documents/upload
* [ ] Parallelize calls in /system/overview and /system/health/services
* [ ] Propagate budget enforcement (USD) to HTTP gateway per user/tenant

### Batch 3 - Services (LLM, Chat, RAG, Observability, Autonomy) (IN PROGRESS)

**Objective**: map the service layer and make explicit critical pending items in the heart of Janus.

#### Tasks

* [ ] Impose size limits in LLMService (prompt + output)
* [ ] Impose size limits in ChatService (message + attachments)
* [ ] Standardize cost registration/estimation in Chat → LLM path
* [ ] Validate conversation ownership in service and SQL repository
* [ ] Make user_id/project_id mandatory and server-side before RAG/LLM
* [ ] Persist ChatEventPublisher events (avoid silent db_logger=None)
* [ ] Expose degradation telemetry in RAG and summarization (explicit failure)
* [ ] Implement backoff, limits, and cancellation in AutonomyLoop
* [ ] Unify repository interfaces used by ChatService and RAGService
* [ ] Centralize identity resolution before calling LLM/RAG/Autonomy

### Batch 4 - Repositories and Persistence (IN PROGRESS)

**Objective**: map repositories, data sources, and persistence contracts, highlighting inconsistencies and technical debt.

#### Tasks

* [ ] Standardize Postgres session (100% async or dedicated sync engine)
* [ ] Fix calls to db.get_session_direct (non-existent method) in repositories
* [ ] Align ChatRepositorySQL with DB infra (avoid incompatible sync Session)
* [ ] Rewrite PromptRepository for coherent flow (async) or separate sync/async
* [ ] Persist collaboration/tool/optimization/context/sandbox repositories (avoid loss on restart)
* [ ] Persist learning stats/experiments (avoid partial loss)
* [ ] Remove or archive file-based chat_repository if not used
* [ ] Define consistency strategy between SQL, Qdrant, and Neo4j (without UoW)
* [ ] Add retries/timeouts and confirmation in cross-store deletions
* [ ] Type returns of Memory/Knowledge repos and standardize errors at repo level
* [ ] Finalize Alembic and guarantee migrations for new models (e.g., ModelDeployment)
* [ ] Remove db.create_tables from boot in production

### Batch 5 - Agents, Tools, and Sandbox (IN PROGRESS)

**Objective**: map agent orchestration, tool-calls, and sandbox, highlighting policy, execution, and isolation failures.

#### Tasks

* [ ] Apply PolicyEngine, rate limit, and confirmation in all chat tool-calls
* [ ] Ensure action_registry.record_call in tool-calls flow (complete telemetry)
* [ ] Fix ChatAgentLoop fallback (execute_tool_calls does not accept strict)
* [ ] Add timeout and concurrency limit per tool in ToolExecutorService
* [ ] Fix missing awaits in core/autonomy/planner.py (draft/critique/refine/replan/verify)
* [ ] Cover planner/autonomy with regression test (coroutine/await)
* [ ] Unify sandbox and integrate Docker executor into services flow
* [ ] Align SandboxService.get_capabilities with real enforcement (timeout/CPU/mem/output)
* [ ] Persist rate limit and stats per user/tenant (Redis/DB) and standardize HITL flow

### Next step after Batch 5
- Batch 6: TBD (define scope).
