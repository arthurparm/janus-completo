#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "obsidian" / "Janus"
OUT_BASE = VAULT / "08 - Documentação do Repositório (Gerado)"

SOURCE_DIRS = [
    ("documentation", ROOT / "documentation"),
    ("backend-docs", ROOT / "backend" / "docs"),
]


@dataclass(frozen=True)
class MirrorSource:
    key: str
    root: Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_rel(p: Path) -> str:
    return p.as_posix().lstrip("./")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def inject_frontmatter(content: str, *, origin: str, generated_at: str) -> str:
    header_lines = [
        "gerado: true",
        f'origem: "{origin}"',
        f'ultima_geracao: "{generated_at}"',
    ]

    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            return "---\n" + "\n".join(header_lines) + "\n" + content[len("---\n") :]

    return "---\n" + "\n".join(header_lines) + "\n---\n\n" + content


def write_text_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if sha256_text(existing) == sha256_text(content):
            return False
    path.write_text(content, encoding="utf-8")
    return True


def is_markdown_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".md"


def discover_markdown_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*.md") if p.is_file()])


def make_index_md(title: str, items: list[tuple[str, str]], generated_at: str) -> str:
    lines = [
        "---",
        "tipo: indice",
        "dominio: docs",
        "camada: navegacao",
        "gerado: true",
        f'ultima_geracao: "{generated_at}"',
        "---",
        "",
        f"# {title}",
        "",
    ]
    if not items:
        lines.append("- (sem arquivos encontrados)")
        lines.append("")
        return "\n".join(lines)

    for label, link in items:
        lines.append(f"- [[{link}|{label}]]")
    lines.append("")
    return "\n".join(lines)


def sync_source(source: MirrorSource, *, generated_at: str) -> tuple[int, int, list[str]]:
    out_root = OUT_BASE / source.key
    files = discover_markdown_files(source.root)
    changed = 0
    total = 0
    created_paths: list[str] = []

    for src in files:
        total += 1
        rel = src.relative_to(source.root)
        out = out_root / rel
        origin = normalize_rel(Path(source.key) / rel)
        txt = src.read_text(encoding="utf-8")
        payload = inject_frontmatter(txt, origin=origin, generated_at=generated_at)
        if write_text_if_changed(out, payload):
            changed += 1
        created_paths.append(normalize_rel(out.relative_to(VAULT)))

    md_files = sorted([p for p in out_root.rglob("*.md") if p.is_file()])
    top_dirs = sorted(
        {p.relative_to(out_root).parts[0] for p in md_files if len(p.relative_to(out_root).parts) > 1},
        key=lambda x: x.lower(),
    )

    for top in top_dirs:
        subdir = out_root / top
        sub_md = sorted([p for p in subdir.rglob("*.md") if p.is_file()])
        sub_items: list[tuple[str, str]] = []
        for f in sub_md:
            if f.name.lower() == "index.md":
                continue
            link = f.relative_to(VAULT).as_posix()[:-3]
            label = f.relative_to(subdir).as_posix()[:-3]
            sub_items.append((label, link))
        write_text_if_changed(subdir / "Index.md", make_index_md(f"{source.key}/{top}", sub_items, generated_at))

    root_items: list[tuple[str, str]] = []
    for f in md_files:
        if f.name.lower() == "index.md":
            continue
        if f.parent == out_root:
            root_items.append((f.stem, f.relative_to(VAULT).as_posix()[:-3]))
    for top in top_dirs:
        root_items.append((top, (out_root / top / "Index.md").relative_to(VAULT).as_posix()[:-3]))

    write_text_if_changed(out_root / "Index.md", make_index_md(f"{source.key} (espelhado)", root_items, generated_at))

    return total, changed, created_paths


def main() -> int:
    if not VAULT.exists():
        raise FileNotFoundError(f"Vault não encontrado em {VAULT}")

    generated_at = now_iso()
    OUT_BASE.mkdir(parents=True, exist_ok=True)

    summary: list[tuple[str, int, int]] = []
    for key, root in SOURCE_DIRS:
        src = MirrorSource(key=key, root=root)
        total, changed, _ = sync_source(src, generated_at=generated_at)
        summary.append((key, total, changed))

    index_items = [(k, f"08 - Documentação do Repositório (Gerado)/{k}/Index") for k, _, _ in summary]
    write_text_if_changed(
        OUT_BASE / "Index.md",
        make_index_md("Documentação do Repositório (Gerado)", index_items, generated_at),
    )

    stats_lines = [
        "---",
        "tipo: diagnostico",
        "dominio: docs",
        "camada: validacao",
        "gerado: true",
        f'ultima_geracao: "{generated_at}"',
        "---",
        "",
        "# Estatísticas de espelhamento",
        "",
    ]
    for key, total, changed in summary:
        stats_lines.append(f"- {key}: {total} arquivos (.md), {changed} escritos/atualizados")
    stats_lines.append("")
    write_text_if_changed(OUT_BASE / "Estatísticas.md", "\n".join(stats_lines))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
