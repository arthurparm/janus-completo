---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/generate_api_matrix.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# generate_api_matrix

## Objetivo
Generate live API endpoint matrix and governance artifacts.

## Arquivos-fonte
- `tooling/generate_api_matrix.py`

## Símbolos
- class: `EndpointKey`
- function: `now_iso()` -> `str`
- function: `normalize_path(path: str)` -> `str`
- function: `fetch_openapi()` -> `dict[str, Any] | None`
- function: `extract_endpoints_from_openapi(spec: dict[str, Any])` -> `list[dict[str, Any]]`
- function: `load_endpoints()` -> `tuple[list[dict[str, Any]], str]`
- function: `load_smoke_results()` -> `dict[EndpointKey, dict[str, Any]]`
- function: `discover_test_endpoint_refs()` -> `set[str]`
- function: `template_path_to_regex(path: str)` -> `re.Pattern[str]`
- function: `build_matrix()` -> `dict[str, Any]`
- function: `render_markdown(matrix: dict[str, Any])` -> `str`
- function: `main()` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
