import os
from typing import Generator

import pytest
import requests
from app.core.infrastructure.auth import create_token

# Helper to allow running tests both locally (against container) and inside container
# Default to localhost for direct local runs. Docker jobs can still set BASE_URL/HEALTH_URL.
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1")
HEALTH_URL = os.getenv("HEALTH_URL", "http://localhost:8000/health")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("E2E_REQUEST_TIMEOUT_SECONDS", "10"))


def _auth_headers() -> dict[str, str]:
    token = create_token(1, expires_in=3600)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL

@pytest.fixture(scope="session")
def health_url() -> str:
    return HEALTH_URL

@pytest.fixture(scope="session")
def api_client():
    """Simple wrapper around requests to handle base URL and chat auth."""
    class Client:
        def get(self, path, **kwargs):
            url = f"{BASE_URL}{path}"
            headers = {**_auth_headers(), **(kwargs.pop("headers", {}) or {})}
            return requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)

        def post(self, path, **kwargs):
            url = f"{BASE_URL}{path}"
            headers = {**_auth_headers(), **(kwargs.pop("headers", {}) or {})}
            return requests.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)

        def delete(self, path, **kwargs):
            url = f"{BASE_URL}{path}"
            headers = {**_auth_headers(), **(kwargs.pop("headers", {}) or {})}
            return requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)

    return Client()

@pytest.fixture(scope="module")
def active_conversation(api_client) -> Generator[str, None, None]:
    """Creates a conversation for testing and ends it after"""
    resp = api_client.post("/chat/start", json={})
    assert resp.status_code == 200
    conversation_id = resp.json().get("conversation_id")
    assert conversation_id is not None

    yield conversation_id

    # Teardown
    api_client.delete(f"/chat/{conversation_id}")
