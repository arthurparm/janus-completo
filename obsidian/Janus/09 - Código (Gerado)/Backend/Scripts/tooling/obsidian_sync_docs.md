---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/obsidian_sync_docs.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# obsidian_sync_docs

## Arquivos-fonte
- `tooling/obsidian_sync_docs.py`

## Símbolos
- class: `MirrorSource`
- function: `now_iso()` -> `str`
- function: `normalize_rel(p: Path)` -> `str`
- function: `sha256_text(text: str)` -> `str`
- function: `inject_frontmatter(content: str, *, origin: str, generated_at: str)` -> `str`
- function: `write_text_if_changed(path: Path, content: str)` -> `bool`
- function: `is_markdown_file(path: Path)` -> `bool`
- function: `discover_markdown_files(root: Path)` -> `list[Path]`
- function: `make_index_md(title: str, items: list[tuple[str, str]], generated_at: str)` -> `str`
- function: `sync_source(source: MirrorSource, *, generated_at: str)` -> `tuple[int, int, list[str]]`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
