import importlib
import re
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

prompt_module = importlib.import_module("app.core.infrastructure.prompt_loader")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_prompt_loader_returns_exact_repository_version() -> None:
    loader = prompt_module.PromptLoader(use_database=False)
    loader.use_database = True
    loader._prompt_repo = object()
    loader._get_prompt_from_database = AsyncMock(return_value="versão 2")

    result = await loader.get("agent", version="2.0")

    assert result == "versão 2"
    loader._get_prompt_from_database.assert_awaited_once_with(
        "agent",
        version="2.0",
        namespace=None,
        lang=None,
        model=None,
    )


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_prompt_loader_does_not_fallback_when_exact_version_is_missing() -> None:
    loader = prompt_module.PromptLoader(use_database=False)
    loader.use_database = True
    loader._prompt_repo = object()
    loader._store = {"agent": "versão sem garantia"}
    loader._get_prompt_from_database = AsyncMock(return_value=None)

    with pytest.raises(KeyError, match="versão '9.9'"):
        await loader.get("agent", version="9.9")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_prompt_loader_rejects_versioned_lookup_without_repository() -> None:
    loader = prompt_module.PromptLoader(use_database=False)
    loader._store = {"agent": "versão sem garantia"}

    with pytest.raises(RuntimeError, match="repositório de prompts"):
        await loader.get("agent", version="2.0")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_prompt_loader_exposes_repository_failure_for_exact_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = prompt_module.PromptLoader(use_database=False)
    loader.use_database = True
    loader._prompt_repo = object()

    async def failing_session() -> AsyncIterator[Any]:
        raise ConnectionError("database offline")
        yield

    db_module = importlib.import_module("app.db")
    monkeypatch.setattr(db_module, "get_db_session", failing_session)

    with pytest.raises(RuntimeError, match="versão '2.0'"):
        await loader.get("agent", version="2.0")


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_repository_queries_prompt_by_semantic_version() -> None:
    from app.repositories.prompt_repository import PromptRepository

    expected = SimpleNamespace(prompt_text="versão 2")
    scalar_result = SimpleNamespace(first=lambda: expected)
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: scalar_result))
    )
    repository = PromptRepository()
    repository._async_session = session

    result = await repository.get_prompt_version("agent", "2.0")

    assert result is expected
    session.execute.assert_awaited_once()


def test_update_prompt_supplies_auditable_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SimpleNamespace(
        create_prompt_version=Mock(
            return_value=SimpleNamespace(prompt_version="persistida")
        )
    )
    invalidate = Mock()
    monkeypatch.setattr(prompt_module.prompt_loader, "use_database", True)
    monkeypatch.setattr(prompt_module.prompt_loader, "_prompt_repo", repository)
    monkeypatch.setattr(prompt_module.prompt_loader, "invalidate", invalidate)

    assert prompt_module.update_prompt("agent", "novo conteúdo") is True

    version = repository.create_prompt_version.call_args.kwargs["version"]
    assert re.fullmatch(r"\d{20}", version)
    assert repository.create_prompt_version.call_args.kwargs["activate"] is True
    invalidate.assert_called_once()


def test_prompt_version_generator_fits_persistent_contract() -> None:
    from app.repositories.prompt_repository import generate_prompt_version

    version = generate_prompt_version()

    assert re.fullmatch(r"\d{20}", version)
