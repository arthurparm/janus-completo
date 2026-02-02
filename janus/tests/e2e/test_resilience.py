def test_invalid_json_payload(api_client):
    """Verify 422 Unprocessable Entity on missing required fields."""
    # Missing conversation_id
    payload = {"message": "Hello", "role": "user"}
    resp = api_client.post("/chat/message", json=payload)
    assert resp.status_code == 422


def test_invalid_role_enum(api_client, active_conversation):
    """Verify validation error on invalid Enum value."""
    payload = {
        "conversation_id": active_conversation,
        "message": "Hello",
        "role": "INVALID_ROLE",
        "priority": "local_only",
    }
    resp = api_client.post("/chat/message", json=payload)
    assert resp.status_code == 422


def test_nonexistent_conversation(api_client):
    """Verify behavior when sending message to non-existent conversation."""
    # Depending on implementation, this might create a new one or fail.
    # Assuming standard behavior is to allow or fail gracefully.
    # If it fails with 500, it's a bug. If it accepts, it's a feature.
    # Let's assert it DOES NOT crash with 500.
    payload = {
        "conversation_id": "non-existent-id-99999",
        "message": "Ghost message",
        "role": "orchestrator",
        "priority": "local_only",
    }
    resp = api_client.post("/chat/message", json=payload)
    assert resp.status_code != 500


def test_method_not_allowed(api_client):
    """Verify 405 Method Not Allowed."""
    # GET on POST endpoint
    resp = api_client.get("/chat/message")
    assert resp.status_code == 405
