import time

from app.core.llm.client import LLMClient, _extract_rate_limit_reset_at
from app.core.llm.rate_limiter import ModelUsageTracker


class _FakeHeaders(dict):
    """Simula httpx.Headers: acesso case-insensitive via .get()."""

    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


class _FakeResponse:
    def __init__(self, headers: dict):
        self.headers = _FakeHeaders(headers)


class _FakeRateLimitError(Exception):
    def __init__(self, message: str, response=None):
        super().__init__(message)
        self.response = response


def test_extract_reset_at_prefers_retry_after_header():
    before = time.time()
    error = _FakeRateLimitError("429", response=_FakeResponse({"Retry-After": "42"}))
    reset_at = _extract_rate_limit_reset_at(error)
    assert reset_at is not None
    assert before + 41 <= reset_at <= before + 43


def test_extract_reset_at_normalizes_epoch_millis_header():
    future_ms = int((time.time() + 3600) * 1000)
    error = _FakeRateLimitError("429", response=_FakeResponse({"X-RateLimit-Reset": str(future_ms)}))
    reset_at = _extract_rate_limit_reset_at(error)
    assert reset_at is not None
    assert abs(reset_at - future_ms / 1000.0) < 1.0


def test_extract_reset_at_falls_back_to_embedded_body_metadata():
    future_ms = int((time.time() + 7200) * 1000)
    message = (
        "Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-day.', "
        f"'metadata': {{'headers': {{'X-RateLimit-Reset': '{future_ms}'}}}}}}}}"
    )
    error = _FakeRateLimitError(message)
    reset_at = _extract_rate_limit_reset_at(error)
    assert reset_at is not None
    assert abs(reset_at - future_ms / 1000.0) < 1.0


def test_extract_reset_at_returns_none_without_signal():
    error = _FakeRateLimitError("429 concurrency limit exceeded")
    assert _extract_rate_limit_reset_at(error) is None


def _client(provider: str = "openrouter") -> LLMClient:
    return LLMClient(
        base=object(),
        provider=provider,
        model="some-model",
        role=None,
        cache_key="k",
        response_cache_enabled=False,
    )


def test_handle_rate_limit_error_respects_provider_reset_timestamp(monkeypatch):
    tracker = ModelUsageTracker()
    monkeypatch.setattr("app.core.llm.client.get_rate_limiter", lambda: tracker)

    reset_at = time.time() + 3600
    error = _FakeRateLimitError("429", response=_FakeResponse({"Retry-After": "3600"}))
    monkeypatch.setattr(
        "app.core.llm.client._extract_rate_limit_reset_at", lambda _e: reset_at
    )

    client = _client("openrouter")
    client._handle_rate_limit_error(error)

    availability = tracker.get_availability("openrouter", "some-model")
    assert availability["available"] is False
    assert availability["details"]["reset_at"] == reset_at


def test_handle_rate_limit_error_marks_daily_exhausted_when_message_says_per_day(monkeypatch):
    tracker = ModelUsageTracker()
    monkeypatch.setattr("app.core.llm.client.get_rate_limiter", lambda: tracker)
    monkeypatch.setattr("app.core.llm.client._extract_rate_limit_reset_at", lambda _e: None)

    error = _FakeRateLimitError("Error code: 429 - Rate limit exceeded: free-models-per-day.")
    client = _client("openrouter")
    client._handle_rate_limit_error(error)

    key = "openrouter:some-model"
    assert key in tracker._daily_exhausted


def test_handle_rate_limit_error_does_not_mark_exhausted_for_transient_429(monkeypatch):
    tracker = ModelUsageTracker()
    monkeypatch.setattr("app.core.llm.client.get_rate_limiter", lambda: tracker)
    monkeypatch.setattr("app.core.llm.client._extract_rate_limit_reset_at", lambda _e: None)

    error = _FakeRateLimitError("429 concurrency limit exceeded")
    client = _client("deepseek")
    client._handle_rate_limit_error(error)

    key = "deepseek:some-model"
    assert key not in tracker._daily_exhausted
    assert key not in tracker._exhausted_until
    assert tracker.is_available("deepseek", "some-model") is True
