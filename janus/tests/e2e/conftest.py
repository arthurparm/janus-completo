import os
from typing import Generator

import pytest
import requests

# Helper to allow running tests both locally (against container) and inside container
# Default to "janus-api" service name (for inside container), fallback to localhost
BASE_URL = os.getenv("BASE_URL", "http://janus-api:8000/api/v1")
HEALTH_URL = os.getenv("HEALTH_URL", "http://janus-api:8000/health")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def health_url() -> str:
    return HEALTH_URL


@pytest.fixture(scope="session")
def api_client():
    """Simple wrapper around requests to handle base URL"""

    class Client:
        def get(self, path, **kwargs):
            url = f"{BASE_URL}{path}"
            return requests.get(url, **kwargs)

        def post(self, path, **kwargs):
            url = f"{BASE_URL}{path}"
            return requests.post(url, **kwargs)

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
    api_client.post("/chat/end", json={"conversation_id": conversation_id})
