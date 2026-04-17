# API Endpoint Matrix (Live)

- Generated at: `2026-04-14T19:18:26.958627+00:00`
- Source: `openapi_live`
- Regenerate command: `python tooling/generate_api_matrix.py`

## Summary

- Total endpoints: `247`
- Smoke results loaded: `6`
- Test path references: `249`

### By Method

| Method | Count |
|---|---:|
| DELETE | 6 |
| GET | 135 |
| PATCH | 2 |
| POST | 101 |
| PUT | 3 |

### By Module

| Module | Total | Smoke Pass | Smoke Fail | Referenced In Tests |
|---|---:|---:|---:|---:|
| Admin | 1 | 0 | 0 | 0 |
| Agent | 1 | 0 | 0 | 1 |
| Assistant | 1 | 0 | 0 | 1 |
| Auth | 8 | 0 | 0 | 8 |
| Auto Analysis | 1 | 0 | 0 | 0 |
| Autonomy | 11 | 0 | 0 | 11 |
| AutonomyAdmin | 9 | 0 | 0 | 1 |
| AutonomyHistory | 4 | 0 | 0 | 4 |
| Chat | 12 | 0 | 0 | 11 |
| Collaboration | 11 | 0 | 0 | 11 |
| Collaboration - Workspace | 5 | 0 | 0 | 3 |
| Context | 6 | 0 | 0 | 6 |
| Deployment | 4 | 0 | 0 | 0 |
| Documents | 6 | 0 | 0 | 6 |
| Evaluation | 5 | 0 | 0 | 0 |
| Feedback | 7 | 0 | 0 | 7 |
| Knowledge | 27 | 2 | 0 | 20 |
| Learning | 12 | 0 | 0 | 12 |
| LLM | 12 | 0 | 0 | 0 |
| Meta-Agent | 6 | 0 | 0 | 6 |
| Observability | 24 | 0 | 0 | 24 |
| Optimization | 6 | 0 | 0 | 0 |
| PendingActions | 5 | 0 | 0 | 5 |
| Productivity | 11 | 0 | 0 | 11 |
| Profiles | 2 | 0 | 0 | 2 |
| RAG | 5 | 0 | 0 | 5 |
| Reflexion | 5 | 0 | 0 | 5 |
| Sandbox | 3 | 0 | 0 | 3 |
| System | 5 | 3 | 0 | 5 |
| Tasks | 8 | 0 | 0 | 8 |
| Tools | 8 | 0 | 0 | 8 |
| unknown | 7 | 1 | 0 | 4 |
| Users | 6 | 0 | 0 | 6 |
| Workers | 3 | 0 | 0 | 1 |

## Endpoint Matrix

| Method | Path | Module | Smoke | In Tests |
|---|---|---|---|---|
| PATCH | `/api/v1/admin/config` | Admin | N/A | no |
| POST | `/api/v1/agent/execute` | Agent | N/A | yes |
| POST | `/api/v1/assistant/execute` | Assistant | N/A | yes |
| POST | `/api/v1/auth/firebase/exchange` | Auth | N/A | yes |
| POST | `/api/v1/auth/local/login` | Auth | N/A | yes |
| GET | `/api/v1/auth/local/me` | Auth | N/A | yes |
| POST | `/api/v1/auth/local/register` | Auth | N/A | yes |
| POST | `/api/v1/auth/local/request-reset` | Auth | N/A | yes |
| POST | `/api/v1/auth/local/reset` | Auth | N/A | yes |
| POST | `/api/v1/auth/supabase/exchange` | Auth | N/A | yes |
| POST | `/api/v1/auth/token` | Auth | N/A | yes |
| GET | `/api/v1/auto-analysis/health-check` | Auto Analysis | N/A | no |
| GET | `/api/v1/autonomy/goals` | Autonomy | N/A | yes |
| POST | `/api/v1/autonomy/goals` | Autonomy | N/A | yes |
| DELETE | `/api/v1/autonomy/goals/{goal_id}` | Autonomy | N/A | yes |
| GET | `/api/v1/autonomy/goals/{goal_id}` | Autonomy | N/A | yes |
| PATCH | `/api/v1/autonomy/goals/{goal_id}/status` | Autonomy | N/A | yes |
| GET | `/api/v1/autonomy/plan` | Autonomy | N/A | yes |
| PUT | `/api/v1/autonomy/plan` | Autonomy | N/A | yes |
| PUT | `/api/v1/autonomy/policy` | Autonomy | N/A | yes |
| POST | `/api/v1/autonomy/start` | Autonomy | N/A | yes |
| GET | `/api/v1/autonomy/status` | Autonomy | N/A | yes |
| POST | `/api/v1/autonomy/stop` | Autonomy | N/A | yes |
| POST | `/api/v1/autonomy/admin/backlog/sync` | AutonomyAdmin | N/A | yes |
| GET | `/api/v1/autonomy/admin/board` | AutonomyAdmin | N/A | no |
| POST | `/api/v1/autonomy/admin/code-qa` | AutonomyAdmin | N/A | no |
| GET | `/api/v1/autonomy/admin/self-study/neo4j-audit` | AutonomyAdmin | N/A | no |
| POST | `/api/v1/autonomy/admin/self-study/neo4j-repair` | AutonomyAdmin | N/A | no |
| POST | `/api/v1/autonomy/admin/self-study/run` | AutonomyAdmin | N/A | no |
| GET | `/api/v1/autonomy/admin/self-study/runs` | AutonomyAdmin | N/A | no |
| GET | `/api/v1/autonomy/admin/self-study/status` | AutonomyAdmin | N/A | no |
| POST | `/api/v1/autonomy/admin/self-study/trigger-on-goal-complete` | AutonomyAdmin | N/A | no |
| GET | `/api/v1/autonomy/history/runs` | AutonomyHistory | N/A | yes |
| GET | `/api/v1/autonomy/history/runs/{run_id}` | AutonomyHistory | N/A | yes |
| GET | `/api/v1/autonomy/history/runs/{run_id}/enqueues` | AutonomyHistory | N/A | yes |
| GET | `/api/v1/autonomy/history/runs/{run_id}/steps` | AutonomyHistory | N/A | yes |
| GET | `/api/v1/chat/conversations` | Chat | N/A | yes |
| GET | `/api/v1/chat/health` | Chat | N/A | yes |
| POST | `/api/v1/chat/message` | Chat | N/A | yes |
| POST | `/api/v1/chat/start` | Chat | N/A | yes |
| GET | `/api/v1/chat/stream/{conversation_id}` | Chat | N/A | yes |
| GET | `/api/v1/chat/study-jobs/{job_id}` | Chat | N/A | no |
| DELETE | `/api/v1/chat/{conversation_id}` | Chat | N/A | yes |
| GET | `/api/v1/chat/{conversation_id}/events` | Chat | N/A | yes |
| GET | `/api/v1/chat/{conversation_id}/history` | Chat | N/A | yes |
| GET | `/api/v1/chat/{conversation_id}/history/paginated` | Chat | N/A | yes |
| PUT | `/api/v1/chat/{conversation_id}/rename` | Chat | N/A | yes |
| GET | `/api/v1/chat/{conversation_id}/trace` | Chat | N/A | yes |
| GET | `/api/v1/collaboration/agents` | Collaboration | N/A | yes |
| POST | `/api/v1/collaboration/agents/create` | Collaboration | N/A | yes |
| GET | `/api/v1/collaboration/agents/{agent_id}` | Collaboration | N/A | yes |
| GET | `/api/v1/collaboration/health` | Collaboration | N/A | yes |
| POST | `/api/v1/collaboration/projects/execute` | Collaboration | N/A | yes |
| GET | `/api/v1/collaboration/tasks` | Collaboration | N/A | yes |
| POST | `/api/v1/collaboration/tasks/create` | Collaboration | N/A | yes |
| POST | `/api/v1/collaboration/tasks/execute` | Collaboration | N/A | yes |
| POST | `/api/v1/collaboration/tasks/execute_parallel` | Collaboration | N/A | yes |
| GET | `/api/v1/collaboration/tasks/{task_id}` | Collaboration | N/A | yes |
| GET | `/api/v1/collaboration/workspace/status` | Collaboration | N/A | yes |
| POST | `/api/v1/collaboration/system/shutdown` | Collaboration - Workspace | N/A | yes |
| POST | `/api/v1/collaboration/workspace/artifacts/add` | Collaboration - Workspace | N/A | yes |
| GET | `/api/v1/collaboration/workspace/artifacts/{key}` | Collaboration - Workspace | N/A | yes |
| POST | `/api/v1/collaboration/workspace/messages/send` | Collaboration - Workspace | N/A | no |
| GET | `/api/v1/collaboration/workspace/messages/{agent_id}` | Collaboration - Workspace | N/A | no |
| GET | `/api/v1/context/current` | Context | N/A | yes |
| POST | `/api/v1/context/enriched` | Context | N/A | yes |
| GET | `/api/v1/context/format-prompt` | Context | N/A | yes |
| POST | `/api/v1/context/web-cache/invalidate` | Context | N/A | yes |
| GET | `/api/v1/context/web-cache/status` | Context | N/A | yes |
| GET | `/api/v1/context/web-search` | Context | N/A | yes |
| POST | `/api/v1/deployment/precheck` | Deployment | N/A | no |
| POST | `/api/v1/deployment/publish` | Deployment | N/A | no |
| POST | `/api/v1/deployment/rollback` | Deployment | N/A | no |
| POST | `/api/v1/deployment/stage` | Deployment | N/A | no |
| POST | `/api/v1/documents/link-url` | Documents | N/A | yes |
| GET | `/api/v1/documents/list` | Documents | N/A | yes |
| GET | `/api/v1/documents/search` | Documents | N/A | yes |
| GET | `/api/v1/documents/status/{doc_id}` | Documents | N/A | yes |
| POST | `/api/v1/documents/upload` | Documents | N/A | yes |
| DELETE | `/api/v1/documents/{doc_id}` | Documents | N/A | yes |
| GET | `/api/v1/evaluation/experiments` | Evaluation | N/A | no |
| POST | `/api/v1/evaluation/experiments` | Evaluation | N/A | no |
| POST | `/api/v1/evaluation/experiments/{experiment_id}/arms` | Evaluation | N/A | no |
| POST | `/api/v1/evaluation/experiments/{experiment_id}/results` | Evaluation | N/A | no |
| GET | `/api/v1/evaluation/experiments/{experiment_id}/winner` | Evaluation | N/A | no |
| POST | `/api/v1/feedback/` | Feedback | N/A | yes |
| GET | `/api/v1/feedback/conversation/{conversation_id}` | Feedback | N/A | yes |
| GET | `/api/v1/feedback/report` | Feedback | N/A | yes |
| GET | `/api/v1/feedback/stats` | Feedback | N/A | yes |
| GET | `/api/v1/feedback/suggestions` | Feedback | N/A | yes |
| POST | `/api/v1/feedback/thumbs-down` | Feedback | N/A | yes |
| POST | `/api/v1/feedback/thumbs-up` | Feedback | N/A | yes |
| GET | `/api/v1/knowledge/classes/implementations` | Knowledge | N/A | no |
| DELETE | `/api/v1/knowledge/clear` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/concepts/reindex` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/concepts/related` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/consolidate` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/consolidate/document` | Knowledge | N/A | no |
| GET | `/api/v1/knowledge/entities` | Knowledge | N/A | yes |
| GET | `/api/v1/knowledge/entity/{entity_name}/relationships` | Knowledge | N/A | yes |
| GET | `/api/v1/knowledge/files/importing` | Knowledge | N/A | no |
| GET | `/api/v1/knowledge/functions/calling` | Knowledge | N/A | no |
| GET | `/api/v1/knowledge/health` | Knowledge | PASS (200) | yes |
| GET | `/api/v1/knowledge/health/detailed` | Knowledge | PASS (200) | yes |
| POST | `/api/v1/knowledge/health/reset-circuit-breaker` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/index` | Knowledge | N/A | yes |
| GET | `/api/v1/knowledge/node-types` | Knowledge | N/A | yes |
| GET | `/api/v1/knowledge/quarantine` | Knowledge | N/A | no |
| POST | `/api/v1/knowledge/quarantine/promote` | Knowledge | N/A | no |
| POST | `/api/v1/knowledge/query` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/query/code` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/relationship-types/register` | Knowledge | N/A | no |
| GET | `/api/v1/knowledge/spaces` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/spaces` | Knowledge | N/A | yes |
| GET | `/api/v1/knowledge/spaces/{knowledge_space_id}` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/spaces/{knowledge_space_id}/consolidate` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/spaces/{knowledge_space_id}/documents/{doc_id}/attach` | Knowledge | N/A | yes |
| POST | `/api/v1/knowledge/spaces/{knowledge_space_id}/query` | Knowledge | N/A | yes |
| GET | `/api/v1/knowledge/stats` | Knowledge | N/A | yes |
| POST | `/api/v1/llm/ab/set-experiment` | LLM | N/A | no |
| GET | `/api/v1/llm/budget/summary` | LLM | N/A | no |
| POST | `/api/v1/llm/cache/invalidate` | LLM | N/A | no |
| GET | `/api/v1/llm/cache/status` | LLM | N/A | no |
| GET | `/api/v1/llm/circuit-breakers` | LLM | N/A | no |
| POST | `/api/v1/llm/circuit-breakers/{provider}/reset` | LLM | N/A | no |
| GET | `/api/v1/llm/health` | LLM | N/A | no |
| POST | `/api/v1/llm/invoke` | LLM | N/A | no |
| GET | `/api/v1/llm/pricing/providers` | LLM | N/A | no |
| GET | `/api/v1/llm/providers` | LLM | N/A | no |
| POST | `/api/v1/llm/response-cache/invalidate` | LLM | N/A | no |
| GET | `/api/v1/llm/response-cache/status` | LLM | N/A | no |
| GET | `/api/v1/learning/dataset/preview` | Learning | N/A | yes |
| GET | `/api/v1/learning/dataset/version` | Learning | N/A | yes |
| POST | `/api/v1/learning/evaluate` | Learning | N/A | yes |
| GET | `/api/v1/learning/experiments` | Learning | N/A | yes |
| GET | `/api/v1/learning/experiments/{experiment_id}` | Learning | N/A | yes |
| POST | `/api/v1/learning/harvest` | Learning | N/A | yes |
| GET | `/api/v1/learning/health` | Learning | N/A | yes |
| GET | `/api/v1/learning/models` | Learning | N/A | yes |
| GET | `/api/v1/learning/models/{model_id}` | Learning | N/A | yes |
| GET | `/api/v1/learning/stats` | Learning | N/A | yes |
| POST | `/api/v1/learning/train` | Learning | N/A | yes |
| GET | `/api/v1/learning/training/status` | Learning | N/A | yes |
| POST | `/api/v1/meta-agent/analyze` | Meta-Agent | N/A | yes |
| GET | `/api/v1/meta-agent/health` | Meta-Agent | N/A | yes |
| POST | `/api/v1/meta-agent/heartbeat/start` | Meta-Agent | N/A | yes |
| GET | `/api/v1/meta-agent/heartbeat/status` | Meta-Agent | N/A | yes |
| POST | `/api/v1/meta-agent/heartbeat/stop` | Meta-Agent | N/A | yes |
| GET | `/api/v1/meta-agent/report/latest` | Meta-Agent | N/A | yes |
| GET | `/api/v1/observability/activity/user` | Observability | N/A | yes |
| GET | `/api/v1/observability/anomalies/predictive` | Observability | N/A | yes |
| GET | `/api/v1/observability/audit/events` | Observability | N/A | yes |
| GET | `/api/v1/observability/audit/export` | Observability | N/A | yes |
| GET | `/api/v1/observability/errors/taxonomy` | Observability | N/A | yes |
| GET | `/api/v1/observability/graph/audit` | Observability | N/A | yes |
| GET | `/api/v1/observability/graph/quarantine` | Observability | N/A | yes |
| POST | `/api/v1/observability/graph/quarantine/promote` | Observability | N/A | yes |
| POST | `/api/v1/observability/health/check-all` | Observability | N/A | yes |
| GET | `/api/v1/observability/health/components/llm_router` | Observability | N/A | yes |
| GET | `/api/v1/observability/health/components/multi_agent_system` | Observability | N/A | yes |
| GET | `/api/v1/observability/health/components/poison_pill_handler` | Observability | N/A | yes |
| GET | `/api/v1/observability/health/system` | Observability | N/A | yes |
| GET | `/api/v1/observability/llm/usage` | Observability | N/A | yes |
| GET | `/api/v1/observability/metrics/summary` | Observability | N/A | yes |
| GET | `/api/v1/observability/metrics/user` | Observability | N/A | yes |
| POST | `/api/v1/observability/metrics/ux` | Observability | N/A | yes |
| POST | `/api/v1/observability/poison-pills/cleanup` | Observability | N/A | yes |
| GET | `/api/v1/observability/poison-pills/quarantined` | Observability | N/A | yes |
| POST | `/api/v1/observability/poison-pills/release` | Observability | N/A | yes |
| GET | `/api/v1/observability/poison-pills/stats` | Observability | N/A | yes |
| GET | `/api/v1/observability/requests/{request_id}/dashboard` | Observability | N/A | yes |
| GET | `/api/v1/observability/slo/domains` | Observability | N/A | yes |
| GET | `/api/v1/observability/user_summary` | Observability | N/A | yes |
| POST | `/api/v1/optimization/analyze` | Optimization | N/A | no |
| GET | `/api/v1/optimization/health` | Optimization | N/A | no |
| GET | `/api/v1/optimization/issues` | Optimization | N/A | no |
| GET | `/api/v1/optimization/metrics/history` | Optimization | N/A | no |
| POST | `/api/v1/optimization/run-cycle` | Optimization | N/A | no |
| GET | `/api/v1/optimization/status` | Optimization | N/A | no |
| GET | `/api/v1/pending_actions/` | PendingActions | N/A | yes |
| POST | `/api/v1/pending_actions/action/{action_id}/approve` | PendingActions | N/A | yes |
| POST | `/api/v1/pending_actions/action/{action_id}/reject` | PendingActions | N/A | yes |
| POST | `/api/v1/pending_actions/{thread_id}/approve` | PendingActions | N/A | yes |
| POST | `/api/v1/pending_actions/{thread_id}/reject` | PendingActions | N/A | yes |
| GET | `/api/v1/productivity/calendar/events` | Productivity | N/A | yes |
| POST | `/api/v1/productivity/calendar/events/add` | Productivity | N/A | yes |
| GET | `/api/v1/productivity/limits/status` | Productivity | N/A | yes |
| GET | `/api/v1/productivity/mail/messages` | Productivity | N/A | yes |
| POST | `/api/v1/productivity/mail/messages/send` | Productivity | N/A | yes |
| GET | `/api/v1/productivity/notes` | Productivity | N/A | yes |
| POST | `/api/v1/productivity/notes/add` | Productivity | N/A | yes |
| POST | `/api/v1/productivity/oauth/google/callback` | Productivity | N/A | yes |
| POST | `/api/v1/productivity/oauth/google/refresh` | Productivity | N/A | yes |
| GET | `/api/v1/productivity/oauth/google/start` | Productivity | N/A | yes |
| POST | `/api/v1/productivity/oauth/google/start` | Productivity | N/A | yes |
| POST | `/api/v1/profiles/` | Profiles | N/A | yes |
| GET | `/api/v1/profiles/{user_id}` | Profiles | N/A | yes |
| GET | `/api/v1/rag/hybrid_search` | RAG | N/A | yes |
| GET | `/api/v1/rag/productivity` | RAG | N/A | yes |
| GET | `/api/v1/rag/search` | RAG | N/A | yes |
| GET | `/api/v1/rag/user-chat` | RAG | N/A | yes |
| GET | `/api/v1/rag/user_chat` | RAG | N/A | yes |
| GET | `/api/v1/reflexion/config` | Reflexion | N/A | yes |
| POST | `/api/v1/reflexion/execute` | Reflexion | N/A | yes |
| GET | `/api/v1/reflexion/health` | Reflexion | N/A | yes |
| POST | `/api/v1/reflexion/reset-circuit-breaker` | Reflexion | N/A | yes |
| GET | `/api/v1/reflexion/summary/post_sprint` | Reflexion | N/A | yes |
| GET | `/api/v1/sandbox/capabilities` | Sandbox | N/A | yes |
| POST | `/api/v1/sandbox/evaluate` | Sandbox | N/A | yes |
| POST | `/api/v1/sandbox/execute` | Sandbox | N/A | yes |
| POST | `/api/v1/system/db/migrate` | System | N/A | yes |
| GET | `/api/v1/system/db/validate` | System | PASS (200) | yes |
| GET | `/api/v1/system/health/services` | System | PASS (200) | yes |
| GET | `/api/v1/system/status` | System | PASS (200) | yes |
| GET | `/api/v1/system/status/user` | System | N/A | yes |
| POST | `/api/v1/tasks/consolidation` | Tasks | N/A | yes |
| GET | `/api/v1/tasks/health/rabbitmq` | Tasks | N/A | yes |
| POST | `/api/v1/tasks/outbox/reconcile` | Tasks | N/A | yes |
| GET | `/api/v1/tasks/outbox/stats` | Tasks | N/A | yes |
| GET | `/api/v1/tasks/queue/{queue_name}` | Tasks | N/A | yes |
| GET | `/api/v1/tasks/queue/{queue_name}/policy` | Tasks | N/A | yes |
| POST | `/api/v1/tasks/queue/{queue_name}/policy/reconcile` | Tasks | N/A | yes |
| GET | `/api/v1/tasks/queue/{queue_name}/policy/validate` | Tasks | N/A | yes |
| GET | `/api/v1/tools/` | Tools | N/A | yes |
| GET | `/api/v1/tools/categories/list` | Tools | N/A | yes |
| POST | `/api/v1/tools/create/from-api` | Tools | N/A | yes |
| POST | `/api/v1/tools/create/from-function` | Tools | N/A | yes |
| GET | `/api/v1/tools/permissions/list` | Tools | N/A | yes |
| GET | `/api/v1/tools/stats/usage` | Tools | N/A | yes |
| DELETE | `/api/v1/tools/{tool_name}` | Tools | N/A | yes |
| GET | `/api/v1/tools/{tool_name}` | Tools | N/A | yes |
| POST | `/api/v1/users/` | Users | N/A | yes |
| GET | `/api/v1/users/{user_id}` | Users | N/A | yes |
| GET | `/api/v1/users/{user_id}/consents` | Users | N/A | yes |
| POST | `/api/v1/users/{user_id}/consents` | Users | N/A | yes |
| DELETE | `/api/v1/users/{user_id}/consents/{scope}` | Users | N/A | yes |
| POST | `/api/v1/users/{user_id}/roles` | Users | N/A | yes |
| POST | `/api/v1/workers/start-all` | Workers | N/A | no |
| GET | `/api/v1/workers/status` | Workers | N/A | yes |
| POST | `/api/v1/workers/stop-all` | Workers | N/A | no |
| GET | `/api/v1/memory/generative` | unknown | N/A | no |
| POST | `/api/v1/memory/generative` | unknown | N/A | no |
| GET | `/api/v1/memory/preferences` | unknown | N/A | no |
| GET | `/api/v1/memory/secrets` | unknown | N/A | yes |
| POST | `/api/v1/memory/secrets` | unknown | N/A | yes |
| GET | `/api/v1/memory/timeline` | unknown | N/A | yes |
| GET | `/api/v1/system/overview` | unknown | PASS (200) | yes |
