import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_sse_stream_emits_token_done_and_protocol(client):
    # start conversation
    r = client.post("/api/v1/chat/start", json={"title": "test"})
    assert r.status_code == 200
    cid = r.json()["conversation_id"]

    with client.stream("GET", f"/api/v1/chat/stream/{cid}", params={"message": "hello", "role": "orchestrator", "priority": "fast_and_cheap"}) as s:
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
    r = client.post("/api/v1/chat/start", json={"title": "large"})
    assert r.status_code == 200
    cid = r.json()["conversation_id"]
    big = "x" * (11 * 1024)
    r = client.get(f"/api/v1/chat/stream/{cid}", params={"message": big})
    # 413 is sent by endpoint validation
    assert r.status_code == 413
