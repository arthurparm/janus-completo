#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "obsidian" / "Janus"
OUT_BASE = VAULT / "09 - Código (Gerado)"
OUT_BACKEND = OUT_BASE / "Backend"
OUT_FRONTEND = OUT_BASE / "Frontend"

OUT_INVENTORY_JSON = ROOT / "outputs" / "qa" / "obsidian_code_inventory.json"

BACKEND_APP = ROOT / "backend" / "app"
BACKEND_ENDPOINTS = BACKEND_APP / "api" / "v1" / "endpoints"
BACKEND_SERVICES = BACKEND_APP / "services"
BACKEND_REPOSITORIES = BACKEND_APP / "repositories"
BACKEND_MODELS = BACKEND_APP / "models"
BACKEND_WORKERS = BACKEND_APP / "core" / "workers"

BACKEND_SCRIPTS = ROOT / "backend" / "scripts"
TOOLING_SCRIPTS = ROOT / "tooling"

FRONTEND_APP = ROOT / "frontend" / "src" / "app"

OBS_INVENTORY_SERVICES = VAULT / "07 - Glossário e Inventários" / "Inventário de Serviços.md"
OBS_INVENTORY_MODELS = VAULT / "07 - Glossário e Inventários" / "Inventário de Entidades.md"
OBS_INVENTORY_ENDPOINTS = VAULT / "07 - Glossário e Inventários" / "Inventário de Endpoints.md"
OBS_INVENTORY_WORKERS = VAULT / "07 - Glossário e Inventários" / "Inventário de Workers.md"

API_MATRIX_JSON = ROOT / "documentation" / "qa" / "api-endpoint-matrix.json"


@dataclass(frozen=True)
class SymbolSignature:
    kind: str
    name: str
    signature: str
    returns: str | None
    doc: str | None


@dataclass(frozen=True)
class ModuleInventory:
    layer: str
    relpath: str
    symbols: list[SymbolSignature]
    doc: str | None
    routes: list[str]
    queues: list[str]
    imports_services: list[str]
    imports_repositories: list[str]
    callers: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel_repo(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def rel_vault(path: Path) -> str:
    return path.relative_to(VAULT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def discover_files(root: Path, *, suffix: str, exclude: set[str] | None = None) -> list[Path]:
    if not root.exists():
        return []
    exclude = exclude or set()
    out: list[Path] = []
    for p in root.rglob(f"*{suffix}"):
        if not p.is_file():
            continue
        if p.name in exclude:
            continue
        out.append(p)
    return sorted(out)


def format_annotation(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def format_arguments(args: ast.arguments) -> str:
    parts: list[str] = []

    def fmt_arg(a: ast.arg, default: ast.AST | None) -> str:
        s = a.arg
        ann = format_annotation(a.annotation)
        if ann:
            s += f": {ann}"
        if default is not None:
            try:
                s += f" = {ast.unparse(default)}"
            except Exception:
                s += " = <default>"
        return s

    posonly = list(args.posonlyargs or [])
    normal = list(args.args or [])
    kwonly = list(args.kwonlyargs or [])

    defaults = list(args.defaults or [])
    total_pos = len(posonly) + len(normal)
    defaults_pad = [None] * (total_pos - len(defaults)) + defaults

    for i, a in enumerate(posonly):
        parts.append(fmt_arg(a, defaults_pad[i]))
    if posonly:
        parts.append("/")

    for i, a in enumerate(normal, start=len(posonly)):
        parts.append(fmt_arg(a, defaults_pad[i]))

    if args.vararg is not None:
        va = args.vararg
        s = f"*{va.arg}"
        ann = format_annotation(va.annotation)
        if ann:
            s += f": {ann}"
        parts.append(s)
    elif kwonly:
        parts.append("*")

    for i, a in enumerate(kwonly):
        d = None
        if args.kw_defaults and i < len(args.kw_defaults):
            d = args.kw_defaults[i]
        parts.append(fmt_arg(a, d))

    if args.kwarg is not None:
        ka = args.kwarg
        s = f"**{ka.arg}"
        ann = format_annotation(ka.annotation)
        if ann:
            s += f": {ann}"
        parts.append(s)

    return ", ".join([p for p in parts if p])


def first_paragraph(doc: str | None) -> str | None:
    if not doc:
        return None
    s = doc.strip()
    if not s:
        return None
    return s.split("\n\n", 1)[0].strip()


def extract_python_symbols(tree: ast.Module) -> list[SymbolSignature]:
    out: list[SymbolSignature] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = format_arguments(node.args)
            ret = format_annotation(node.returns)
            sig = f"{node.name}({args})"
            out.append(
                SymbolSignature(
                    kind="function",
                    name=node.name,
                    signature=sig,
                    returns=ret,
                    doc=first_paragraph(ast.get_docstring(node)),
                )
            )
        elif isinstance(node, ast.ClassDef):
            out.append(
                SymbolSignature(
                    kind="class",
                    name=node.name,
                    signature=node.name,
                    returns=None,
                    doc=first_paragraph(ast.get_docstring(node)),
                )
            )
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = format_arguments(child.args)
                    ret = format_annotation(child.returns)
                    sig = f"{node.name}.{child.name}({args})"
                    out.append(
                        SymbolSignature(
                            kind="method",
                            name=f"{node.name}.{child.name}",
                            signature=sig,
                            returns=ret,
                            doc=first_paragraph(ast.get_docstring(child)),
                        )
                    )

    return out


def parse_python_module(path: Path) -> tuple[str | None, list[SymbolSignature]]:
    try:
        txt = read_text(path)
        tree = ast.parse(txt, filename=str(path))
    except Exception:
        return None, []

    return first_paragraph(ast.get_docstring(tree)), extract_python_symbols(tree)


def extract_endpoint_routes(text: str) -> list[str]:
    routes: list[str] = []
    for m in re.finditer(r"@router\.(get|post|put|patch|delete)\(\s*([\"'])(.+?)\2", text):
        routes.append(f"{m.group(1).upper()} {m.group(3)}")
    return sorted(set(routes))


def extract_queue_names(text: str) -> list[str]:
    found: set[str] = set()
    for m in re.finditer(r"(janus\.[a-z0-9_.-]+)", text, flags=re.IGNORECASE):
        found.add(m.group(1))
    for m in re.finditer(r"\bQueueName\.([A-Z0-9_]+)\b", text):
        found.add(f"QueueName.{m.group(1)}")
    return sorted(found)


def extract_imported_modules(text: str, *, prefix: str) -> list[str]:
    found: set[str] = set()
    p_from = re.compile(rf"^\s*from\s+{re.escape(prefix)}\.([a-zA-Z0-9_]+)\s+import\s+", flags=re.M)
    p_import = re.compile(rf"^\s*import\s+{re.escape(prefix)}\.([a-zA-Z0-9_]+)\b", flags=re.M)
    for m in p_from.finditer(text):
        found.add(m.group(1))
    for m in p_import.finditer(text):
        found.add(m.group(1))
    return sorted(found)


def build_import_index(files: Iterable[Path]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    p = re.compile(r"^\s*(?:from|import)\s+app\.(services|repositories|models)\.([a-zA-Z0-9_]+)", flags=re.M)
    for f in files:
        try:
            txt = read_text(f)
        except Exception:
            continue
        for m in p.finditer(txt):
            mod = f"app.{m.group(1)}.{m.group(2)}"
            index.setdefault(mod, []).append(rel_repo(f))
    for k in list(index.keys()):
        index[k] = sorted(set(index[k]))
    return index


def build_frontmatter(
    *,
    title: str,
    domain: str,
    layer: str,
    origin: str,
    generated_at: str,
) -> str:
    return "\n".join(
        [
            "---",
            "tipo: codigo",
            f"dominio: {domain}",
            f"camada: {layer}",
            "gerado: true",
            f'origem: "{origin}"',
            f'ultima_geracao: "{generated_at}"',
            "status: ativo",
            "---",
            "",
            f"# {title}",
            "",
        ]
    )


def render_module_note(inv: ModuleInventory, *, title: str, domain: str, generated_at: str) -> str:
    fm = build_frontmatter(
        title=title,
        domain=domain,
        layer=inv.layer,
        origin=inv.relpath,
        generated_at=generated_at,
    )
    lines = [fm]

    if inv.doc:
        lines.extend(["## Objetivo", inv.doc, ""])

    lines.extend(["## Arquivos-fonte", f"- `{inv.relpath}`", ""])

    if inv.routes:
        lines.extend(["## Rotas", *[f"- `{r}`" for r in inv.routes], ""])

    if inv.queues:
        lines.extend(["## Filas/loops observáveis", *[f"- `{q}`" for q in inv.queues], ""])

    if inv.imports_services or inv.imports_repositories:
        lines.append("## Dependências de código")
        if inv.imports_services:
            lines.append("- Serviços")
            lines.extend([f"  - `{m}`" for m in inv.imports_services])
        if inv.imports_repositories:
            lines.append("- Repositórios")
            lines.extend([f"  - `{m}`" for m in inv.imports_repositories])
        lines.append("")

    if inv.callers:
        lines.extend(["## Fluxos de uso (chamadores)", *[f"- `{c}`" for c in inv.callers], ""])

    if inv.symbols:
        lines.append("## Símbolos")
        for s in inv.symbols:
            header = f"- {s.kind}: `{s.signature}`"
            if s.returns:
                header += f" -> `{s.returns}`"
            lines.append(header)
            if s.doc:
                lines.append(f"  - {s.doc}")
        lines.append("")

    lines.append("## Observações")
    lines.append("- Esta nota é gerada automaticamente a partir do código-fonte.")
    lines.append("")

    return "\n".join(lines)


def note_path_for_backend(layer: str, module_file: Path) -> Path:
    rel = module_file.relative_to(ROOT).as_posix()
    if layer == "api":
        rel2 = module_file.relative_to(BACKEND_ENDPOINTS).with_suffix("").as_posix()
        return OUT_BACKEND / "API" / f"{rel2}.md"
    if layer == "services":
        return OUT_BACKEND / "Services" / f"{module_file.stem}.md"
    if layer == "repositories":
        return OUT_BACKEND / "Repositories" / f"{module_file.stem}.md"
    if layer == "models":
        return OUT_BACKEND / "Models" / f"{module_file.stem}.md"
    if layer == "workers":
        rel2 = module_file.relative_to(BACKEND_WORKERS).with_suffix("").as_posix()
        return OUT_BACKEND / "Workers" / f"{rel2}.md"
    if layer == "scripts":
        if rel.startswith("tooling/"):
            rel2 = module_file.relative_to(TOOLING_SCRIPTS).with_suffix("").as_posix()
            return OUT_BACKEND / "Scripts" / "tooling" / f"{rel2}.md"
        rel2 = module_file.relative_to(BACKEND_SCRIPTS).with_suffix("").as_posix()
        return OUT_BACKEND / "Scripts" / "backend-scripts" / f"{rel2}.md"
    raise ValueError(f"layer não suportada: {layer}")


def note_path_for_frontend(module_file: Path) -> Path:
    rel = module_file.relative_to(FRONTEND_APP).with_suffix("").as_posix()
    return OUT_FRONTEND / f"{rel}.md"


def discover_frontend_ts_files() -> list[Path]:
    if not FRONTEND_APP.exists():
        return []
    out: list[Path] = []
    for p in FRONTEND_APP.rglob("*.ts"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if name.endswith(".spec.ts"):
            continue
        out.append(p)
    return sorted(out)


def extract_ts_doc(text: str) -> str | None:
    m = re.search(r"^\s*/\*\*(.*?)\*/", text, flags=re.S)
    if not m:
        return None
    body = m.group(1)
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("*"):
            s = s[1:].lstrip()
        if s:
            lines.append(s)
    return first_paragraph("\n".join(lines))


def extract_ts_symbols(text: str) -> list[SymbolSignature]:
    out: list[SymbolSignature] = []

    for m in re.finditer(r"\bexport\s+function\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*(?::\s*([^\\{;]+))?", text):
        name = m.group(1)
        args = " ".join(m.group(2).split())
        ret = (m.group(3) or "").strip() or None
        sig = f"{name}({args})"
        out.append(SymbolSignature(kind="function", name=name, signature=sig, returns=ret, doc=None))

    for m in re.finditer(r"\bexport\s+class\s+([A-Za-z0-9_]+)", text):
        name = m.group(1)
        ctor = None
        m_ctor = re.search(rf"\bclass\s+{re.escape(name)}\b[\s\S]*?\bconstructor\s*\(([^)]*)\)", text)
        if m_ctor:
            ctor = " ".join(m_ctor.group(1).split())
        sig = name if ctor is None else f"{name}.constructor({ctor})"
        out.append(SymbolSignature(kind="class", name=name, signature=sig, returns=None, doc=None))

    return out


def parse_ts_module(path: Path) -> tuple[str | None, list[SymbolSignature]]:
    try:
        txt = read_text(path)
    except Exception:
        return None, []
    return extract_ts_doc(txt), extract_ts_symbols(txt)


def sanitize_obsidian_link(p: Path) -> str:
    rel = p.relative_to(VAULT).as_posix()
    if rel.lower().endswith(".md"):
        rel = rel[:-3]
    return rel


def write_index(index_path: Path, *, title: str, notes: list[Path], generated_at: str) -> None:
    lines = [
        "---",
        "tipo: indice",
        "dominio: codigo",
        "camada: navegacao",
        "gerado: true",
        f'ultima_geracao: "{generated_at}"',
        "---",
        "",
        f"# {title}",
        "",
    ]
    if not notes:
        lines.append("- (sem itens)")
        lines.append("")
        write_text(index_path, "\n".join(lines))
        return
    for note in sorted(notes, key=lambda x: x.as_posix().lower()):
        link = sanitize_obsidian_link(note)
        label = note.parent.name if note.stem.lower() == "index" else note.stem
        lines.append(f"- [[{link}|{label}]]")
    lines.append("")
    write_text(index_path, "\n".join(lines))


def update_section_list(md_path: Path, *, header: str, items: list[str]) -> None:
    if not md_path.exists():
        return
    txt = read_text(md_path)
    m = re.search(rf"(?m)^\#\#\s+{re.escape(header)}\s*$", txt)
    if not m:
        return
    start = m.end()
    next_h = re.search(r"(?m)^\#\#\s+", txt[start:])
    end = start + (next_h.start() if next_h else len(txt[start:]))
    before = txt[:start]
    after = txt[end:]
    body = "\n" + "\n".join([f"- `{i}`" for i in items]) + "\n"
    write_text(md_path, before + body + after)


def update_services_inventory(service_files: list[Path]) -> None:
    items = [p.stem for p in service_files if p.name != "__init__.py"]
    update_section_list(OBS_INVENTORY_SERVICES, header="Serviços", items=sorted(items))


def update_models_inventory(model_files: list[Path]) -> None:
    items = [p.stem for p in model_files if p.name != "__init__.py"]
    update_section_list(OBS_INVENTORY_MODELS, header="Modelos", items=sorted(items))


def update_endpoints_inventory(endpoint_files: list[Path]) -> None:
    items: list[str] = []
    for p in endpoint_files:
        rel = p.relative_to(BACKEND_ENDPOINTS).with_suffix("").as_posix()
        items.append(rel)
    update_section_list(OBS_INVENTORY_ENDPOINTS, header="Módulos", items=sorted(items))


def update_workers_inventory(worker_files: list[Path]) -> None:
    items: list[str] = []
    for p in worker_files:
        rel = p.relative_to(BACKEND_WORKERS).with_suffix("").as_posix()
        items.append(rel)
    update_section_list(OBS_INVENTORY_WORKERS, header="Arquivos de workers que não viram nome próprio em `/workers/status`", items=sorted(items))


def load_api_matrix_modules() -> dict[str, list[str]]:
    if not API_MATRIX_JSON.exists():
        return {}
    raw = json.loads(API_MATRIX_JSON.read_text(encoding="utf-8"))
    rows = raw.get("rows") or raw.get("endpoints") or []
    mod_map: dict[str, set[str]] = {}
    for r in rows:
        mod = str(r.get("module") or "").strip() or "unknown"
        method = str(r.get("method") or "").upper() or "GET"
        path = str(r.get("path") or "").strip()
        if not path:
            continue
        mod_map.setdefault(mod, set()).add(f"{method} {path}")
    return {k: sorted(v) for k, v in mod_map.items()}


def main() -> int:
    if not VAULT.exists():
        raise FileNotFoundError(f"Vault não encontrado em {VAULT}")

    generated_at = now_iso()
    OUT_BASE.mkdir(parents=True, exist_ok=True)

    backend_py_files = discover_files(BACKEND_APP, suffix=".py", exclude=set())
    import_index = build_import_index(backend_py_files)

    service_files = discover_files(BACKEND_SERVICES, suffix=".py", exclude={"__init__.py"})
    repo_files = discover_files(BACKEND_REPOSITORIES, suffix=".py", exclude={"__init__.py"})
    model_files = discover_files(BACKEND_MODELS, suffix=".py", exclude={"__init__.py"})
    worker_files = discover_files(BACKEND_WORKERS, suffix=".py", exclude={"__init__.py"})
    endpoint_files = discover_files(BACKEND_ENDPOINTS, suffix=".py", exclude={"__init__.py"})
    backend_script_files = discover_files(BACKEND_SCRIPTS, suffix=".py", exclude=set())
    tooling_script_files = discover_files(TOOLING_SCRIPTS, suffix=".py", exclude=set())

    update_services_inventory(service_files)
    update_models_inventory(model_files)
    update_endpoints_inventory(endpoint_files)

    api_routes_by_module = load_api_matrix_modules()

    inventories: dict[str, list[ModuleInventory]] = {"backend": [], "frontend": []}
    written_notes: dict[str, list[str]] = {"backend": [], "frontend": []}

    def emit_backend(layer: str, module_file: Path) -> None:
        relpath = rel_repo(module_file)
        doc, symbols = parse_python_module(module_file)
        txt = read_text(module_file)

        routes: list[str] = []
        queues: list[str] = []
        imports_services: list[str] = []
        imports_repositories: list[str] = []
        callers: list[str] = []

        if layer == "api":
            routes = extract_endpoint_routes(txt)
            tag = module_file.relative_to(BACKEND_ENDPOINTS).with_suffix("").as_posix().split("/", 1)[0]
            if tag in api_routes_by_module:
                routes = sorted(set(routes + api_routes_by_module[tag]))
            imports_services = extract_imported_modules(txt, prefix="app.services")
            imports_repositories = extract_imported_modules(txt, prefix="app.repositories")
        elif layer == "workers":
            queues = extract_queue_names(txt)
        elif layer in {"services", "repositories"}:
            imports_repositories = extract_imported_modules(txt, prefix="app.repositories")

        mod_key = None
        if layer == "services":
            mod_key = f"app.services.{module_file.stem}"
        elif layer == "repositories":
            mod_key = f"app.repositories.{module_file.stem}"
        elif layer == "models":
            mod_key = f"app.models.{module_file.stem}"
        if mod_key:
            callers = import_index.get(mod_key, [])

        inv = ModuleInventory(
            layer=layer,
            relpath=relpath,
            symbols=symbols,
            doc=doc,
            routes=routes,
            queues=queues,
            imports_services=imports_services,
            imports_repositories=imports_repositories,
            callers=callers,
        )
        inventories["backend"].append(inv)
        note_path = note_path_for_backend(layer, module_file)
        title = module_file.stem if layer != "api" else module_file.relative_to(BACKEND_ENDPOINTS).with_suffix("").as_posix()
        payload = render_module_note(inv, title=title, domain="backend", generated_at=generated_at)
        write_text(note_path, payload)
        written_notes["backend"].append(rel_vault(note_path))

    for f in sorted(endpoint_files):
        emit_backend("api", f)
    for f in sorted(service_files):
        emit_backend("services", f)
    for f in sorted(repo_files):
        emit_backend("repositories", f)
    for f in sorted(model_files):
        emit_backend("models", f)
    for f in sorted(worker_files):
        emit_backend("workers", f)
    for f in sorted(backend_script_files + tooling_script_files):
        emit_backend("scripts", f)

    write_index(
        OUT_BACKEND / "Index.md",
        title="Backend — Código (Gerado)",
        notes=[VAULT / p for p in written_notes["backend"]],
        generated_at=generated_at,
    )

    frontend_ts_files = discover_frontend_ts_files()

    def emit_frontend(module_file: Path) -> None:
        relpath = rel_repo(module_file)
        doc, symbols = parse_ts_module(module_file)
        rel_local = module_file.relative_to(FRONTEND_APP).as_posix()
        top = rel_local.split("/", 1)[0] if "/" in rel_local else "root"

        inv = ModuleInventory(
            layer=f"frontend_{top}",
            relpath=relpath,
            symbols=symbols,
            doc=doc,
            routes=[],
            queues=[],
            imports_services=[],
            imports_repositories=[],
            callers=[],
        )
        inventories["frontend"].append(inv)
        note_path = note_path_for_frontend(module_file)
        title = module_file.relative_to(FRONTEND_APP).with_suffix("").as_posix()
        payload = render_module_note(inv, title=title, domain="frontend", generated_at=generated_at)
        write_text(note_path, payload)
        written_notes["frontend"].append(rel_vault(note_path))

    for f in frontend_ts_files:
        emit_frontend(f)

    top_dirs = sorted(
        {p.relative_to(FRONTEND_APP).parts[0] for p in frontend_ts_files if len(p.relative_to(FRONTEND_APP).parts) > 1},
        key=lambda x: x.lower(),
    )
    for top in top_dirs:
        notes = []
        for p in written_notes["frontend"]:
            note = VAULT / p
            rel_note = note.relative_to(OUT_FRONTEND).as_posix()
            if rel_note.startswith(f"{top}/") and note.name.lower() != "index.md":
                notes.append(note)
        write_index(OUT_FRONTEND / top / "Index.md", title=f"Frontend/{top} — Código (Gerado)", notes=notes, generated_at=generated_at)

    write_index(
        OUT_FRONTEND / "Index.md",
        title="Frontend — Código (Gerado)",
        notes=[OUT_FRONTEND / top / "Index.md" for top in top_dirs],
        generated_at=generated_at,
    )

    def symbol_to_dict(s: SymbolSignature) -> dict[str, Any]:
        return {
            "kind": s.kind,
            "name": s.name,
            "signature": s.signature,
            "returns": s.returns,
            "doc": s.doc,
        }

    def module_to_dict(m: ModuleInventory) -> dict[str, Any]:
        return {
            "layer": m.layer,
            "relpath": m.relpath,
            "doc": m.doc,
            "routes": m.routes,
            "queues": m.queues,
            "imports_services": m.imports_services,
            "imports_repositories": m.imports_repositories,
            "callers": m.callers,
            "symbols": [symbol_to_dict(s) for s in m.symbols],
        }

    out_payload: dict[str, Any] = {
        "generated_at": generated_at,
        "repo_root": str(ROOT),
        "vault_root": str(VAULT),
        "backend": [module_to_dict(inv) for inv in inventories["backend"]],
        "frontend": [module_to_dict(inv) for inv in inventories["frontend"]],
        "written_notes": written_notes,
    }
    OUT_INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_INVENTORY_JSON.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
