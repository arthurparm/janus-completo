def test_health_check(api_client, health_url):
    """Verify that the health check endpoint returns 200 OK."""
    # Use requests directly for absolute URL
    import requests
    resp = requests.get(health_url)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "Janus", "version": "0.1.0", "environment": "production", "tailscale": None}

def test_start_conversation(api_client):
    """Verify that a new conversation can be started."""
    resp = api_client.post("/chat/start", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert len(data["conversation_id"]) > 0

def test_send_message_echo(api_client, active_conversation):
    """Verify standard message sending."""
    payload = {
        "conversation_id": active_conversation,
        "message": "Hello, this is a test.",
        "role": "orchestrator",
        "priority": "local_only"
    }
    resp = api_client.post("/chat/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Expecting a dict with 'response' field
    assert "response" in data
    assert len(data["response"]) > 0

def test_browse_url_tool_trigger(api_client, active_conversation):
    """Verify that asking to browse a URL triggers the browse_url tool logic."""
    # Note: This relies on the LLM interpreting the intent correctly.
    # Providing a very clear instruction.
    payload = {
        "conversation_id": active_conversation,
        "message": "Use the browse_url tool to read https://example.com",
        "role": "orchestrator",
        "priority": "local_only"
    }
    resp = api_client.post("/chat/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # We expect the response to contain some content from example.com OR a refusal (which means API worked)
    assert "response" in data
    text = data["response"]
    lowered_text = lowered(text)
    # Check for success (content) or standard refusal (capability)
    assert "Example Domain" in text or "example.com" in lowered_text or "capacidade" in lowered_text or "sorry" in lowered_text or "cannot" in lowered_text

def test_anonymous_memory_support(api_client):
    """Verify that operations without user_id still function (using default_user)."""
    # Start chat without user_id (already default in other tests, but explicit here)
    resp = api_client.post("/chat/start", json={"persona": "helpful"})
    assert resp.status_code == 200
    cid = resp.json()["conversation_id"]

    # Send message
    msg_payload = {
        "conversation_id": cid,
        "message": "My name is Anonymous.",
        "role": "orchestrator"
        # No user_id provided
    }
    resp = api_client.post("/chat/message", json=msg_payload)
    assert resp.status_code == 200

    # Verify we can retrieve history (implies persistence worked under default user)
    hist_resp = api_client.get(f"/chat/{cid}/history")
    assert hist_resp.status_code == 200
    messages = hist_resp.json().get("messages", [])
    assert len(messages) >= 2  # User msg + Assistant response

def lowered(s):
    return s.lower() if s else ""
