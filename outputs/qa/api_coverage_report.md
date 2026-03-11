# API Coverage Report (OQ-011)

- Generated at: `2026-03-11T21:14:45.067447+00:00`
- Source matrix mode: `api_inventory_fallback`
- Source matrix generated at: `2026-03-11T21:14:33.527126+00:00`

## Summary

- Total endpoints: `226`
- Covered endpoints: `27`
- Uncovered endpoints: `199`
- Coverage percent: `11.95%`
- Runtime validated endpoints: `6`
- Runtime failed endpoints: `0`
- Test referenced endpoints (no runtime smoke): `21`

## Target Tracking

- Expected endpoints (target): `229`
- Observed endpoints: `226`
- Target met: `False`
- Endpoint gap: `3`

## Coverage By Module

| Module | Total | Covered | Uncovered | Runtime PASS | Runtime FAIL | Test Ref | Coverage % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Admin | 1 | 0 | 1 | 0 | 0 | 0 | 0.0% |
| Agent | 1 | 0 | 1 | 0 | 0 | 0 | 0.0% |
| Assistant | 1 | 0 | 1 | 0 | 0 | 0 | 0.0% |
| Auth | 8 | 1 | 7 | 0 | 0 | 1 | 12.5% |
| Auto Analysis | 1 | 0 | 1 | 0 | 0 | 0 | 0.0% |
| Autonomy | 11 | 1 | 10 | 0 | 0 | 1 | 9.09% |
| AutonomyHistory | 3 | 0 | 3 | 0 | 0 | 0 | 0.0% |
| Chat | 11 | 5 | 6 | 0 | 0 | 5 | 45.45% |
| Collaboration | 11 | 0 | 11 | 0 | 0 | 0 | 0.0% |
| Collaboration - Workspace | 5 | 0 | 5 | 0 | 0 | 0 | 0.0% |
| Consents | 3 | 0 | 3 | 0 | 0 | 0 | 0.0% |
| Context | 6 | 0 | 6 | 0 | 0 | 0 | 0.0% |
| Deployment | 4 | 0 | 4 | 0 | 0 | 0 | 0.0% |
| Documents | 6 | 0 | 6 | 0 | 0 | 0 | 0.0% |
| Evaluation | 5 | 0 | 5 | 0 | 0 | 0 | 0.0% |
| Feedback | 7 | 0 | 7 | 0 | 0 | 0 | 0.0% |
| Knowledge | 21 | 3 | 18 | 2 | 0 | 1 | 14.29% |
| Learning | 12 | 0 | 12 | 0 | 0 | 0 | 0.0% |
| LLM | 12 | 0 | 12 | 0 | 0 | 0 | 0.0% |
| Meta-Agent | 6 | 1 | 5 | 0 | 0 | 1 | 16.67% |
| Observability | 22 | 1 | 21 | 0 | 0 | 1 | 4.55% |
| Optimization | 6 | 0 | 6 | 0 | 0 | 0 | 0.0% |
| PendingActions | 5 | 0 | 5 | 0 | 0 | 0 | 0.0% |
| Productivity | 11 | 3 | 8 | 0 | 0 | 3 | 27.27% |
| Profiles | 2 | 0 | 2 | 0 | 0 | 0 | 0.0% |
| RAG | 5 | 1 | 4 | 0 | 0 | 1 | 20.0% |
| Reflexion | 5 | 1 | 4 | 0 | 0 | 1 | 20.0% |
| Sandbox | 3 | 0 | 3 | 0 | 0 | 0 | 0.0% |
| System | 5 | 3 | 2 | 3 | 0 | 0 | 60.0% |
| Tasks | 6 | 0 | 6 | 0 | 0 | 0 | 0.0% |
| Tools | 8 | 3 | 5 | 0 | 0 | 3 | 37.5% |
| unknown | 4 | 1 | 3 | 1 | 0 | 0 | 25.0% |
| Users | 6 | 2 | 4 | 0 | 0 | 2 | 33.33% |
| Workers | 3 | 1 | 2 | 0 | 0 | 1 | 33.33% |

## Runtime Failures

- No runtime failures captured in smoke data.

## Uncovered Endpoints (top 150)

| Method | Path | Module | Operation Id |
|---|---|---|---|
| PATCH | `/api/v1/admin/config` | Admin | update_config_api_v1_admin_config_patch |
| POST | `/api/v1/agent/execute` | Agent | agent_execute_api_v1_agent_execute_post |
| POST | `/api/v1/assistant/execute` | Assistant | assistant_execute_api_v1_assistant_execute_post |
| POST | `/api/v1/auth/firebase/exchange` | Auth | firebase_exchange_api_v1_auth_firebase_exchange_post |
| GET | `/api/v1/auth/local/me` | Auth | local_me_api_v1_auth_local_me_get |
| POST | `/api/v1/auth/local/register` | Auth | local_register_api_v1_auth_local_register_post |
| POST | `/api/v1/auth/local/request-reset` | Auth | local_request_reset_api_v1_auth_local_request_reset_post |
| POST | `/api/v1/auth/local/reset` | Auth | local_reset_password_api_v1_auth_local_reset_post |
| POST | `/api/v1/auth/supabase/exchange` | Auth | supabase_exchange_api_v1_auth_supabase_exchange_post |
| POST | `/api/v1/auth/token` | Auth | issue_token_api_v1_auth_token_post |
| GET | `/api/v1/auto-analysis/health-check` | Auto Analysis | auto_analyze_api_v1_auto_analysis_health_check_get |
| GET | `/api/v1/autonomy/goals` | Autonomy | list_goals_api_v1_autonomy_goals_get |
| POST | `/api/v1/autonomy/goals` | Autonomy | create_goal_api_v1_autonomy_goals_post |
| DELETE | `/api/v1/autonomy/goals/{goal_id}` | Autonomy | delete_goal_api_v1_autonomy_goals__goal_id__delete |
| GET | `/api/v1/autonomy/goals/{goal_id}` | Autonomy | get_goal_api_v1_autonomy_goals__goal_id__get |
| PATCH | `/api/v1/autonomy/goals/{goal_id}/status` | Autonomy | update_goal_status_api_v1_autonomy_goals__goal_id__status_patch |
| GET | `/api/v1/autonomy/plan` | Autonomy | get_autonomy_plan_api_v1_autonomy_plan_get |
| PUT | `/api/v1/autonomy/plan` | Autonomy | update_autonomy_plan_api_v1_autonomy_plan_put |
| PUT | `/api/v1/autonomy/policy` | Autonomy | update_policy_api_v1_autonomy_policy_put |
| GET | `/api/v1/autonomy/status` | Autonomy | autonomy_status_api_v1_autonomy_status_get |
| POST | `/api/v1/autonomy/stop` | Autonomy | stop_autonomy_api_v1_autonomy_stop_post |
| GET | `/api/v1/autonomy/history/runs` | AutonomyHistory | list_runs_api_v1_autonomy_history_runs_get |
| GET | `/api/v1/autonomy/history/runs/{run_id}` | AutonomyHistory | get_run_api_v1_autonomy_history_runs__run_id__get |
| GET | `/api/v1/autonomy/history/runs/{run_id}/steps` | AutonomyHistory | list_steps_api_v1_autonomy_history_runs__run_id__steps_get |
| GET | `/api/v1/chat/conversations` | Chat | list_conversations_api_v1_chat_conversations_get |
| GET | `/api/v1/chat/{conversation_id}/events` | Chat | stream_agent_events_api_v1_chat__conversation_id__events_get |
| GET | `/api/v1/chat/{conversation_id}/history` | Chat | chat_history_api_v1_chat__conversation_id__history_get |
| GET | `/api/v1/chat/{conversation_id}/history/paginated` | Chat | chat_history_paginated_api_v1_chat__conversation_id__history_paginated_get |
| PUT | `/api/v1/chat/{conversation_id}/rename` | Chat | rename_conversation_api_v1_chat__conversation_id__rename_put |
| GET | `/api/v1/chat/{conversation_id}/trace` | Chat | get_conversation_trace_api_v1_chat__conversation_id__trace_get |
| GET | `/api/v1/collaboration/agents` | Collaboration | list_agents_api_v1_collaboration_agents_get |
| POST | `/api/v1/collaboration/agents/create` | Collaboration | create_agent_api_v1_collaboration_agents_create_post |
| GET | `/api/v1/collaboration/agents/{agent_id}` | Collaboration | get_agent_details_api_v1_collaboration_agents__agent_id__get |
| GET | `/api/v1/collaboration/health` | Collaboration | health_check_api_v1_collaboration_health_get |
| POST | `/api/v1/collaboration/projects/execute` | Collaboration | execute_project_api_v1_collaboration_projects_execute_post |
| GET | `/api/v1/collaboration/tasks` | Collaboration | list_tasks_api_v1_collaboration_tasks_get |
| POST | `/api/v1/collaboration/tasks/create` | Collaboration | create_task_api_v1_collaboration_tasks_create_post |
| POST | `/api/v1/collaboration/tasks/execute` | Collaboration | execute_task_api_v1_collaboration_tasks_execute_post |
| POST | `/api/v1/collaboration/tasks/execute_parallel` | Collaboration | execute_tasks_parallel_api_v1_collaboration_tasks_execute_parallel_post |
| GET | `/api/v1/collaboration/tasks/{task_id}` | Collaboration | get_task_details_api_v1_collaboration_tasks__task_id__get |
| GET | `/api/v1/collaboration/workspace/status` | Collaboration | get_workspace_status_api_v1_collaboration_workspace_status_get |
| POST | `/api/v1/collaboration/system/shutdown` | Collaboration - Workspace | shutdown_system_api_v1_collaboration_system_shutdown_post |
| POST | `/api/v1/collaboration/workspace/artifacts/add` | Collaboration - Workspace | add_artifact_api_v1_collaboration_workspace_artifacts_add_post |
| GET | `/api/v1/collaboration/workspace/artifacts/{key}` | Collaboration - Workspace | get_artifact_api_v1_collaboration_workspace_artifacts__key__get |
| POST | `/api/v1/collaboration/workspace/messages/send` | Collaboration - Workspace | send_message_api_v1_collaboration_workspace_messages_send_post |
| GET | `/api/v1/collaboration/workspace/messages/{agent_id}` | Collaboration - Workspace | get_messages_for_api_v1_collaboration_workspace_messages__agent_id__get |
| GET | `/api/v1/consents/` | Consents | list_consents_api_v1_consents__get |
| POST | `/api/v1/consents/` | Consents | grant_consent_api_v1_consents__post |
| POST | `/api/v1/consents/{consent_id}/revoke` | Consents | revoke_consent_api_v1_consents__consent_id__revoke_post |
| GET | `/api/v1/context/current` | Context | get_current_context_api_v1_context_current_get |
| POST | `/api/v1/context/enriched` | Context | get_enriched_context_api_v1_context_enriched_post |
| GET | `/api/v1/context/format-prompt` | Context | format_context_for_prompt_api_v1_context_format_prompt_get |
| POST | `/api/v1/context/web-cache/invalidate` | Context | invalidate_web_cache_api_v1_context_web_cache_invalidate_post |
| GET | `/api/v1/context/web-cache/status` | Context | get_web_cache_status_api_v1_context_web_cache_status_get |
| GET | `/api/v1/context/web-search` | Context | search_web_api_v1_context_web_search_get |
| POST | `/api/v1/deployment/precheck` | Deployment | precheck_api_v1_deployment_precheck_post |
| POST | `/api/v1/deployment/publish` | Deployment | publish_api_v1_deployment_publish_post |
| POST | `/api/v1/deployment/rollback` | Deployment | rollback_api_v1_deployment_rollback_post |
| POST | `/api/v1/deployment/stage` | Deployment | stage_api_v1_deployment_stage_post |
| POST | `/api/v1/documents/link-url` | Documents | link_url_api_v1_documents_link_url_post |
| GET | `/api/v1/documents/list` | Documents | list_documents_api_v1_documents_list_get |
| GET | `/api/v1/documents/search` | Documents | search_documents_api_v1_documents_search_get |
| GET | `/api/v1/documents/status/{doc_id}` | Documents | document_status_api_v1_documents_status__doc_id__get |
| POST | `/api/v1/documents/upload` | Documents | upload_document_api_v1_documents_upload_post |
| DELETE | `/api/v1/documents/{doc_id}` | Documents | delete_document_api_v1_documents__doc_id__delete |
| GET | `/api/v1/evaluation/experiments` | Evaluation | list_experiments_api_v1_evaluation_experiments_get |
| POST | `/api/v1/evaluation/experiments` | Evaluation | create_experiment_api_v1_evaluation_experiments_post |
| POST | `/api/v1/evaluation/experiments/{experiment_id}/arms` | Evaluation | add_arm_api_v1_evaluation_experiments__experiment_id__arms_post |
| POST | `/api/v1/evaluation/experiments/{experiment_id}/results` | Evaluation | add_result_api_v1_evaluation_experiments__experiment_id__results_post |
| GET | `/api/v1/evaluation/experiments/{experiment_id}/winner` | Evaluation | experiment_winner_api_v1_evaluation_experiments__experiment_id__winner_get |
| POST | `/api/v1/feedback/` | Feedback | record_feedback_api_v1_feedback__post |
| GET | `/api/v1/feedback/conversation/{conversation_id}` | Feedback | get_conversation_feedback_api_v1_feedback_conversation__conversation_id__get |
| GET | `/api/v1/feedback/report` | Feedback | get_satisfaction_report_api_v1_feedback_report_get |
| GET | `/api/v1/feedback/stats` | Feedback | get_feedback_stats_api_v1_feedback_stats_get |
| GET | `/api/v1/feedback/suggestions` | Feedback | get_improvement_suggestions_api_v1_feedback_suggestions_get |
| POST | `/api/v1/feedback/thumbs-down` | Feedback | thumbs_down_api_v1_feedback_thumbs_down_post |
| POST | `/api/v1/feedback/thumbs-up` | Feedback | thumbs_up_api_v1_feedback_thumbs_up_post |
| GET | `/api/v1/knowledge/classes/implementations` | Knowledge | classes_implementations_api_v1_knowledge_classes_implementations_get |
| DELETE | `/api/v1/knowledge/clear` | Knowledge | clear_knowledge_graph_api_v1_knowledge_clear_delete |
| POST | `/api/v1/knowledge/concepts/reindex` | Knowledge | reindex_concepts_api_v1_knowledge_concepts_reindex_post |
| POST | `/api/v1/knowledge/concepts/related` | Knowledge | related_concepts_api_v1_knowledge_concepts_related_post |
| POST | `/api/v1/knowledge/consolidate` | Knowledge | publish_consolidation_api_v1_knowledge_consolidate_post |
| POST | `/api/v1/knowledge/consolidate/document` | Knowledge | consolidate_document_api_v1_knowledge_consolidate_document_post |
| GET | `/api/v1/knowledge/entities` | Knowledge | get_code_entities_api_v1_knowledge_entities_get |
| GET | `/api/v1/knowledge/entity/{entity_name}/relationships` | Knowledge | get_entity_relationships_api_v1_knowledge_entity__entity_name__relationships_get |
| GET | `/api/v1/knowledge/files/importing` | Knowledge | files_importing_api_v1_knowledge_files_importing_get |
| GET | `/api/v1/knowledge/functions/calling` | Knowledge | functions_calling_api_v1_knowledge_functions_calling_get |
| POST | `/api/v1/knowledge/health/reset-circuit-breaker` | Knowledge | reset_circuit_breaker_api_v1_knowledge_health_reset_circuit_breaker_post |
| POST | `/api/v1/knowledge/index` | Knowledge | trigger_indexing_api_v1_knowledge_index_post |
| GET | `/api/v1/knowledge/node-types` | Knowledge | get_node_types_api_v1_knowledge_node_types_get |
| GET | `/api/v1/knowledge/quarantine` | Knowledge | list_quarantine_api_v1_knowledge_quarantine_get |
| POST | `/api/v1/knowledge/quarantine/promote` | Knowledge | promote_quarantine_api_v1_knowledge_quarantine_promote_post |
| POST | `/api/v1/knowledge/query` | Knowledge | query_knowledge_api_v1_knowledge_query_post |
| POST | `/api/v1/knowledge/relationship-types/register` | Knowledge | register_relationship_type_api_v1_knowledge_relationship_types_register_post |
| GET | `/api/v1/knowledge/stats` | Knowledge | get_knowledge_stats_api_v1_knowledge_stats_get |
| GET | `/api/v1/learning/dataset/preview` | Learning | preview_dataset_api_v1_learning_dataset_preview_get |
| GET | `/api/v1/learning/dataset/version` | Learning | get_dataset_version_api_v1_learning_dataset_version_get |
| POST | `/api/v1/learning/evaluate` | Learning | evaluate_model_api_v1_learning_evaluate_post |
| GET | `/api/v1/learning/experiments` | Learning | list_experiments_api_v1_learning_experiments_get |
| GET | `/api/v1/learning/experiments/{experiment_id}` | Learning | get_experiment_details_api_v1_learning_experiments__experiment_id__get |
| POST | `/api/v1/learning/harvest` | Learning | trigger_harvesting_api_v1_learning_harvest_post |
| GET | `/api/v1/learning/health` | Learning | learning_health_api_v1_learning_health_get |
| GET | `/api/v1/learning/models` | Learning | list_models_api_v1_learning_models_get |
| GET | `/api/v1/learning/models/{model_id}` | Learning | get_model_details_api_v1_learning_models__model_id__get |
| GET | `/api/v1/learning/stats` | Learning | get_learning_stats_api_v1_learning_stats_get |
| POST | `/api/v1/learning/train` | Learning | trigger_training_api_v1_learning_train_post |
| GET | `/api/v1/learning/training/status` | Learning | get_training_status_api_v1_learning_training_status_get |
| POST | `/api/v1/llm/ab/set-experiment` | LLM | set_ab_experiment_api_v1_llm_ab_set_experiment_post |
| GET | `/api/v1/llm/budget/summary` | LLM | get_budget_summary_api_v1_llm_budget_summary_get |
| POST | `/api/v1/llm/cache/invalidate` | LLM | invalidate_llm_cache_api_v1_llm_cache_invalidate_post |
| GET | `/api/v1/llm/cache/status` | LLM | get_cache_status_api_v1_llm_cache_status_get |
| GET | `/api/v1/llm/circuit-breakers` | LLM | get_circuit_breaker_status_api_v1_llm_circuit_breakers_get |
| POST | `/api/v1/llm/circuit-breakers/{provider}/reset` | LLM | reset_circuit_breaker_api_v1_llm_circuit_breakers__provider__reset_post |
| GET | `/api/v1/llm/health` | LLM | llm_health_api_v1_llm_health_get |
| POST | `/api/v1/llm/invoke` | LLM | invoke_llm_api_v1_llm_invoke_post |
| GET | `/api/v1/llm/pricing/providers` | LLM | get_provider_pricing_api_v1_llm_pricing_providers_get |
| GET | `/api/v1/llm/providers` | LLM | list_llm_providers_api_v1_llm_providers_get |
| POST | `/api/v1/llm/response-cache/invalidate` | LLM | invalidate_response_cache_api_v1_llm_response_cache_invalidate_post |
| GET | `/api/v1/llm/response-cache/status` | LLM | get_response_cache_status_api_v1_llm_response_cache_status_get |
| POST | `/api/v1/meta-agent/analyze` | Meta-Agent | run_analysis_api_v1_meta_agent_analyze_post |
| GET | `/api/v1/meta-agent/health` | Meta-Agent | health_check_api_v1_meta_agent_health_get |
| POST | `/api/v1/meta-agent/heartbeat/start` | Meta-Agent | start_heartbeat_api_v1_meta_agent_heartbeat_start_post |
| POST | `/api/v1/meta-agent/heartbeat/stop` | Meta-Agent | stop_heartbeat_api_v1_meta_agent_heartbeat_stop_post |
| GET | `/api/v1/meta-agent/report/latest` | Meta-Agent | get_latest_report_api_v1_meta_agent_report_latest_get |
| GET | `/api/v1/observability/activity/user` | Observability | user_activity_api_v1_observability_activity_user_get |
| GET | `/api/v1/observability/audit/export` | Observability | export_audit_events_api_v1_observability_audit_export_get |
| GET | `/api/v1/observability/errors/taxonomy` | Observability | error_taxonomy_api_v1_observability_errors_taxonomy_get |
| GET | `/api/v1/observability/graph/audit` | Observability | graph_audit_api_v1_observability_graph_audit_get |
| GET | `/api/v1/observability/graph/quarantine` | Observability | graph_quarantine_list_api_v1_observability_graph_quarantine_get |
| POST | `/api/v1/observability/graph/quarantine/promote` | Observability | graph_quarantine_promote_api_v1_observability_graph_quarantine_promote_post |
| POST | `/api/v1/observability/health/check-all` | Observability | check_all_components_api_v1_observability_health_check_all_post |
| GET | `/api/v1/observability/health/components/llm_router` | Observability | health_llm_router_api_v1_observability_health_components_llm_router_get |
| GET | `/api/v1/observability/health/components/multi_agent_system` | Observability | health_multi_agent_api_v1_observability_health_components_multi_agent_system_get |
| GET | `/api/v1/observability/health/components/poison_pill_handler` | Observability | health_poison_pill_handler_api_v1_observability_health_components_poison_pill_handler_get |
| GET | `/api/v1/observability/health/system` | Observability | get_system_health_api_v1_observability_health_system_get |
| GET | `/api/v1/observability/llm/usage` | Observability | llm_usage_api_v1_observability_llm_usage_get |
| GET | `/api/v1/observability/metrics/summary` | Observability | get_metrics_summary_api_v1_observability_metrics_summary_get |
| GET | `/api/v1/observability/metrics/user` | Observability | user_metrics_api_v1_observability_metrics_user_get |
| POST | `/api/v1/observability/metrics/ux` | Observability | record_ux_metric_api_v1_observability_metrics_ux_post |
| POST | `/api/v1/observability/poison-pills/cleanup` | Observability | cleanup_quarantine_api_v1_observability_poison_pills_cleanup_post |
| GET | `/api/v1/observability/poison-pills/quarantined` | Observability | get_quarantined_messages_api_v1_observability_poison_pills_quarantined_get |
| POST | `/api/v1/observability/poison-pills/release` | Observability | release_from_quarantine_api_v1_observability_poison_pills_release_post |
| GET | `/api/v1/observability/poison-pills/stats` | Observability | get_poison_pill_stats_api_v1_observability_poison_pills_stats_get |
| GET | `/api/v1/observability/requests/{request_id}/dashboard` | Observability | request_pipeline_dashboard_api_v1_observability_requests__request_id__dashboard_get |
| GET | `/api/v1/observability/user_summary` | Observability | user_summary_api_v1_observability_user_summary_get |
| POST | `/api/v1/optimization/analyze` | Optimization | analyze_system_api_v1_optimization_analyze_post |
| GET | `/api/v1/optimization/health` | Optimization | get_system_health_api_v1_optimization_health_get |
| GET | `/api/v1/optimization/issues` | Optimization | get_detected_issues_api_v1_optimization_issues_get |
| GET | `/api/v1/optimization/metrics/history` | Optimization | get_metrics_history_api_v1_optimization_metrics_history_get |
| POST | `/api/v1/optimization/run-cycle` | Optimization | run_optimization_cycle_api_v1_optimization_run_cycle_post |

_Truncated: 49 additional uncovered endpoints not shown._
