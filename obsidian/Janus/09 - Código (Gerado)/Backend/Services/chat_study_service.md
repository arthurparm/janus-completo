---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/chat_study_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# chat_study_service

## Arquivos-fonte
- `backend/app/services/chat_study_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/chat/chat_message.py`
- `backend/app/services/chat/streaming_service.py`

## Símbolos
- function: `_repo_root()` -> `Path`
- function: `_question_tokens(question: str)` -> `list[str]`
- function: `_looks_text_file(path: Path)` -> `bool`
- function: `_sanitize_snippet(snippet: str)` -> `str`
- class: `ChatStudyJob`
- class: `ChatStudyService`
- method: `ChatStudyService.__init__(self, *, llm_service: Any | None, knowledge_service: Any | None, autonomy_admin_service: Any | None)` -> `None`
- method: `ChatStudyService.answer_with_study(self, *, question: str, role: ModelRole = ModelRole.ORCHESTRATOR, priority: ModelPriority = ModelPriority.FAST_AND_CHEAP, user_id: str | None = None, conversation_id: str | None = None, progress_cb: Any | None = None)` -> `dict[str, Any]`
- method: `ChatStudyService._try_knowledge_first(self, *, question: str, role: ModelRole, priority: ModelPriority, progress: Any)` -> `str | None`
- method: `ChatStudyService._safe_knowledge_health(self)` -> `dict[str, Any]`
- method: `ChatStudyService._run_self_study(self, question: str)` -> `None`
- method: `ChatStudyService._iter_repo_files(self)` -> `list[Path]`
- method: `ChatStudyService._scan_repo_for_citations(self, question: str)` -> `list[dict[str, Any]]`
- method: `ChatStudyService._build_citation(self, path: Path, tokens: list[str])` -> `dict[str, Any] | None`
- method: `ChatStudyService._synthesize_answer(self, *, question: str, citations: list[dict[str, Any]], role: ModelRole, priority: ModelPriority)` -> `str`
- class: `ChatStudyJobService`
- method: `ChatStudyJobService.__init__(self, *, study_service: ChatStudyService, chat_service: Any)` -> `None`
- method: `ChatStudyJobService.create_job(self, *, conversation_id: str, message_id: str, question: str, user_id: str | None, placeholder_message: str)` -> `ChatStudyJob`
- method: `ChatStudyJobService.get_job(self, job_id: str)` -> `ChatStudyJob | None`
- method: `ChatStudyJobService.run_job(self, *, job_id: str, role: ModelRole = ModelRole.ORCHESTRATOR, priority: ModelPriority = ModelPriority.FAST_AND_CHEAP)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
