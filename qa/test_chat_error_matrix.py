from qa.test_chat_endpoint_contract import _DummyChatService, _build_client


def test_chat_stream_413_returns_canonical_error_detail():
    svc = _DummyChatService()
    client = _build_client(svc)
    too_large = "x" * (11 * 1024)
    resp = client.get("/api/v1/chat/stream/conv-1", params={"message": too_large})
    assert resp.status_code == 413
    detail = resp.json()["detail"]
    assert detail["code"] == "CHAT_MESSAGE_TOO_LARGE"
    assert detail["category"] == "validation"
    assert detail["retryable"] is False

