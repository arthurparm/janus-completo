---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/obsidian_generate_code_inventory.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# obsidian_generate_code_inventory

## Arquivos-fonte
- `tooling/obsidian_generate_code_inventory.py`

## Símbolos
- class: `SymbolSignature`
- class: `ModuleInventory`
- function: `now_iso()` -> `str`
- function: `rel_repo(path: Path)` -> `str`
- function: `rel_vault(path: Path)` -> `str`
- function: `read_text(path: Path)` -> `str`
- function: `write_text(path: Path, content: str)` -> `None`
- function: `discover_files(root: Path, *, suffix: str, exclude: set[str] | None = None)` -> `list[Path]`
- function: `format_annotation(node: ast.AST | None)` -> `str | None`
- function: `format_arguments(args: ast.arguments)` -> `str`
- function: `first_paragraph(doc: str | None)` -> `str | None`
- function: `extract_python_symbols(tree: ast.Module)` -> `list[SymbolSignature]`
- function: `parse_python_module(path: Path)` -> `tuple[str | None, list[SymbolSignature]]`
- function: `extract_endpoint_routes(text: str)` -> `list[str]`
- function: `extract_queue_names(text: str)` -> `list[str]`
- function: `extract_imported_modules(text: str, *, prefix: str)` -> `list[str]`
- function: `build_import_index(files: Iterable[Path])` -> `dict[str, list[str]]`
- function: `build_frontmatter(*, title: str, domain: str, layer: str, origin: str, generated_at: str)` -> `str`
- function: `render_module_note(inv: ModuleInventory, *, title: str, domain: str, generated_at: str)` -> `str`
- function: `note_path_for_backend(layer: str, module_file: Path)` -> `Path`
- function: `note_path_for_frontend(module_file: Path)` -> `Path`
- function: `discover_frontend_ts_files()` -> `list[Path]`
- function: `extract_ts_doc(text: str)` -> `str | None`
- function: `extract_ts_symbols(text: str)` -> `list[SymbolSignature]`
- function: `parse_ts_module(path: Path)` -> `tuple[str | None, list[SymbolSignature]]`
- function: `sanitize_obsidian_link(p: Path)` -> `str`
- function: `write_index(index_path: Path, *, title: str, notes: list[Path], generated_at: str)` -> `None`
- function: `update_section_list(md_path: Path, *, header: str, items: list[str])` -> `None`
- function: `update_services_inventory(service_files: list[Path])` -> `None`
- function: `update_models_inventory(model_files: list[Path])` -> `None`
- function: `update_endpoints_inventory(endpoint_files: list[Path])` -> `None`
- function: `update_workers_inventory(worker_files: list[Path])` -> `None`
- function: `load_api_matrix_modules()` -> `dict[str, list[str]]`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
