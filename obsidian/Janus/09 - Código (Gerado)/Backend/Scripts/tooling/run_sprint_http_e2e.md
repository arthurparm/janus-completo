---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/run_sprint_http_e2e.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# run_sprint_http_e2e

## Arquivos-fonte
- `tooling/run_sprint_http_e2e.py`

## Símbolos
- class: `HttpRequestDef`
- function: `interpolate(text: str, vars_map: dict[str, str])` -> `str`
- function: `parse_http_file(path: Path)` -> `tuple[dict[str, str], list[HttpRequestDef]]`
- function: `expected_statuses_from_script(script: str)` -> `list[int]`
- function: `extract_json_path(payload: Any, path: str)` -> `Any`
- function: `_eval_assign_expr(expr: str, payload: Any, status_code: int)` -> `str | None`
- function: `apply_script_assignments(script: str, payload: Any, status_code: int, vars_map: dict[str, str])` -> `None`
- function: `summarize_response(resp: requests.Response)` -> `dict[str, Any]`
- function: `execute_request(req: HttpRequestDef, *, session: requests.Session, vars_map: dict[str, str], phase: str, seq: int, timeout: float, request_id_prefix: str, correlator: DockerLogCorrelator | None)` -> `tuple[dict[str, Any], dict[str, Any] | None]`
- function: `_redact_bootstrap_auth(boot: dict[str, Any] | None)` -> `dict[str, Any] | None`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
