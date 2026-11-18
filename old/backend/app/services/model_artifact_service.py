from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MODELS_BASE_DIR = Path("/app/workspace/models")


class ModelArtifactError(ValueError):
    """Raised when a model artifact identifier or file is invalid."""


def resolve_model_file(model_id: str, filename: str) -> Path:
    if not MODEL_ID_PATTERN.fullmatch(str(model_id or "")):
        raise ModelArtifactError("Invalid model_id format")
    if Path(filename).name != filename:
        raise ModelArtifactError("Invalid artifact filename")

    base_dir = MODELS_BASE_DIR.resolve()
    model_dir = (base_dir / model_id).resolve()
    try:
        model_dir.relative_to(base_dir)
    except ValueError as exc:
        raise ModelArtifactError("Invalid model artifact path") from exc
    candidate = (model_dir / filename).resolve()
    try:
        candidate.relative_to(base_dir)
    except ValueError as exc:
        raise ModelArtifactError("Invalid model artifact path") from exc
    return candidate


def load_model_metadata(model_id: str) -> dict[str, Any]:
    metadata_path = resolve_model_file(model_id, "metadata.json")
    if not metadata_path.is_file():
        raise ModelArtifactError("Model metadata.json was not found")
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelArtifactError("Model metadata.json is unreadable or invalid") from exc
    if not isinstance(payload, dict):
        raise ModelArtifactError("Model metadata.json must contain an object")
    return payload
