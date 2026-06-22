---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/knowledge_space_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# knowledge_space_service

## Arquivos-fonte
- `backend/app/services/knowledge_space_service.py`

## Dependências de código
- Repositórios
  - `data_governance_repository`
  - `document_manifest_repository`
  - `knowledge_space_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/knowledge.py`
- `backend/app/core/workers/async_consolidation_worker.py`
- `backend/app/core/workers/document_ingestion_worker.py`
- `backend/app/services/chat/message_orchestration_service.py`

## Símbolos
- class: `KnowledgeSpaceService`
- method: `KnowledgeSpaceService.__init__(self, *, manifest_repo: DocumentManifestRepository | None = None, space_repo: KnowledgeSpaceRepository | None = None, llm_service: Any | None = None)` -> `None`
- method: `KnowledgeSpaceService.build_space_id(self, user_id: str)` -> `str`
- method: `KnowledgeSpaceService.create_space(self, *, user_id: str, name: str, source_type: str = 'documentation', source_id: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None, description: str | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.list_spaces(self, *, user_id: str, limit: int = 100)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService.get_space(self, *, knowledge_space_id: str, user_id: str | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.get_space_status(self, *, knowledge_space_id: str, user_id: str | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._reconcile_ready_processing_space(self, *, knowledge_space: dict[str, Any], documents_processing: int = 0, documents_queued: int = 0)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.mark_consolidation_requested(self, *, knowledge_space_id: str, user_id: str | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.attach_document(self, *, knowledge_space_id: str, doc_id: str, user_id: str, source_type: str | None = None, source_id: str | None = None, doc_role: str | None = None, edition_or_version: str | None = None, language: str | None = None, parent_collection_id: str | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.consolidate_space(self, *, knowledge_space_id: str, limit_docs: int = 20)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.query_space(self, *, knowledge_space_id: str, user_id: str | None = None, question: str, mode: str = 'auto', limit: int = 5)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService.estimate_query_timing(self, *, knowledge_space_id: str, question: str, mode: str = 'auto')` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._build_query_timing_hint(self, *, knowledge_space: dict[str, Any], question: str, mode: str, query_profile: dict[str, Any] | None = None, prefer_locator: bool | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._merge_query_timing_hint(self, result: dict[str, Any], *, timing_hint: dict[str, Any])` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._build_scope_payload(self, *, knowledge_space_id: str | None, source_type: str | None, source_id: str | None, doc_role: str | None, edition_or_version: str | None, language: str | None, parent_collection_id: str | None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._sync_doc_scope_payload(self, *, doc_id: str, user_id: str, scope_payload: dict[str, Any])` -> `None`
- method: `KnowledgeSpaceService._load_document_points(self, *, doc_id: str, user_id: str, knowledge_space_id: str)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._build_structured_sections(self, *, text: str | None = None, points: list[dict[str, Any]] | None = None, manifest: dict[str, Any], knowledge_space: dict[str, Any])` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._prepare_document_lines(self, *, text: str | None, points: list[dict[str, Any]] | None)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._clean_document_text(self, text: str)` -> `str`
- method: `KnowledgeSpaceService._normalize_inline_text(self, value: str)` -> `str`
- method: `KnowledgeSpaceService._normalize_line_key(self, value: str)` -> `str`
- method: `KnowledgeSpaceService._is_repeated_noise_candidate(self, value: str)` -> `bool`
- method: `KnowledgeSpaceService._is_noise_line(self, value: str)` -> `bool`
- method: `KnowledgeSpaceService._looks_like_table_line(self, value: str)` -> `bool`
- method: `KnowledgeSpaceService._classify_section(self, title: str, body: str, *, doc_role: str, order: int)` -> `str`
- method: `KnowledgeSpaceService._infer_applies_to(self, title: str, body: str, *, section_role: str)` -> `list[str]`
- method: `KnowledgeSpaceService._infer_extends_or_overrides(self, title: str, body: str, doc_role: str)` -> `str | None`
- method: `KnowledgeSpaceService._infer_doc_role(self, manifest: dict[str, Any], knowledge_space: dict[str, Any])` -> `str`
- method: `KnowledgeSpaceService._is_heading(self, line: str)` -> `bool`
- method: `KnowledgeSpaceService._normalize_heading_title(self, line: str)` -> `str`
- method: `KnowledgeSpaceService._normalize_heading_token(self, token: str)` -> `str`
- method: `KnowledgeSpaceService._normalize_search_text(self, value: str)` -> `str`
- method: `KnowledgeSpaceService._compact_search_text(self, value: str)` -> `str`
- method: `KnowledgeSpaceService._tokenize_search_terms(self, value: str, *, min_len: int = 3)` -> `set[str]`
- method: `KnowledgeSpaceService._score_heading_quality(self, title: str)` -> `float`
- method: `KnowledgeSpaceService._score_content_density(self, body: str)` -> `float`
- method: `KnowledgeSpaceService._score_noise(self, *, title: str, body: str, section_role: str, order: int)` -> `float`
- method: `KnowledgeSpaceService._looks_like_editorial_content(self, *, title: str, body: str)` -> `bool`
- method: `KnowledgeSpaceService._has_creation_foundation_signal(self, *, title: str, content: str, doc_role: str)` -> `bool`
- method: `KnowledgeSpaceService._looks_like_premise_or_flavor_section(self, *, title: str, content: str)` -> `bool`
- method: `KnowledgeSpaceService._is_base_creation_foundation_section(self, *, title: str, content: str, section_role: str, applies_to: list[str] | set[str] | tuple[str, ...])` -> `bool`
- method: `KnowledgeSpaceService._is_supplement_creation_extension_section(self, *, title: str, content: str, section_role: str, applies_to: list[str] | set[str] | tuple[str, ...])` -> `bool`
- method: `KnowledgeSpaceService._apply_section_quality(self, section: dict[str, Any])` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._finalize_sections(self, sections: list[dict[str, Any]])` -> `tuple[list[dict[str, Any]], int]`
- method: `KnowledgeSpaceService._build_query_profile(self, question: str)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._extract_task_target_phrases(self, *, question: str, topic_phrases: set[str], source_terms: set[str])` -> `set[str]`
- method: `KnowledgeSpaceService._sanitize_task_target_phrase(self, value: str | None)` -> `str`
- method: `KnowledgeSpaceService._sanitize_entity_candidate(self, value: str | None, *, max_tokens: int = 3)` -> `str`
- method: `KnowledgeSpaceService._sanitize_theme_candidate(self, value: str | None, *, max_tokens: int = 3)` -> `str`
- method: `KnowledgeSpaceService._should_accept_llm_entity_candidate(self, entity: str, *, title: str, body: str)` -> `bool`
- method: `KnowledgeSpaceService._select_strict_topic_phrases(self, *, topic_terms: set[str], topic_phrases: set[str])` -> `set[str]`
- method: `KnowledgeSpaceService._extract_query_phrases(self, question: str)` -> `set[str]`
- method: `KnowledgeSpaceService._trim_text(self, text: str | None, *, max_chars: int)` -> `str`
- method: `KnowledgeSpaceService._chunk_rows(self, rows: list[dict[str, Any]], *, batch_size: int)` -> `list[list[dict[str, Any]]]`
- method: `KnowledgeSpaceService._summarize_text(self, text: str, max_chars: int = 360)` -> `str`
- method: `KnowledgeSpaceService._extract_concepts(self, text: str, *, title: str, limit: int = 6)` -> `list[str]`
- method: `KnowledgeSpaceService._extract_entities(self, text: str, *, title: str, limit: int = 6)` -> `list[str]`
- method: `KnowledgeSpaceService._extract_themes(self, text: str, *, title: str, entities: list[str] | None = None, limit: int = 6)` -> `list[str]`
- method: `KnowledgeSpaceService._enrich_sections_with_llm(self, sections: list[dict[str, Any]], *, knowledge_space: dict[str, Any])` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._select_sections_for_llm_enrichment(self, sections: list[dict[str, Any]], *, max_sections: int)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._build_section_enrichment_prompt(self, *, section: dict[str, Any], knowledge_space: dict[str, Any])` -> `str`
- method: `KnowledgeSpaceService._merge_llm_section_enrichment(self, *, section: dict[str, Any], payload: dict[str, Any] | None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._build_consolidation_metrics(self, *, sections: list[dict[str, Any]], skipped_sections: int)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._index_canonical_sections(self, *, knowledge_space: dict[str, Any], sections: list[dict[str, Any]])` -> `int`
- method: `KnowledgeSpaceService._upsert_points_resilient(self, *, client: Any, collection_name: str, points: list[models.PointStruct], min_batch_size: int = 8)` -> `None`
- method: `KnowledgeSpaceService._persist_structure_graph(self, *, knowledge_space: dict[str, Any], manifests: list[dict[str, Any]], sections: list[dict[str, Any]])` -> `None`
- method: `KnowledgeSpaceService._build_consolidation_summary(self, *, space: dict[str, Any], manifests: list[dict[str, Any]], sections: list[dict[str, Any]], metrics: dict[str, Any])` -> `str`
- method: `KnowledgeSpaceService._detect_scope_conflicts(self, *, space: dict[str, Any], manifests: list[dict[str, Any]])` -> `list[str]`
- method: `KnowledgeSpaceService._lexical_overlap(self, *, text: str, title: str, concepts: list[str], query_terms: set[str])` -> `int`
- method: `KnowledgeSpaceService._target_overlap(self, *, text: str, title: str, concepts: list[str], target_terms: set[str], target_phrases: set[str])` -> `tuple[int, int]`
- method: `KnowledgeSpaceService._count_conflicting_entities(self, *, entities: list[str], target_terms: set[str], target_phrases: set[str])` -> `tuple[int, int]`
- method: `KnowledgeSpaceService._phrase_overlap(self, *, text: str, title: str, query_phrases: set[str])` -> `int`
- method: `KnowledgeSpaceService._is_low_trust_sequence_title(self, title: str)` -> `bool`
- method: `KnowledgeSpaceService._is_sequence_anchor(self, *, title: str, content: str, doc_role: str)` -> `bool`
- method: `KnowledgeSpaceService._looks_like_specific_option_chunk(self, *, title: str, content: str)` -> `bool`
- method: `KnowledgeSpaceService._looks_like_table_of_contents_chunk(self, *, title: str, content: str)` -> `bool`
- method: `KnowledgeSpaceService._classify_chunk_match(self, *, point_score: float, lexical_overlap: int, phrase_overlap: int, explicit_locator: bool)` -> `str`
- method: `KnowledgeSpaceService._query_canonical(self, *, knowledge_space: dict[str, Any], question: str, limit: int, active_doc_ids: set[str] | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._should_scroll_canonical_point_type(self, *, point_type: str, query_profile: dict[str, Any], answer_strategy: str)` -> `bool`
- method: `KnowledgeSpaceService._resolve_canonical_query_types(self, answer_strategy: str)` -> `list[str]`
- method: `KnowledgeSpaceService._detect_answer_strategy(self, question: str)` -> `str`
- method: `KnowledgeSpaceService._build_ollama_only_policy(self, *, model: str)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._is_target_constrained_task_candidate(self, *, title: str, content: str, doc_role: str, section_role: str, applies_to: list[str] | None, target_term_overlap: int, target_phrase_overlap: int, matched_entities: int, conflicting_entities: int, query_profile: dict[str, Any])` -> `bool`
- method: `KnowledgeSpaceService._collect_operational_support_points(self, *, knowledge_space: dict[str, Any], question: str, limit: int, active_doc_ids: set[str] | None, selected_sections: list[dict[str, Any]] | None = None, support_plan: dict[str, Any] | None = None)` -> `list[Any]`
- method: `KnowledgeSpaceService._build_target_constrained_support_steps(self, *, query_profile: dict[str, Any])` -> `list[dict[str, str]]`
- method: `KnowledgeSpaceService._build_fallback_operational_plan(self, *, selected_sections: list[dict[str, Any]], query_profile: dict[str, Any] | None = None)` -> `list[dict[str, str]]`
- method: `KnowledgeSpaceService._build_operational_plan_prompt(self, *, question: str, selected: list[dict[str, Any]], knowledge_space: dict[str, Any], query_profile: dict[str, Any] | None = None)` -> `str`
- method: `KnowledgeSpaceService._plan_operational_support(self, *, question: str, selected: list[dict[str, Any]], knowledge_space: dict[str, Any])` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._build_operational_prompt(self, *, question: str, retrieval_strategy: str, selected: list[dict[str, Any]], support_points: list[Any], knowledge_space: dict[str, Any], support_plan: dict[str, Any] | None = None)` -> `str`
- method: `KnowledgeSpaceService._render_operational_answer(self, *, selected: list[dict[str, Any]], retrieval_strategy: str, knowledge_space: dict[str, Any], question: str, limit: int, active_doc_ids: set[str] | None)` -> `str`
- method: `KnowledgeSpaceService._prefer_locator(self, question: str)` -> `bool`
- method: `KnowledgeSpaceService._select_canonical_candidates(self, *, points: list[Any], question: str, query_profile: dict[str, Any], answer_strategy: str, limit: int)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._prune_target_constrained_task_sections(self, *, selected: list[dict[str, Any]], query_profile: dict[str, Any], limit: int)` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._replace_with_structural_supplement_anchor(self, *, selected: list[dict[str, Any]], candidate_points: list[Any], query_profile: dict[str, Any])` -> `list[dict[str, Any]]`
- method: `KnowledgeSpaceService._build_canonical_gaps(self, *, selected: list[dict[str, Any]], answer_strategy: str, confidence: float, query_profile: dict[str, Any])` -> `list[str]`
- method: `KnowledgeSpaceService._query_quick_lookup(self, *, knowledge_space: dict[str, Any], question: str, limit: int, active_doc_ids: set[str] | None = None)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._select_quick_lookup_points(self, *, points: list[Any], question: str, query_profile: dict[str, Any], limit: int)` -> `list[Any]`
- method: `KnowledgeSpaceService._build_source_scope(self, knowledge_space: dict[str, Any])` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._render_canonical_answer(self, selected: list[dict[str, Any]], *, answer_strategy: str)` -> `str`
- method: `KnowledgeSpaceService._render_comparative_answer(self, selected: list[dict[str, Any]])` -> `str`
- method: `KnowledgeSpaceService._render_sequence_answer(self, selected: list[dict[str, Any]])` -> `str`
- method: `KnowledgeSpaceService._render_scope_answer(self, selected: list[dict[str, Any]])` -> `str`
- method: `KnowledgeSpaceService._render_quick_answer(self, points: list[Any], *, knowledge_space: dict[str, Any])` -> `str`
- method: `KnowledgeSpaceService._map_citation(self, point: Any, *, snippet_limit: int)` -> `dict[str, Any]`
- method: `KnowledgeSpaceService._collect_conflicting_support_entities(self, *, selected: list[dict[str, Any]], support_points: list[Any], query_profile: dict[str, Any])` -> `set[str]`
- method: `KnowledgeSpaceService._looks_low_information_operational_answer(self, response: str)` -> `bool`
- method: `KnowledgeSpaceService._should_accept_operational_response(self, *, response: str, selected: list[dict[str, Any]], support_points: list[Any], query_profile: dict[str, Any], support_plan: dict[str, Any] | None)` -> `bool`
- method: `KnowledgeSpaceService._render_grounded_task_fallback(self, *, selected: list[dict[str, Any]], support_points: list[Any], query_profile: dict[str, Any], support_plan: dict[str, Any] | None)` -> `str`
- method: `KnowledgeSpaceService._select_best_operational_support_section(self, *, support_points: list[Any], doc_role: str, query_profile: dict[str, Any])` -> `dict[str, Any] | None`
- method: `KnowledgeSpaceService._average_score(self, points: list[Any])` -> `float`
- method: `KnowledgeSpaceService._is_retryable_qdrant_scroll_error(self, exc: Exception)` -> `bool`
- method: `KnowledgeSpaceService._scroll_points(self, *, collection_name: str, query_filter: models.Filter, batch_size: int = 128, min_batch_size: int = 16)` -> `list[Any]`
- method: `KnowledgeSpaceService._filter_points_by_doc_ids(self, points: list[Any], *, active_doc_ids: set[str] | None)` -> `list[Any]`
- function: `get_knowledge_space_service(request: Request)` -> `KnowledgeSpaceService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
