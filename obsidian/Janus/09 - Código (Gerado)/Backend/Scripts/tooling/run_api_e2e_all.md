---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/run_api_e2e_all.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# run_api_e2e_all

## Objetivo
Execute one runtime probe for every /api/v1 endpoint in the live OpenAPI spec.

## Arquivos-fonte
- `tooling/run_api_e2e_all.py`

## Símbolos
- class: `Endpoint`
- class: `ContextStore`
- method: `ContextStore.__init__(self)` -> `None`
- method: `ContextStore.get(self, path: str, default: Any = None)` -> `Any`
- method: `ContextStore.set(self, path: str, value: Any)` -> `None`
- function: `sanitize_headers(headers: dict[str, str])` -> `dict[str, str]`
- function: `fetch_openapi(openapi_url: str, timeout: float)` -> `dict[str, Any]`
- function: `save_json(path: Path, payload: Any)` -> `None`
- function: `load_fixtures(path: Path)` -> `dict[str, dict[str, Any]]`
- function: `iter_endpoints(openapi: dict[str, Any])` -> `list[Endpoint]`
- function: `build_endpoint_index(endpoints: Iterable[Endpoint])` -> `dict[tuple[str, str], Endpoint]`
- function: `resolve_ref(openapi: dict[str, Any], schema: dict[str, Any])` -> `dict[str, Any]`
- function: `choose_non_null_schema(openapi: dict[str, Any], options: list[Any])` -> `dict[str, Any]`
- function: `sample_string(name: str, schema: dict[str, Any], ctx: ContextStore)` -> `str`
- function: `sample_value(openapi: dict[str, Any], name: str, schema: dict[str, Any], ctx: ContextStore)` -> `Any`
- function: `interpolate_templates(obj: Any, ctx: ContextStore)` -> `Any`
- function: `path_param_sample(name: str, schema: dict[str, Any], ctx: ContextStore)` -> `Any`
- function: `query_param_sample(name: str, schema: dict[str, Any], ctx: ContextStore)` -> `Any`
- function: `collect_expected_statuses(endpoint: Endpoint, fixture: dict[str, Any] | None)` -> `list[int]`
- function: `endpoint_is_streaming(endpoint: Endpoint)` -> `bool`
- function: `classify_status(actual: int, expected: list[int])` -> `str`
- function: `retry_after_seconds(resp: requests.Response, attempt: int)` -> `float`
- function: `extract_json_path(payload: Any, path: str)` -> `Any`
- function: `infer_context_from_response(endpoint: Endpoint, body: Any, ctx: ContextStore)` -> `None`
- function: `build_request(endpoint: Endpoint, openapi: dict[str, Any], ctx: ContextStore, fixture: dict[str, Any] | None, *, allow_auto_auth: bool = True)` -> `tuple[str, dict[str, Any], dict[str, str], Any, str | None]`
- function: `summarize_response(resp: requests.Response)` -> `dict[str, Any]`
- function: `module_priority(name: str)` -> `int`
- function: `fixture_order(fixture: dict[str, Any] | None)` -> `int`
- function: `render_markdown(report: dict[str, Any])` -> `str`
- function: `_new_summary_bucket()` -> `dict[str, int]`
- function: `_run_phase(args: argparse.Namespace, *, phase: str, boot: dict[str, Any] | None = None, request_id_seq_start: int = 0)` -> `tuple[dict[str, Any], int]`
- function: `_render_markdown_dual(report: dict[str, Any])` -> `str`
- function: `main()` -> `int`
- function: `_flatten_keys(obj: Any, prefix: str = '')` -> `list[str]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
