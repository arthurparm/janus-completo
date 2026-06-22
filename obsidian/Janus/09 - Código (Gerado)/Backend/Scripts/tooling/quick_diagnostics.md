---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/quick_diagnostics.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# quick_diagnostics

## Arquivos-fonte
- `tooling/quick_diagnostics.py`

## Símbolos
- function: `_http_probe(url: str, timeout: float, insecure_tls: bool)` -> `dict[str, Any]`
- function: `_tcp_probe(host: str, port: int, timeout: float)` -> `dict[str, Any]`
- function: `_config_checks(config_paths: list[str] | None = None)` -> `list[dict[str, Any]]`
- function: `_parse_env_file(path: Path)` -> `dict[str, str]`
- function: `build_report(host: str, backend_port: int, frontend_port: int, timeout: float, insecure_tls: bool, config_paths: list[str] | None = None, http_probe: Callable[[str, float, bool], dict[str, Any]] = _http_probe, tcp_probe: Callable[[str, int, float], dict[str, Any]] = _tcp_probe)` -> `dict[str, Any]`
- function: `parse_args()` -> `argparse.Namespace`
- function: `_print_summary(report: dict[str, Any])` -> `None`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
