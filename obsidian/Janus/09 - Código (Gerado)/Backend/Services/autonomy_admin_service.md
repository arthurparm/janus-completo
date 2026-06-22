---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/autonomy_admin_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# autonomy_admin_service

## Arquivos-fonte
- `backend/app/services/autonomy_admin_service.py`

## Dependências de código
- Repositórios
  - `autonomy_admin_repository`
  - `memory_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/autonomy.py`
- `backend/app/api/v1/endpoints/autonomy_admin.py`
- `backend/app/main.py`
- `backend/app/services/collaboration_service.py`

## Símbolos
- class: `AutonomyAdminServiceError`
- class: `AutonomyAdminService`
- method: `AutonomyAdminService.__init__(self, llm_service: LLMService, knowledge_service: KnowledgeService)`
- method: `AutonomyAdminService._normalize_repo_path(self, raw_path: str | Path | None)` -> `str | None`
- method: `AutonomyAdminService._is_allowed_file_path(self, rel_path: str | None)` -> `bool`
- method: `AutonomyAdminService._repo_relative_if_allowed(self, path: Path)` -> `str | None`
- method: `AutonomyAdminService._looks_like_remote_reference(raw_path: str | Path | None)` -> `bool`
- method: `AutonomyAdminService._resolve_local_study_path(self, raw_path: str | Path | None)` -> `tuple[Path | None, str | None]`
- method: `AutonomyAdminService._fingerprint(parts: list[str])` -> `str`
- method: `AutonomyAdminService._build_self_memory_key(self, *, rel_path: str, summary_version: str | None, sha_after: str | None)` -> `str`
- method: `AutonomyAdminService._get_self_study_run_budget_seconds(self)` -> `int`
- method: `AutonomyAdminService._classify_sprint_type(self, finding: dict[str, Any])` -> `tuple[str, str | None, bool, str | None, str | None]`
- method: `AutonomyAdminService._find_latest_json(self, pattern: str)` -> `Path | None`
- method: `AutonomyAdminService._load_json_if_exists(self, path: Path | None)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._collect_findings(self)` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService.sync_backlog(self)` -> `dict[str, Any]`
- method: `AutonomyAdminService.auto_close_tasks(self)` -> `int`
- method: `AutonomyAdminService.get_board(self, *, status: str | None = None, limit: int = 200)` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService._git(self, args: list[str])` -> `str | None`
- method: `AutonomyAdminService._get_head_commit(self)` -> `str | None`
- method: `AutonomyAdminService._resolve_files_for_study(self, *, mode: str, base_commit: str | None, target_commit: str | None, task_files: list[str] | None = None)` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService._compact_list(values: list[str], limit: int = 6)` -> `list[str]`
- method: `AutonomyAdminService._extract_touchpoints(content_lower: str)` -> `list[str]`
- method: `AutonomyAdminService._infer_domain_tags(self, rel_path: str, content_lower: str)` -> `list[str]`
- method: `AutonomyAdminService._build_summary_payload(self, *, rel_path: str, language: str, summary: str, symbols: list[str], imports: list[str], touchpoints: list[str], domain_tags: list[str], confidence: float, purpose: str, risks: list[str], test_impact: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._summarize_python_file(self, rel_path: str, content: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._summarize_js_like_file(self, rel_path: str, content: str, suffix: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._summarize_style_file(self, rel_path: str, content: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._summarize_markdown_file(self, rel_path: str, content: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._summarize_json_file(self, rel_path: str, content: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._summarize_file(self, rel_path: str)` -> `dict[str, Any] | None`
- method: `AutonomyAdminService._build_graph_path_candidates(self, rel_path: str)` -> `list[str]`
- method: `AutonomyAdminService._preferred_graph_owner_path(self, rel_path: str, path_candidates: list[str])` -> `str`
- method: `AutonomyAdminService._read_study_file_content(self, rel_path: str)` -> `tuple[str, str] | None`
- method: `AutonomyAdminService._infer_self_memory_relationship_types(self, rel_path: str, summary: str)` -> `list[str]`
- method: `AutonomyAdminService._build_self_memory_rel_merge_block(self, target_var: str)` -> `str`
- method: `AutonomyAdminService._get_code_graph_file_count(self)` -> `int`
- method: `AutonomyAdminService._ensure_code_graph_ready(self, *, force: bool = False)` -> `int`
- method: `AutonomyAdminService._upsert_self_memory_graph_links(self, *, memory_key: str, rel_path: str, path_candidates: list[str], summary_payload: dict[str, Any], sha_after: str | None, source_experience_id: str | None, symbol_names: list[str], rel_types: list[str])` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService._get_self_memory_graph_link_counts(self, *, memory_key: str, rel_path: str, path_candidates: list[str], symbol_names: list[str])` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService._memorize_self_study_summary(self, *, rel_path: str, summary_payload: dict[str, Any], sha_after: str | None)` -> `Experience`
- method: `AutonomyAdminService._ensure_self_study_experience_node(self, *, experience: Experience, rel_path: str, summary_payload: dict[str, Any])` -> `None`
- method: `AutonomyAdminService._persist_self_memory(self, *, rel_path: str, summary_payload: dict[str, Any], sha_after: str | None, source_experience_id: str | None = None)` -> `None`
- method: `AutonomyAdminService.run_self_study(self, *, mode: str = 'incremental', reason: str | None = None, trigger_type: str = 'manual', task_files: list[str] | None = None)` -> `dict[str, Any]`
- method: `AutonomyAdminService.get_self_study_status(self)` -> `dict[str, Any]`
- method: `AutonomyAdminService.get_self_study_neo4j_audit(self, *, orphan_limit: int = 25)` -> `dict[str, Any]`
- method: `AutonomyAdminService.repair_self_study_neo4j(self, *, limit: int | None = None)` -> `dict[str, Any]`
- method: `AutonomyAdminService.list_self_study_runs(self, limit: int = 20)` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService._is_legacy_code_answer(answer: str)` -> `bool`
- method: `AutonomyAdminService._line_label(citation: dict[str, Any])` -> `str`
- method: `AutonomyAdminService._build_code_evidence_answer(self, *, question: str, citations: list[dict[str, Any]], self_memory: list[dict[str, Any]])` -> `str`
- method: `AutonomyAdminService._recall_self_study_memories(self, *, question: str, limit: int = 5)` -> `list[dict[str, Any]]`
- method: `AutonomyAdminService.ask_code_as_admin(self, *, question: str, limit: int = 10, citation_limit: int = 8)` -> `dict[str, Any]`
- method: `AutonomyAdminService.startup_self_study_check(self)` -> `dict[str, Any]`
- function: `get_autonomy_admin_service(request: Request)` -> `AutonomyAdminService`
- function: `maybe_trigger_self_study_on_goal_completion(*, app: Any | None, reason: str, trigger_type: str = 'goal_completed')` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
