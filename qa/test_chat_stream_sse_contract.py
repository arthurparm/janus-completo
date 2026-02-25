from qa.test_chat_endpoint_contract import _DummyChatService, _build_client


def test_chat_stream_sse_keeps_core_events_contract():
    svc = _DummyChatService()
    client = _build_client(svc)
    resp = client.get(
        "/api/v1/chat/stream/conv-1",
        params={"message": "hello", "role": "orchestrator", "priority": "fast_and_cheap"},
        headers={"X-Actor-User-Id": "1"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "event: protocol" in body
    assert "event: token" in body
    assert "event: done" in body

