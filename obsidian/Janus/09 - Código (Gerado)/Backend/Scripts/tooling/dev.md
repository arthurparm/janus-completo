---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/dev.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# dev

## Arquivos-fonte
- `tooling/dev.py`

## Símbolos
- function: `run(cmd: list[str], *, cwd: Path | None = None)` -> `None`
- function: `ensure_env_files()` -> `None`
- function: `resolve_env_file(name: str)` -> `str`
- function: `npm_install(frontend_dir: Path)` -> `None`
- function: `wait_for_health(urls: list[str], retries: int = 90, sleep_seconds: float = 2.0)` -> `None`
- function: `cmd_setup()` -> `None`
- function: `cmd_up()` -> `None`
- function: `cmd_qa()` -> `None`
- function: `cmd_down()` -> `None`
- function: `cmd_doctor(args: argparse.Namespace)` -> `None`
- function: `cmd_checklist(args: argparse.Namespace)` -> `None`
- function: `parse_args()` -> `argparse.Namespace`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
