---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/generate_api_coverage_report.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# generate_api_coverage_report

## Objetivo
Generate OQ-011 API coverage report from the live endpoint matrix.

## Arquivos-fonte
- `tooling/generate_api_coverage_report.py`

## Símbolos
- function: `now_iso()` -> `str`
- function: `normalize_path(path: str)` -> `str`
- function: `endpoint_status(endpoint: dict[str, Any])` -> `str`
- function: `parse_docker_ps_output(raw: str)` -> `list[dict[str, Any]]`
- function: `load_matrix(path: Path)` -> `dict[str, Any]`
- function: `build_coverage_report(matrix: dict[str, Any], expected_endpoints: int)` -> `dict[str, Any]`
- function: `render_markdown(report: dict[str, Any], max_uncovered_rows: int = 150)` -> `str`
- function: `_clip(text: str, max_chars: int = 20000)` -> `str`
- function: `_run(cmd: list[str])` -> `dict[str, Any]`
- function: `collect_docker_evidence(log_tail_lines: int)` -> `tuple[dict[str, Any], str]`
- function: `parse_args()` -> `argparse.Namespace`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
