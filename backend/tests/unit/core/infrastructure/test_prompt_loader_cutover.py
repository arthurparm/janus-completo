import importlib
from pathlib import Path

import pytest

prompt_module = importlib.import_module("app.core.infrastructure.prompt_loader")


@pytest.mark.asyncio
async def test_prompt_loader_get_uses_file_fallback_when_other_sources_missing(tmp_path, monkeypatch):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "example_prompt.txt").write_text("conteudo de arquivo", encoding="utf-8")

    monkeypatch.setattr(prompt_module, "PROMPTS_DIR", prompt_dir)
    monkeypatch.setattr(prompt_module, "_file_prompts_cache", {})

    loader = prompt_module.PromptLoader(use_database=False)
    loader._store = {}

    result = await loader.get("example_prompt")

    assert result == "conteudo de arquivo"


@pytest.mark.asyncio
async def test_get_prompt_returns_none_when_prompt_is_missing(monkeypatch):
    async def fake_get(*args, **kwargs):
        del args, kwargs
        raise KeyError("missing")

    monkeypatch.setattr(prompt_module.prompt_loader, "get", fake_get)

    assert await prompt_module.get_prompt("missing") is None


@pytest.mark.asyncio
async def test_get_formatted_prompt_formats_successfully(monkeypatch):
    async def fake_get_prompt(prompt_name: str, **kwargs):
        del kwargs
        assert prompt_name == "welcome"
        return "Ola {nome}"

    monkeypatch.setattr(prompt_module, "get_prompt", fake_get_prompt)

    result = await prompt_module.get_formatted_prompt("welcome", nome="Janus")

    assert result == "Ola Janus"


@pytest.mark.asyncio
async def test_get_formatted_prompt_is_tolerant_on_missing_placeholder(monkeypatch, caplog):
    async def fake_get_prompt(prompt_name: str, **kwargs):
        del prompt_name, kwargs
        return "Ola {nome}"

    monkeypatch.setattr(prompt_module, "get_prompt", fake_get_prompt)

    with caplog.at_level("ERROR"):
        result = await prompt_module.get_formatted_prompt("welcome", outro="x")

    assert result == "Ola {nome}"
    assert "Variável faltando no prompt" in caplog.text


def test_prompts_dir_is_exported():
    assert isinstance(prompt_module.PROMPTS_DIR, Path)
