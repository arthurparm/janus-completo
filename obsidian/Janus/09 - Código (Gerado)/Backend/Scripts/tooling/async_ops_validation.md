---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/async_ops_validation.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# async_ops_validation

## Objetivo
Operational async validation runner:
- Concurrent API load scenario
- Controlled chaos (postgres down/up)
- SLO gate evaluation
- JSON report output

## Arquivos-fonte
- `tooling/async_ops_validation.py`

## Símbolos
- class: `RequestResult`
- function: `_http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 45.0)` -> `tuple[int, Any, float]`
- function: `_safe_call(endpoint: str, method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 45.0)` -> `RequestResult`
- function: `_quantile(values: list[float], q: float)` -> `float`
- function: `_summarize(results: list[RequestResult])` -> `dict[str, Any]`
- function: `_user_flow(base_url: str, idx: int, timeout: float)` -> `list[RequestResult]`
- function: `run_concurrent_load(base_url: str, users: int, timeout: float)` -> `dict[str, Any]`
- function: `_docker(cmd: list[str])` -> `subprocess.CompletedProcess[str]`
- function: `_wait_service_healthy(container_name: str, timeout_s: float)` -> `bool`
- function: `run_chaos(base_url: str, chaos_timeout_s: float, postgres_container: str)` -> `dict[str, Any]`
- function: `evaluate_slo(load_summary: dict[str, Any], chaos_summary: dict[str, Any], slo: dict[str, float])` -> `dict[str, Any]`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
