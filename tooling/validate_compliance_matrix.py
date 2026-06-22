import json
import sys
from pathlib import Path


_ALLOWED_STATUSES = {"implemented", "planned", "in_progress", "deprecated"}
_ALLOWED_EVIDENCE_TYPES = {"code", "test", "doc", "ops"}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_matrix(repo_root: Path, matrix_path: Path) -> list[str]:
    errors: list[str] = []
    payload = _read_json(matrix_path)
    if str(payload.get("classification") or "").strip() != "internal-only":
        errors.append("classification must be 'internal-only'")
    controls = payload.get("controls") or []
    if not isinstance(controls, list):
        return ["controls must be a list"]

    for control in controls:
        if not isinstance(control, dict):
            errors.append("control entry must be an object")
            continue
        cid = str(control.get("id") or "").strip() or "<missing-id>"
        title = str(control.get("title") or "").strip()
        status = str(control.get("status") or "").strip()
        if cid == "<missing-id>":
            errors.append("control missing id")
        if not title:
            errors.append(f"{cid}: missing title")
        if status not in _ALLOWED_STATUSES:
            errors.append(f"{cid}: invalid status '{status}'")

        evidence = control.get("evidence") or []
        if not isinstance(evidence, list):
            errors.append(f"{cid}: evidence must be a list")
            continue
        if status == "implemented" and not evidence:
            errors.append(f"{cid}: implemented controls must have evidence")

        for item in evidence:
            if not isinstance(item, dict):
                errors.append(f"{cid}: evidence item must be an object")
                continue
            etype = str(item.get("type") or "").strip()
            if etype not in _ALLOWED_EVIDENCE_TYPES:
                errors.append(f"{cid}: invalid evidence type '{etype}'")
            rel_path = str(item.get("path") or "").strip()
            if not rel_path:
                errors.append(f"{cid}: evidence item missing path")
                continue
            target = (repo_root / rel_path).resolve()
            if not target.exists():
                errors.append(f"{cid}: missing file {rel_path}")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    matrix_path = repo_root / "documentation" / "compliance" / "compliance-traceability-matrix.json"
    if len(sys.argv) > 1:
        matrix_path = (repo_root / sys.argv[1]).resolve()

    if not matrix_path.exists():
        print(f"Matrix not found: {matrix_path}", file=sys.stderr)
        return 2

    errors = _validate_matrix(repo_root=repo_root, matrix_path=matrix_path)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
