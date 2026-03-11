#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


TASK_TYPES = ("codigo", "docs", "deploy")


@dataclass(frozen=True)
class ChecklistItem:
    id: str
    text: str


CHECKLISTS: dict[str, list[ChecklistItem]] = {
    "codigo": [
        ChecklistItem("code-change-scoped", "Escopo da alteracao documentado e sem impacto lateral nao mapeado."),
        ChecklistItem("code-tests-selected", "Testes automatizados relevantes identificados para o fluxo alterado."),
        ChecklistItem("code-quality-gates", "Lint/type/test/build executados ou motivo de excecao registrado."),
        ChecklistItem("code-risk-notes", "Riscos, rollback e pontos de observabilidade registrados."),
    ],
    "docs": [
        ChecklistItem("docs-source-traceability", "Fontes/artefatos de origem citados de forma rastreavel."),
        ChecklistItem("docs-consistency", "Terminologia e versoes alinhadas com README/workflows do repositorio."),
        ChecklistItem("docs-actionability", "Passos de execucao e validacao estao objetivos e reproduziveis."),
        ChecklistItem("docs-review", "Revisao ortografica e tecnica concluida antes da publicacao."),
    ],
    "deploy": [
        ChecklistItem("deploy-target-confirmed", "Ambiente alvo, host e portas confirmados antes do deploy."),
        ChecklistItem("deploy-migrations-safe", "Migracoes e scripts de infraestrutura validados como idempotentes."),
        ChecklistItem("deploy-health-checks", "Health checks e status de servicos definidos para verificacao pos-deploy."),
        ChecklistItem("deploy-rollback-plan", "Plano de rollback e coleta de logs pronto para incidente."),
    ],
}


def build_checklist(task_type: str) -> dict[str, object]:
    if task_type not in CHECKLISTS:
        allowed = ", ".join(TASK_TYPES)
        raise ValueError(f"Invalid task type: {task_type}. Allowed: {allowed}.")
    return {
        "task_type": task_type,
        "items": [{"id": item.id, "text": item.text} for item in CHECKLISTS[task_type]],
    }


def _render_markdown(payload: dict[str, object]) -> str:
    task_type = str(payload["task_type"])
    lines = [f"# Checklist de saida ({task_type})", ""]
    for item in payload["items"]:
        if isinstance(item, dict):
            lines.append(f"- [ ] {item['text']} (`{item['id']}`)")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AG-007 checklist de saida por tipo de tarefa.")
    parser.add_argument("--type", dest="task_type", choices=TASK_TYPES, required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--out", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_checklist(args.task_type)
    content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.format == "markdown":
        content = _render_markdown(payload)

    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(str(output_path))
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
