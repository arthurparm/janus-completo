"""Validate documentation/compliance/compliance-traceability-matrix.json against its schema.

Uses pydantic (already a first-class backend dependency) instead of hand-rolled
dict-walking so the shape of a control/evidence entry is declared once and every
error message comes from the same, consistent validator machinery.
"""

import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

ControlStatus = Literal["implemented", "planned", "in_progress", "deprecated"]
EvidenceType = Literal["code", "test", "doc", "ops"]


class EvidenceItem(BaseModel):
    type: EvidenceType
    path: str = Field(min_length=1)


class ControlEntry(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: ControlStatus
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _implemented_controls_need_evidence(self) -> "ControlEntry":
        if self.status == "implemented" and not self.evidence:
            raise ValueError("implemented controls must have evidence")
        return self


class ComplianceMatrix(BaseModel):
    classification: Literal["internal-only"]
    controls: list[ControlEntry]


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_matrix(repo_root: Path, matrix_path: Path) -> list[str]:
    payload = _read_json(matrix_path)
    try:
        matrix = ComplianceMatrix.model_validate(payload)
    except ValidationError as exc:
        return [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        ]

    errors: list[str] = []
    for control in matrix.controls:
        for item in control.evidence:
            if not (repo_root / item.path).resolve().exists():
                errors.append(f"{control.id}: missing file {item.path}")
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
