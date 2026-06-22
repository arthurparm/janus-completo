---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/technical_qa_eval_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# technical_qa_eval_service

## Arquivos-fonte
- `backend/app/services/technical_qa_eval_service.py`

## Símbolos
- function: `_now_iso()` -> `str`
- function: `_percentile(values: list[float], percentile: float)` -> `float`
- function: `_dataset_hash(payload: dict[str, Any])` -> `str`
- function: `_safe_slug(value: str)` -> `str`
- function: `_line_value(raw: Any)` -> `int`
- function: `_citation_rule_matches(citation: dict[str, Any], rule: dict[str, Any])` -> `bool`
- class: `TechnicalQAEvaluator`
- method: `TechnicalQAEvaluator.__init__(self, dataset_path: str | Path)`
- method: `TechnicalQAEvaluator.load_dataset(self)` -> `dict[str, Any]`
- method: `TechnicalQAEvaluator.run(self, query_fn: QueryFn, *, query_limit: int = 10, citation_limit: int = 8, timeout_s: float = 20.0)` -> `dict[str, Any]`
- function: `render_markdown_summary(result: dict[str, Any])` -> `str`
- function: `write_run_artifacts(result: dict[str, Any], runs_root: str | Path)` -> `Path`
- function: `publish_baseline(result: dict[str, Any], baselines_root: str | Path)` -> `Path`
- function: `compare_with_baseline(result: dict[str, Any], baselines_root: str | Path)` -> `dict[str, Any] | None`
- function: `evaluate_regression_gate(*, comparison: dict[str, Any] | None, require_baseline: bool, max_pass_rate_drop: float, max_citation_coverage_drop: float, max_p95_latency_increase_ms: float)` -> `dict[str, Any]`
- function: `_find_repo_file_for_rule(repo_root: Path, rule: dict[str, Any])` -> `Path | None`
- function: `_find_line_for_keywords(file_path: Path, keywords: list[str], fallback_line: int)` -> `int`
- function: `build_offline_codebase_query_fn(*, dataset_payload: dict[str, Any], repo_root: str | Path)` -> `QueryFn`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
