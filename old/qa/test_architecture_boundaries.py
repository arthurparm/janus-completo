from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS_DIR = REPO_ROOT / "backend" / "app" / "api" / "v1" / "endpoints"
GOOGLE_WORKER_FILE = (
    REPO_ROOT / "backend" / "app" / "core" / "workers" / "google_productivity_worker.py"
)

FORBIDDEN_QDRANT_PATTERNS = (
    "from qdrant_client",
    "get_async_qdrant_client",
    "aget_or_create_collection",
    "AsyncQdrantClient",
    "aembed_text",
)

FORBIDDEN_INFERENCE_PATTERNS = (
    "from app.repositories.llm_repository",
    "get_llm_repository",
    "from app.core.llm.router import get_llm",
    "from app.core.llm.client import get_llm_client",
)


def _python_sources(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.py") if path.name != "__init__.py")


def test_application_plane_endpoints_do_not_import_qdrant_directly() -> None:
    violations: list[str] = []
    for path in _python_sources(ENDPOINTS_DIR):
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_QDRANT_PATTERNS:
            if pattern in content:
                violations.append(f"{path.relative_to(REPO_ROOT)} -> {pattern}")
    assert not violations, "Application Plane must not import Qdrant directly:\n" + "\n".join(violations)


def test_application_plane_endpoints_do_not_import_llm_infra_directly() -> None:
    violations: list[str] = []
    for path in _python_sources(ENDPOINTS_DIR):
        content = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_INFERENCE_PATTERNS:
            if pattern in content:
                violations.append(f"{path.relative_to(REPO_ROOT)} -> {pattern}")
    assert not violations, "Application Plane must use InferenceFacade instead of LLM infra:\n" + "\n".join(violations)


def test_google_productivity_worker_uses_knowledge_facade_for_indexing() -> None:
    content = GOOGLE_WORKER_FILE.read_text(encoding="utf-8")
    violations = [pattern for pattern in FORBIDDEN_QDRANT_PATTERNS if pattern in content]
    assert not violations, (
        "google_productivity_worker must not access Qdrant directly:\n"
        + "\n".join(violations)
    )
    assert "get_knowledge_facade" in content
