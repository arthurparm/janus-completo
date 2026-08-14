from __future__ import annotations

import json

import pytest

from app.repositories.productivity_repository import (
    ProductivityNotesRepository,
    ProductivityRepositoryError,
)


def test_notes_are_persisted_under_distinct_owner_paths() -> None:
    files: dict[str, str] = {}

    def read(path: str) -> str:
        return files.get(path, f"Erro: O ficheiro '{path}' não foi encontrado.")

    def write(path: str, content: str, overwrite: bool) -> str:
        assert overwrite is True
        files[f"workspace/{path}"] = content
        return "ok"

    repository = ProductivityNotesRepository(reader=read, writer=write)

    assert repository.add_note("user-a", {"title": "A", "content": "segredo A"}) == 1
    assert repository.add_note("user-b", {"title": "B", "content": "segredo B"}) == 1

    assert repository.list_notes("user-a") == [
        {"title": "A", "content": "segredo A"}
    ]
    assert repository.list_notes("user-b") == [
        {"title": "B", "content": "segredo B"}
    ]
    assert len(files) == 2
    assert all("notes_default.json" not in path for path in files)
    assert all("workspace/workspace" not in path for path in files)


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    "payload", ["{", json.dumps({"title": "not-a-list"})]
)
def test_corrupt_or_invalid_notes_are_not_overwritten(payload: str) -> None:
    writes: list[str] = []

    def write(path: str, _content: str, _overwrite: bool) -> str:
        writes.append(path)
        return "ok"

    repository = ProductivityNotesRepository(
        reader=lambda _path: payload,
        writer=write,
    )

    with pytest.raises(ProductivityRepositoryError, match="nenhuma gravação"):
        repository.add_note("user-a", {"title": "nova", "content": "nota"})

    assert writes == []


def test_write_failure_is_reported_instead_of_returning_success() -> None:
    repository = ProductivityNotesRepository(
        reader=lambda path: f"Erro: O ficheiro '{path}' não foi encontrado.",
        writer=lambda _path, _content, _overwrite: "Erro: disco indisponível",
    )

    with pytest.raises(ProductivityRepositoryError, match="persistir"):
        repository.add_note("user-a", {"title": "nova", "content": "nota"})
