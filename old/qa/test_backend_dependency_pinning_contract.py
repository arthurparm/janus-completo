from __future__ import annotations

from pathlib import Path
import re
import tomllib


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_asyncpg_is_pinned_in_pyproject() -> None:
    pyproject_path = _repo_root() / "backend" / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    deps = pyproject["tool"]["poetry"]["dependencies"]
    assert deps.get("asyncpg") == "0.31.0"


def test_asyncpg_version_matches_requirements_lock() -> None:
    requirements_path = _repo_root() / "backend" / "requirements.txt"
    requirements = requirements_path.read_text(encoding="utf-8")
    match = re.search(r"^asyncpg==([0-9.]+)\b", requirements, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == "0.31.0"
