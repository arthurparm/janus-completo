import os
from unittest.mock import AsyncMock, patch

import pytest
from app.config import AppSettings, require_current_runtime_model
from app.core.autonomy.autonomy_cost_tracker import MODEL_PRICING
from app.core.llm.factory import _gemini_model_supports_sampling as factory_gemini_sampling
from app.core.llm.factory import _model_supports_temperature as factory_supports_temperature
from app.core.llm.pricing import _get_model_pricing
from app.core.llm.router import CandidateFilter, LLMFactory, RouterSelection, get_llm
from app.core.llm.router import _gemini_model_supports_sampling as router_gemini_sampling
from app.core.llm.router import _model_supports_temperature as router_supports_temperature
from app.core.llm.types import ModelPriority, ModelRole
from pydantic import ValidationError


def test_all_runtime_model_defaults_are_current_and_explicit() -> None:
    with patch.dict(os.environ, {}, clear=True):
        settings = AppSettings(_env_file=None)

    assert settings.OPENAI_MODEL_NAME == "gpt-5.6-luna"
    assert settings.OPENAI_MODELS == ["gpt-5.6-luna"]
    assert settings.OLLAMA_ENABLED is False
    assert settings.GEMINI_ENABLED is False
    assert settings.EMBEDDINGS_DEFAULT_PROVIDER == "openai"
    assert settings.EMBEDDINGS_LOCAL_ENABLED is False
    assert settings.EMBEDDINGS_FAIL_CLOSED is True
    assert settings.RAG_RERANK_BACKEND == "heuristic"
    assert settings.XAI_MODEL_NAME == "grok-4.5"
    assert settings.XAI_MODELS == ["grok-4.5"]
    assert settings.GEMINI_MODEL_NAME == "gemini-3.6-flash"
    assert settings.GEMINI_MODELS == ["gemini-3.6-flash"]
    assert settings.DEEPSEEK_MODEL_NAME == "deepseek-v4-flash"
    assert settings.DEEPSEEK_MODELS == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert settings.OPENROUTER_FREE_MODELS_ENABLED is False
    assert settings.OPENROUTER_REASONING_ENABLED is True
    assert settings.OPENROUTER_MODEL_NAME == "poolside/laguna-s-2.1:free"
    assert settings.OPENROUTER_MODELS == [
        "poolside/laguna-s-2.1:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "cohere/north-mini-code:free",
        "google/gemma-4-31b-it:free",
        "openai/gpt-oss-20b:free",
    ]
    assert settings.OLLAMA_ORCHESTRATOR_MODEL == "gpt-oss:20b"
    assert settings.OLLAMA_CODER_MODEL == "qwen3.5:9b"
    assert settings.OLLAMA_CURATOR_MODEL == "ministral-3:14b"
    assert settings.OLLAMA_VISION_MODEL == "qwen3.5:9b"
    assert settings.OPENAI_MODEL_PRICING == {
        "gpt-5.6-luna": {
            "input_per_1k_usd": 0.0002,
            "output_per_1k_usd": 0.0012,
        }
    }
    assert MODEL_PRICING["gpt-5.6-luna"] == {
        "input_per_1k": 0.0002,
        "output_per_1k": 0.0012,
    }
    assert settings.XAI_MODEL_PRICING == {
        "grok-4.5": {
            "input_per_1k_usd": 0.002,
            "output_per_1k_usd": 0.006,
        }
    }
    assert MODEL_PRICING["grok-4.5"] == {
        "input_per_1k": 0.002,
        "output_per_1k": 0.006,
    }
    for candidates in settings.LLM_CLOUD_MODEL_CANDIDATES.values():
        assert all(not candidate.startswith("openai:gpt-4") for candidate in candidates)
        assert "openai:gpt-5-mini" not in candidates
        assert all("grok-4-1" not in candidate for candidate in candidates)

    assert settings.LLM_CLOUD_MODEL_CANDIDATES["orchestrator"][0] == (
        "openrouter:poolside/laguna-s-2.1:free"
    )
    assert settings.LLM_CLOUD_MODEL_CANDIDATES["code_generator"][:2] == [
        "openrouter:poolside/laguna-s-2.1:free",
        "deepseek:deepseek-v4-pro",
    ]
    assert settings.LLM_CLOUD_MODEL_CANDIDATES["knowledge_curator"][0] == (
        "openrouter:poolside/laguna-s-2.1:free"
    )

    assert MODEL_PRICING["gemini-3.6-flash"] == {
        "input_per_1k": 0.0015,
        "output_per_1k": 0.0075,
    }
    assert MODEL_PRICING["deepseek-v4-flash"] == {
        "input_per_1k": 0.00014,
        "output_per_1k": 0.00028,
    }
    assert MODEL_PRICING["deepseek-v4-pro"] == {
        "input_per_1k": 0.000435,
        "output_per_1k": 0.00087,
    }


@pytest.mark.parametrize(
    ("field", "retired_model"),
    [
        ("OPENAI_MODEL_NAME", "gpt-4o"),
        ("GEMINI_MODEL_NAME", "gemini-2.5-flash"),
        ("DEEPSEEK_MODEL_NAME", "deepseek-chat"),
        ("XAI_MODEL_NAME", "grok-4-1-fast-reasoning"),
        ("OLLAMA_CODER_MODEL", "deepseek-coder:6.7b"),
    ],
)
def test_retired_runtime_models_are_rejected(field: str, retired_model: str) -> None:
    with patch.dict(os.environ, {}, clear=True), pytest.raises(
        ValidationError, match="runtime models are outside the current allowlist"
    ):
        AppSettings(_env_file=None, **{field: retired_model})


def test_gpt_5_6_luna_does_not_receive_temperature() -> None:
    assert factory_supports_temperature("gpt-5.6-luna") is False
    assert router_supports_temperature("gpt-5.6-luna") is False


def test_gemini_3_6_flash_does_not_receive_deprecated_sampling_parameters() -> None:
    assert factory_gemini_sampling("gemini-3.6-flash") is False
    assert router_gemini_sampling("gemini-3.6-flash") is False


def test_current_provider_pricing_is_resolved_by_model() -> None:
    assert _get_model_pricing("openai", "gpt-5.6-luna").input_per_1k_usd == 0.0002
    assert _get_model_pricing("google_gemini", "gemini-3.6-flash").output_per_1k_usd == 0.0075
    assert _get_model_pricing("deepseek", "deepseek-v4-pro").input_per_1k_usd == 0.000435
    assert _get_model_pricing("xai", "grok-4.5").output_per_1k_usd == 0.006
    assert (
        _get_model_pricing(
            "openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free"
        ).output_per_1k_usd
        == 0.0
    )


def test_openrouter_free_catalog_requires_explicit_enablement() -> None:
    selection = RouterSelection(
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )
    factory = LLMFactory(selection)

    with (
        patch("app.core.llm.router._validate_openrouter_key", return_value=True),
        patch("app.core.llm.router.settings.OPENROUTER_FREE_MODELS_ENABLED", False),
    ):
        descriptor = next(
            item for item in factory.cloud_catalog() if item["provider_key"] == "openrouter"
        )
        assert descriptor["enabled"] is False

    with (
        patch("app.core.llm.router._validate_openrouter_key", return_value=True),
        patch("app.core.llm.router.settings.OPENROUTER_FREE_MODELS_ENABLED", True),
    ):
        descriptor = next(
            item for item in factory.cloud_catalog() if item["provider_key"] == "openrouter"
        )
        assert descriptor["enabled"] is True
        assert descriptor["models"][0] == "poolside/laguna-s-2.1:free"
        assert factory.resolve_model_name("openrouter") == (
            "poolside/laguna-s-2.1:free"
        )


def test_gemini_catalog_is_disabled_even_when_a_key_is_present() -> None:
    selection = RouterSelection(
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )
    factory = LLMFactory(selection)

    with (
        patch("app.core.llm.router._validate_gemini_key", return_value=True),
        patch("app.core.llm.router.settings.GEMINI_ENABLED", False),
    ):
        descriptor = next(
            item for item in factory.cloud_catalog() if item["provider_key"] == "google_gemini"
        )

    assert descriptor["enabled"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"EMBEDDINGS_DEFAULT_PROVIDER": "local"},
        {"EMBEDDINGS_DEFAULT_PROVIDER": "ollama"},
        {"RAG_RERANK_BACKEND": "cross_encoder"},
    ],
)
def test_local_model_runtime_requires_explicit_opt_in(overrides: dict[str, object]) -> None:
    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError):
        AppSettings(_env_file=None, **overrides)


def test_role_candidate_priority_is_deterministic() -> None:
    selection = RouterSelection(
        role=ModelRole.CODE_GENERATOR,
        priority=ModelPriority.FAST_AND_CHEAP,
    )
    factory = LLMFactory(selection)

    candidates = CandidateFilter(selection, factory)._role_candidates_map()

    assert candidates["openrouter"] == ["poolside/laguna-s-2.1:free"]


def test_openrouter_reasoning_override_disables_pool_reuse() -> None:
    selection = RouterSelection(
        role=ModelRole.ORCHESTRATOR,
        priority=ModelPriority.HIGH_QUALITY,
        reasoning_override={"enabled": False},
    )
    factory = LLMFactory(selection)

    assert selection.pool_allowed is False
    assert factory.openrouter_reasoning == {"enabled": False}


def test_runtime_model_override_must_be_in_current_allowlist() -> None:
    assert require_current_runtime_model("gpt-5.6-luna") == "gpt-5.6-luna"
    with pytest.raises(ValueError, match="outside the current allowlist"):
        require_current_runtime_model("not-in-current-catalog")


@pytest.mark.asyncio
async def test_strict_provider_never_falls_back_silently() -> None:
    with (
        patch(
            "app.core.llm.router._apply_budget_guardrail",
            new=AsyncMock(side_effect=lambda selection: selection),
        ),
        patch(
            "app.core.llm.router.CandidateFilter.ensure_explicit_provider_allowed",
            new=AsyncMock(side_effect=RuntimeError("provider unavailable")),
        ),
    ):
        with pytest.raises(RuntimeError, match="provider unavailable"):
            await get_llm(
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.HIGH_QUALITY,
                config={
                    "provider": "openrouter",
                    "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                    "strict_provider": True,
                    "disable_failover": True,
                },
            )
