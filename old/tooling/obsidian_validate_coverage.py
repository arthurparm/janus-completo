#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "obsidian" / "Janus"

BACKEND_APP = ROOT / "backend" / "app"
BACKEND_ENDPOINTS = BACKEND_APP / "api" / "v1" / "endpoints"
BACKEND_SERVICES = BACKEND_APP / "services"
BACKEND_REPOSITORIES = BACKEND_APP / "repositories"
BACKEND_MODELS = BACKEND_APP / "models"
BACKEND_WORKERS = BACKEND_APP / "core" / "workers"

BACKEND_SCRIPTS = ROOT / "backend" / "scripts"
TOOLING_SCRIPTS = ROOT / "tooling"

OUT_BASE = VAULT / "09 - Código (Gerado)"
OUT_BACKEND = OUT_BASE / "Backend"
OUT_FRONTEND = OUT_BASE / "Frontend"

FRONTEND_APP = ROOT / "frontend" / "src" / "app"

OBS_INVENTORY_SERVICES = VAULT / "07 - Glossário e Inventários" / "Inventário de Serviços.md"
OBS_INVENTORY_MODELS = VAULT / "07 - Glossário e Inventários" / "Inventário de Entidades.md"
OBS_INVENTORY_ENDPOINTS = VAULT / "07 - Glossário e Inventários" / "Inventário de Endpoints.md"


OUT_JSON = ROOT / "outputs" / "qa" / "obsidian_doc_coverage.json"
OUT_CHECKLIST = VAULT / "06 - Qualidade e Testes" / "Checklist de Cobertura Obsidian (Gerado).md"

DOC_OUT_BASE = VAULT / "08 - Documentação do Repositório (Gerado)"


def rel_repo(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
    rel2 = module_file.relative_to(FRONTEND_APP).with_suffix("").as_posix()
    return OUT_FRONTEND / f"{rel2}.md"


def discover_frontend_ts_files() -> list[Path]:
    if not FRONTEND_APP.exists():
        return []
    out: list[Path] = []
    for p in FRONTEND_APP.rglob("*.ts"):
        if not p.is_file():
            continue
        if p.name.lower().endswith(".spec.ts"):
            continue
        out.append(p)
    return sorted(out)


def find_missing_frontend_notes(files: list[Path]) -> list[str]:
    missing: list[str] = []
    for f in files:
        note = note_path_for_frontend(f)
        if not note.exists():
            missing.append(f"{rel_repo(f)} -> {note.relative_to(VAULT).as_posix()}")
    return missing


@dataclass(frozen=True)
class CoverageResult:
    name: str
    expected: int
    present: int
    missing: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_missing_notes(layer: str, files: list[Path]) -> list[str]:
    missing: list[str] = []
    for f in files:
        note = note_path_for_backend(layer, f)
        if not note.exists():
            missing.append(f"{rel_repo(f)} -> {note.relative_to(VAULT).as_posix()}")
    return missing


def validate_inventory_contains_all(md_path: Path, items: list[str]) -> list[str]:
    if not md_path.exists():
        return [f"arquivo inexistente: {md_path.relative_to(ROOT).as_posix()}"]
    txt = read_text(md_path)
    missing: list[str] = []
    for it in items:
        needle = f"`{it}`"
        if needle not in txt:
            missing.append(it)
    return missing


def list_markdown_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("*.md") if p.is_file()])


def expected_mirrors() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []

    doc_src = ROOT / "documentation"
    doc_out = DOC_OUT_BASE / "documentation"
    for src in list_markdown_files(doc_src):
        rel = src.relative_to(doc_src)
        pairs.append((src, doc_out / rel))

    backend_docs_src = ROOT / "backend" / "docs"
    backend_docs_out = DOC_OUT_BASE / "backend-docs"
    if backend_docs_src.exists():
        for src in list_markdown_files(backend_docs_src):
            rel = src.relative_to(backend_docs_src)
            pairs.append((src, backend_docs_out / rel))

    return pairs


def validate_mirrors() -> CoverageResult:
    missing: list[str] = []
    pairs = expected_mirrors()
    for src, out in pairs:
        if not out.exists():
            missing.append(f"{rel_repo(src)} -> {out.relative_to(VAULT).as_posix()}")
    return CoverageResult(
        name="mirror_docs",
        expected=len(pairs),
        present=len(pairs) - len(missing),
        missing=missing,
    )


def write_report(results: list[CoverageResult], *, generated_at: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "repo_root": str(ROOT),
        "vault_root": str(VAULT),
        "results": [
            {
                "name": r.name,
                "expected": r.expected,
                "present": r.present,
                "missing_count": len(r.missing),
                "missing": r.missing,
            }
            for r in results
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_checklist(report: dict[str, Any]) -> None:
    generated_at = report.get("generated_at") or now_iso()
    lines = [
        "---",
        "tipo: qualidade",
        "dominio: testes",
        "camada: validacao",
        "gerado: true",
        f'ultima_geracao: "{generated_at}"',
        "---",
        "",
        "# Checklist de Cobertura Obsidian (Gerado)",
        "",
        "## Critérios",
        "- 0 itens faltantes em cada categoria de cobertura crítica.",
        "- Espelhamento completo de `documentation/**` (Markdown) para a área gerada do vault.",
        "",
        "## Resultados",
        "",
    ]

    for r in report.get("results") or []:
        name = r.get("name")
        expected = int(r.get("expected") or 0)
        present = int(r.get("present") or 0)
        missing_count = int(r.get("missing_count") or 0)
        ok = missing_count == 0 and expected == present
        box = "x" if ok else " "
        lines.append(f"- [{box}] {name}: {present}/{expected} (faltando={missing_count})")

    lines.extend(["", "## Evidências (faltas)", ""])

    for r in report.get("results") or []:
        missing = r.get("missing") or []
        if not missing:
            continue
        lines.append(f"### {r.get('name')}")
        for item in missing[:200]:
            lines.append(f"- `{item}`")
        if len(missing) > 200:
            lines.append(f"- (truncado: {len(missing) - 200} itens adicionais)")
        lines.append("")

    OUT_CHECKLIST.parent.mkdir(parents=True, exist_ok=True)
    OUT_CHECKLIST.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not VAULT.exists():
        raise FileNotFoundError(f"Vault não encontrado em {VAULT}")

    generated_at = now_iso()

    endpoint_files = discover_files(BACKEND_ENDPOINTS, suffix=".py", exclude={"__init__.py"})
    service_files = discover_files(BACKEND_SERVICES, suffix=".py", exclude={"__init__.py"})
    repo_files = discover_files(BACKEND_REPOSITORIES, suffix=".py", exclude={"__init__.py"})
    model_files = discover_files(BACKEND_MODELS, suffix=".py", exclude={"__init__.py"})
    worker_files = discover_files(BACKEND_WORKERS, suffix=".py", exclude={"__init__.py"})
    backend_script_files = discover_files(BACKEND_SCRIPTS, suffix=".py", exclude=set())
    tooling_script_files = discover_files(TOOLING_SCRIPTS, suffix=".py", exclude=set())
    frontend_ts_files = discover_frontend_ts_files()

    results: list[CoverageResult] = []
    results.append(
        CoverageResult(
            name="backend_api_notes",
            expected=len(endpoint_files),
            present=len(endpoint_files) - len(find_missing_notes("api", endpoint_files)),
            missing=find_missing_notes("api", endpoint_files),
        )
    )
    results.append(
        CoverageResult(
            name="backend_services_notes",
            expected=len(service_files),
            present=len(service_files) - len(find_missing_notes("services", service_files)),
            missing=find_missing_notes("services", service_files),
        )
    )
    results.append(
        CoverageResult(
            name="backend_repositories_notes",
            expected=len(repo_files),
            present=len(repo_files) - len(find_missing_notes("repositories", repo_files)),
            missing=find_missing_notes("repositories", repo_files),
        )
    )
    results.append(
        CoverageResult(
            name="backend_models_notes",
            expected=len(model_files),
            present=len(model_files) - len(find_missing_notes("models", model_files)),
            missing=find_missing_notes("models", model_files),
        )
    )
    results.append(
        CoverageResult(
            name="backend_workers_notes",
            expected=len(worker_files),
            present=len(worker_files) - len(find_missing_notes("workers", worker_files)),
            missing=find_missing_notes("workers", worker_files),
        )
    )
    scripts = backend_script_files + tooling_script_files
    results.append(
        CoverageResult(
            name="backend_scripts_notes",
            expected=len(scripts),
            present=len(scripts) - len(find_missing_notes("scripts", scripts)),
            missing=find_missing_notes("scripts", scripts),
        )
    )
    results.append(
        CoverageResult(
            name="frontend_ts_notes",
            expected=len(frontend_ts_files),
            present=len(frontend_ts_files) - len(find_missing_frontend_notes(frontend_ts_files)),
            missing=find_missing_frontend_notes(frontend_ts_files),
        )
    )

    results.append(validate_mirrors())

    service_items = sorted([p.stem for p in service_files])
    model_items = sorted([p.stem for p in model_files])
    endpoint_items = sorted(
        [p.relative_to(BACKEND_ENDPOINTS).with_suffix("").as_posix() for p in endpoint_files]
    )

    results.append(
        CoverageResult(
            name="obsidian_inventory_services",
            expected=len(service_items),
            present=len(service_items) - len(validate_inventory_contains_all(OBS_INVENTORY_SERVICES, service_items)),
            missing=validate_inventory_contains_all(OBS_INVENTORY_SERVICES, service_items),
        )
    )
    results.append(
        CoverageResult(
            name="obsidian_inventory_models",
            expected=len(model_items),
            present=len(model_items) - len(validate_inventory_contains_all(OBS_INVENTORY_MODELS, model_items)),
            missing=validate_inventory_contains_all(OBS_INVENTORY_MODELS, model_items),
        )
    )
    results.append(
        CoverageResult(
            name="obsidian_inventory_endpoints",
            expected=len(endpoint_items),
            present=len(endpoint_items) - len(validate_inventory_contains_all(OBS_INVENTORY_ENDPOINTS, endpoint_items)),
            missing=validate_inventory_contains_all(OBS_INVENTORY_ENDPOINTS, endpoint_items),
        )
    )

    report = write_report(results, generated_at=generated_at)
    write_checklist(report)

    missing_total = sum(int(r.get("missing_count") or 0) for r in report.get("results") or [])
    return 0 if missing_total == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
