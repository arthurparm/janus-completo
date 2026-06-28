import pytest
from app.core.infrastructure.auth import create_token
from app.main import app
from starlette.testclient import TestClient


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(1, expires_in=3600)}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_sse_stream_emits_token_done_and_protocol(client):
    # start conversation
    r = client.post("/api/v1/chat/start", json={"title": "test"}, headers=_auth_headers())
    assert r.status_code == 200
    cid = r.json()["conversation_id"]

    with client.stream(
        "POST",
        f"/api/v1/chat/stream/{cid}",
        json={"message": "hello", "role": "orchestrator", "priority": "fast_and_cheap"},
        headers=_auth_headers(),
    ) as s:
        buf = []
        for chunk in s.iter_lines():
            if not chunk:
                continue
            buf.append(chunk.decode("utf-8") if isinstance(chunk, (bytes, bytearray)) else chunk)
            if len(buf) > 100:
                break
        # Must contain at least one token, protocol and a done event
        assert any(line.startswith("event: token") for line in buf), buf
        assert any(line.startswith("event: protocol") for line in buf), buf
        assert any(line.startswith("event: done") for line in buf), buf


def test_message_too_large_rejected(client):
    r = client.post("/api/v1/chat/start", json={"title": "large"}, headers=_auth_headers())
    assert r.status_code == 200
    cid = r.json()["conversation_id"]
    big = "x" * (11 * 1024)
    r = client.post(f"/api/v1/chat/stream/{cid}", json={"message": big}, headers=_auth_headers())
    # 413 is sent by endpoint validation
    assert r.status_code == 413
