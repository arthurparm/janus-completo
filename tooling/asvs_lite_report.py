import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

RequirementStatus = Literal[
    "implemented", "planned", "in_progress", "deprecated", "not_applicable"
]
Severity = Literal["P0", "P1", "P2", "P3"]
EvidenceType = Literal["code", "test", "doc", "ops"]


class EvidenceItem(BaseModel):
    type: EvidenceType
    path: str = Field(min_length=1)


class Requirement(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    level: str = ""
    severity: Severity
    weight: int = Field(gt=0)
    status: RequirementStatus
    evidence: list[EvidenceItem] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _format_md(report: dict) -> str:
    lines: list[str] = []
    summary = report.get("summary") or {}
    score = report.get("score") or {}
    lines.append("# ASVS-lite Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total requirements: {summary.get('total')}")
    lines.append(f"- Implemented: {summary.get('implemented')}")
    lines.append(f"- Incomplete: {summary.get('incomplete')}")
    lines.append(f"- Score: {score.get('percent'):.2%} ({score.get('achieved_points')}/{score.get('max_points')})")
    lines.append("")
    lines.append("## Requirements")
    lines.append("")
    lines.append("| ID | Severity | Status | Weight | Title | Evidence |")
    lines.append("|---|---|---|---:|---|---|")
    for item in report.get("requirements") or []:
        ev = item.get("evidence") or []
        lines.append(
            f"| {item.get('id')} | {item.get('severity')} | {item.get('status')} | {item.get('weight')} | {item.get('title')} | {len(ev)} |"
        )
    lines.append("")
    failures = report.get("failures") or []
    if failures:
        lines.append("## Gate Failures")
        lines.append("")
        for f in failures:
            lines.append(f"- {f}")
        lines.append("")
    missing_evidence = report.get("missing_evidence") or []
    if missing_evidence:
        lines.append("## Missing Evidence")
        lines.append("")
        for f in missing_evidence:
            lines.append(f"- {f}")
        lines.append("")
    return "\n".join(lines)


def _requirement_id(raw: object) -> str:
    if isinstance(raw, dict):
        rid = str(raw.get("id") or "").strip()
        if rid:
            return rid
    return "<missing-id>"


def _validate_and_score(repo_root: Path, spec_path: Path) -> tuple[dict, list[str], list[str]]:
    payload = _read_json(spec_path)
    raw_requirements = payload.get("requirements") or []
    if not isinstance(raw_requirements, list):
        raise ValueError("requirements must be a list")

    missing_evidence: list[str] = []
    structural_errors: list[str] = []

    max_points = 0
    achieved_points = 0
    implemented = 0
    incomplete = 0

    normalized_items: list[dict] = []

    for raw_req in raw_requirements:
        rid = _requirement_id(raw_req)
        try:
            req = Requirement.model_validate(raw_req)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                structural_errors.append(f"{rid}: {loc}: {err['msg']}" if loc else f"{rid}: {err['msg']}")
            continue

        for ev in req.evidence:
            target = (repo_root / ev.path).resolve()
            if not target.exists():
                missing_evidence.append(f"{req.id}: missing file {ev.path}")

        max_points += req.weight
        if req.status == "implemented":
            implemented += 1
            achieved_points += req.weight
            if not req.evidence:
                missing_evidence.append(f"{req.id}: implemented requirements must have evidence")
        else:
            incomplete += 1

        normalized_items.append(
            {
                "id": req.id,
                "title": req.title,
                "level": req.level,
                "severity": req.severity,
                "weight": req.weight,
                "status": req.status,
                "tags": req.tags,
                "evidence": [item.model_dump() for item in req.evidence],
            }
        )

    percent = (achieved_points / max_points) if max_points > 0 else 0.0
    report = {
        "summary": {
            "total": len(normalized_items),
            "implemented": implemented,
            "incomplete": incomplete,
        },
        "score": {
            "achieved_points": achieved_points,
            "max_points": max_points,
            "percent": percent,
        },
        "requirements": normalized_items,
        "missing_evidence": missing_evidence,
        "structural_errors": structural_errors,
    }
    return report, missing_evidence, structural_errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        default="documentation/security/asvs-lite/asvs-lite.json",
        help="Path to ASVS-lite spec JSON (relative to repo root).",
    )
    parser.add_argument("--json-out", default="outputs/qa/asvs_lite_report.json")
    parser.add_argument("--md-out", default="outputs/qa/asvs_lite_report.md")
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--fail-on-p0-missing", action="store_true")
    parser.add_argument("--fail-on-missing-evidence", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / args.spec).resolve()
    report, missing_evidence, structural_errors = _validate_and_score(
        repo_root=repo_root, spec_path=spec_path
    )

    failures: list[str] = []
    if structural_errors:
        failures.append("invalid_spec_structure")
    if args.fail_on_missing_evidence and missing_evidence:
        failures.append("missing_evidence")

    min_score = args.min_score
    if min_score is None:
        try:
            min_score = float(_read_json(spec_path).get("min_score_percent"))
        except Exception:
            min_score = None
    if min_score is not None:
        if float(report["score"]["percent"]) < float(min_score):
            failures.append(f"score_below_threshold:{min_score}")

    if args.fail_on_p0_missing:
        for item in report.get("requirements") or []:
            if item.get("severity") == "P0" and item.get("status") != "implemented":
                failures.append(f"missing_p0:{item.get('id')}")

    report["failures"] = failures

    _write_json((repo_root / args.json_out).resolve(), report)
    _write_text((repo_root / args.md_out).resolve(), _format_md(report))

    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
