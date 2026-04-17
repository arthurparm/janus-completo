# API Coverage Report (OQ-011)

- Generated at: `2026-04-14T19:18:22.550833+00:00`
- Source matrix mode: `openapi_live`
- Source matrix generated at: `2026-04-14T19:16:09.253038+00:00`

## Summary

- Total endpoints: `247`
- Covered endpoints: `195`
- Uncovered endpoints: `52`
- Coverage percent: `78.95%`
- Runtime validated endpoints: `6`
- Runtime failed endpoints: `0`
- Test referenced endpoints (no runtime smoke): `189`

## Target Tracking

- Expected endpoints (target): `247`
- Observed endpoints: `247`
- Target met: `True`
- Endpoint gap: `0`

## Coverage By Module

| Module | Total | Covered | Uncovered | Runtime PASS | Runtime FAIL | Test Ref | Coverage % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Admin | 1 | 0 | 1 | 0 | 0 | 0 | 0.0% |
| Agent | 1 | 1 | 0 | 0 | 0 | 1 | 100.0% |
| Assistant | 1 | 1 | 0 | 0 | 0 | 1 | 100.0% |
| Auth | 8 | 8 | 0 | 0 | 0 | 8 | 100.0% |
| Auto Analysis | 1 | 0 | 1 | 0 | 0 | 0 | 0.0% |
| Autonomy | 11 | 11 | 0 | 0 | 0 | 11 | 100.0% |
| AutonomyAdmin | 9 | 1 | 8 | 0 | 0 | 1 | 11.11% |
| AutonomyHistory | 4 | 4 | 0 | 0 | 0 | 4 | 100.0% |
| Chat | 12 | 11 | 1 | 0 | 0 | 11 | 91.67% |
| Collaboration | 11 | 11 | 0 | 0 | 0 | 11 | 100.0% |
| Collaboration - Workspace | 5 | 3 | 2 | 0 | 0 | 3 | 60.0% |
| Context | 6 | 6 | 0 | 0 | 0 | 6 | 100.0% |
| Deployment | 4 | 0 | 4 | 0 | 0 | 0 | 0.0% |
| Documents | 6 | 6 | 0 | 0 | 0 | 6 | 100.0% |
| Evaluation | 5 | 0 | 5 | 0 | 0 | 0 | 0.0% |
| Feedback | 7 | 7 | 0 | 0 | 0 | 7 | 100.0% |
| Knowledge | 27 | 20 | 7 | 2 | 0 | 18 | 74.07% |
| Learning | 12 | 12 | 0 | 0 | 0 | 12 | 100.0% |
| LLM | 12 | 0 | 12 | 0 | 0 | 0 | 0.0% |
| Meta-Agent | 6 | 6 | 0 | 0 | 0 | 6 | 100.0% |
| Observability | 24 | 24 | 0 | 0 | 0 | 24 | 100.0% |
| Optimization | 6 | 0 | 6 | 0 | 0 | 0 | 0.0% |
| PendingActions | 5 | 5 | 0 | 0 | 0 | 5 | 100.0% |
| Productivity | 11 | 11 | 0 | 0 | 0 | 11 | 100.0% |
| Profiles | 2 | 2 | 0 | 0 | 0 | 2 | 100.0% |
| RAG | 5 | 5 | 0 | 0 | 0 | 5 | 100.0% |
| Reflexion | 5 | 5 | 0 | 0 | 0 | 5 | 100.0% |
| Sandbox | 3 | 3 | 0 | 0 | 0 | 3 | 100.0% |
| System | 5 | 5 | 0 | 3 | 0 | 2 | 100.0% |
| Tasks | 8 | 8 | 0 | 0 | 0 | 8 | 100.0% |
| Tools | 8 | 8 | 0 | 0 | 0 | 8 | 100.0% |
| unknown | 7 | 4 | 3 | 1 | 0 | 3 | 57.14% |
| Users | 6 | 6 | 0 | 0 | 0 | 6 | 100.0% |
| Workers | 3 | 1 | 2 | 0 | 0 | 1 | 33.33% |

## Runtime Failures

- No runtime failures captured in smoke data.

## Uncovered Endpoints (top 150)

| Method | Path | Module | Operation Id |
|---|---|---|---|
| PATCH | `/api/v1/admin/config` | Admin | update_config_api_v1_admin_config_patch |
| GET | `/api/v1/auto-analysis/health-check` | Auto Analysis | auto_analyze_api_v1_auto_analysis_health_check_get |
| GET | `/api/v1/autonomy/admin/board` | AutonomyAdmin | get_board_api_v1_autonomy_admin_board_get |
| POST | `/api/v1/autonomy/admin/code-qa` | AutonomyAdmin | code_qa_api_v1_autonomy_admin_code_qa_post |
| GET | `/api/v1/autonomy/admin/self-study/neo4j-audit` | AutonomyAdmin | self_study_neo4j_audit_api_v1_autonomy_admin_self_study_neo4j_audit_get |
| POST | `/api/v1/autonomy/admin/self-study/neo4j-repair` | AutonomyAdmin | self_study_neo4j_repair_api_v1_autonomy_admin_self_study_neo4j_repair_post |
| POST | `/api/v1/autonomy/admin/self-study/run` | AutonomyAdmin | run_self_study_api_v1_autonomy_admin_self_study_run_post |
| GET | `/api/v1/autonomy/admin/self-study/runs` | AutonomyAdmin | self_study_runs_api_v1_autonomy_admin_self_study_runs_get |
| GET | `/api/v1/autonomy/admin/self-study/status` | AutonomyAdmin | self_study_status_api_v1_autonomy_admin_self_study_status_get |
| POST | `/api/v1/autonomy/admin/self-study/trigger-on-goal-complete` | AutonomyAdmin | admin_manual_goal_completion_trigger_api_v1_autonomy_admin_self_study_trigger_on_goal_complete_post |
| GET | `/api/v1/chat/study-jobs/{job_id}` | Chat | get_study_job_api_v1_chat_study_jobs__job_id__get |
| POST | `/api/v1/collaboration/workspace/messages/send` | Collaboration - Workspace | send_message_api_v1_collaboration_workspace_messages_send_post |
| GET | `/api/v1/collaboration/workspace/messages/{agent_id}` | Collaboration - Workspace | get_messages_for_api_v1_collaboration_workspace_messages__agent_id__get |
| POST | `/api/v1/deployment/precheck` | Deployment | precheck_api_v1_deployment_precheck_post |
| POST | `/api/v1/deployment/publish` | Deployment | publish_api_v1_deployment_publish_post |
| POST | `/api/v1/deployment/rollback` | Deployment | rollback_api_v1_deployment_rollback_post |
| POST | `/api/v1/deployment/stage` | Deployment | stage_api_v1_deployment_stage_post |
| GET | `/api/v1/evaluation/experiments` | Evaluation | list_experiments_api_v1_evaluation_experiments_get |
| POST | `/api/v1/evaluation/experiments` | Evaluation | create_experiment_api_v1_evaluation_experiments_post |
| POST | `/api/v1/evaluation/experiments/{experiment_id}/arms` | Evaluation | add_arm_api_v1_evaluation_experiments__experiment_id__arms_post |
| POST | `/api/v1/evaluation/experiments/{experiment_id}/results` | Evaluation | add_result_api_v1_evaluation_experiments__experiment_id__results_post |
| GET | `/api/v1/evaluation/experiments/{experiment_id}/winner` | Evaluation | experiment_winner_api_v1_evaluation_experiments__experiment_id__winner_get |
| GET | `/api/v1/knowledge/classes/implementations` | Knowledge | classes_implementations_api_v1_knowledge_classes_implementations_get |
| POST | `/api/v1/knowledge/consolidate/document` | Knowledge | consolidate_document_api_v1_knowledge_consolidate_document_post |
| GET | `/api/v1/knowledge/files/importing` | Knowledge | files_importing_api_v1_knowledge_files_importing_get |
| GET | `/api/v1/knowledge/functions/calling` | Knowledge | functions_calling_api_v1_knowledge_functions_calling_get |
| GET | `/api/v1/knowledge/quarantine` | Knowledge | list_quarantine_api_v1_knowledge_quarantine_get |
| POST | `/api/v1/knowledge/quarantine/promote` | Knowledge | promote_quarantine_api_v1_knowledge_quarantine_promote_post |
| POST | `/api/v1/knowledge/relationship-types/register` | Knowledge | register_relationship_type_api_v1_knowledge_relationship_types_register_post |
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
| POST | `/api/v1/optimization/analyze` | Optimization | analyze_system_api_v1_optimization_analyze_post |
| GET | `/api/v1/optimization/health` | Optimization | get_system_health_api_v1_optimization_health_get |
| GET | `/api/v1/optimization/issues` | Optimization | get_detected_issues_api_v1_optimization_issues_get |
| GET | `/api/v1/optimization/metrics/history` | Optimization | get_metrics_history_api_v1_optimization_metrics_history_get |
| POST | `/api/v1/optimization/run-cycle` | Optimization | run_optimization_cycle_api_v1_optimization_run_cycle_post |
| GET | `/api/v1/optimization/status` | Optimization | get_optimization_status_api_v1_optimization_status_get |
| GET | `/api/v1/memory/generative` | unknown | get_generative_memories_api_v1_memory_generative_get |
| POST | `/api/v1/memory/generative` | unknown | add_generative_memory_api_v1_memory_generative_post |
| GET | `/api/v1/memory/preferences` | unknown | get_user_preferences_api_v1_memory_preferences_get |
| POST | `/api/v1/workers/start-all` | Workers | start_workers_api_v1_workers_start_all_post |
| POST | `/api/v1/workers/stop-all` | Workers | stop_workers_api_v1_workers_stop_all_post |
