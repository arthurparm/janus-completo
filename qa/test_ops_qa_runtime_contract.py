from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_ops_qa_qdrant_version_matches_pc2_compose() -> None:
    compose_text = _read_repo_file("docker-compose.pc2.yml")
    ops_text = _read_repo_file("OPS_QA.md")

    image_match = re.search(r"image:\s*qdrant/qdrant:(v[\w.\-]+)", compose_text)
    assert image_match, "docker-compose.pc2.yml must pin the Qdrant image version."
    qdrant_image_version = image_match.group(1)

    doc_match = re.search(r"qdrant \((v[\w.\-]+)\):", ops_text)
    assert doc_match, "OPS_QA.md must document the PC2 Qdrant runtime version."
    documented_version = doc_match.group(1)

    assert documented_version == qdrant_image_version
