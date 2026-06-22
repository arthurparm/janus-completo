---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/obsidian_validate_coverage.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# obsidian_validate_coverage

## Arquivos-fonte
- `tooling/obsidian_validate_coverage.py`

## Símbolos
- function: `rel_repo(path: Path)` -> `str`
- function: `discover_files(root: Path, *, suffix: str, exclude: set[str] | None = None)` -> `list[Path]`
- function: `note_path_for_backend(layer: str, module_file: Path)` -> `Path`
- function: `note_path_for_frontend(module_file: Path)` -> `Path`
- function: `discover_frontend_ts_files()` -> `list[Path]`
- function: `find_missing_frontend_notes(files: list[Path])` -> `list[str]`
- class: `CoverageResult`
- function: `now_iso()` -> `str`
- function: `read_text(path: Path)` -> `str`
- function: `find_missing_notes(layer: str, files: list[Path])` -> `list[str]`
- function: `validate_inventory_contains_all(md_path: Path, items: list[str])` -> `list[str]`
- function: `list_markdown_files(root: Path)` -> `list[Path]`
- function: `expected_mirrors()` -> `list[tuple[Path, Path]]`
- function: `validate_mirrors()` -> `CoverageResult`
- function: `write_report(results: list[CoverageResult], *, generated_at: str)` -> `dict[str, Any]`
- function: `write_checklist(report: dict[str, Any])` -> `None`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
