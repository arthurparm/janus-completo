from unittest.mock import patch

import pytest
from app.core.embeddings import embedding_manager


def test_provider_order_excludes_all_local_model_paths() -> None:
    with (
        patch.object(embedding_manager.settings, "OLLAMA_ENABLED", False),
        patch.object(embedding_manager.settings, "EMBEDDINGS_LOCAL_ENABLED", False),
        patch.object(embedding_manager, "_PROVIDER_PREF", "openai"),
    ):
        assert embedding_manager._provider_order() == ["openai", "openrouter"]


def test_disabled_local_provider_is_rejected() -> None:
    with (
        patch.object(embedding_manager.settings, "OLLAMA_ENABLED", False),
        patch.object(embedding_manager.settings, "EMBEDDINGS_LOCAL_ENABLED", False),
        patch.object(embedding_manager, "_PROVIDER_PREF", "local"),
        pytest.raises(RuntimeError, match="disabled by runtime policy"),
    ):
        embedding_manager._provider_order()


def test_all_cloud_embedding_failures_fail_closed() -> None:
    with patch.object(embedding_manager.settings, "EMBEDDINGS_FAIL_CLOSED", True), pytest.raises(
        RuntimeError, match="cloud embedding providers failed"
    ):
        embedding_manager._handle_all_providers_failed(batch_size=1)
