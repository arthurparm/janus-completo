import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))


@pytest.fixture
def client():
    from app.api.v1.endpoints.chat.chat_history import router
    import app.api.v1.endpoints.chat.chat_history as mod

    class DummyChatService:
        def get_history_paginated(self, **kwargs):
            return {
                "conversation_id": kwargs["conversation_id"],
                "persona": None,
                "messages": [
                    {"timestamp": 1.0, "role": "user", "text": "ok"},
                    {"bad": True},
                ],
            }

        def get_history(self, conversation_id, **_kwargs):
            return {
                "conversation_id": conversation_id,
                "persona": None,
                "messages": [{"timestamp": 1.0, "role": "user", "text": "ok"}],
            }

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/chat")
    app.state.chat_service = DummyChatService()

    class Identity:
        user_id = "u1"

    mod.resolve_authenticated_user_context = lambda *a, **k: Identity()
    mod.is_chat_auth_enforced = lambda: False
    mod.actor_project_id = lambda _req: "p1"

    yield TestClient(app)


def test_history_limit_branch(client):
    resp = client.get("/api/v1/chat/conv-1/history?limit=10")
    assert resp.status_code == 200


def test_history_no_limit_branch(client):
    resp = client.get("/api/v1/chat/conv-1/history")
    assert resp.status_code == 200


def test_history_conversion_failure_branch(monkeypatch):
    from app.api.v1.endpoints.chat.chat_history import router

    class DummyChatService:
        def get_history_paginated(self, **kwargs):
            return {
                "conversation_id": kwargs["conversation_id"],
                "persona": None,
                "messages": [{"timestamp": 1.0, "role": "user", "text": "boom"}],
            }

    import app.api.v1.endpoints.chat.chat_history as mod

    monkeypatch.setattr(mod, "apply_ui_to_message", lambda _m: (_ for _ in ()).throw(ValueError("x")))

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/chat")
    app.state.chat_service = DummyChatService()

    class Identity:
        user_id = "u1"

    mod.resolve_authenticated_user_context = lambda *a, **k: Identity()
    mod.is_chat_auth_enforced = lambda: False
    mod.actor_project_id = lambda _req: "p1"

    client = TestClient(app)
    resp = client.get("/api/v1/chat/conv-1/history?limit=1")
    assert resp.status_code == 200


def test_history_401_branch(monkeypatch):
    import app.api.v1.endpoints.chat.chat_history as mod
    from app.api.v1.endpoints.chat.chat_history import router
    from fastapi.testclient import TestClient

    class Identity:
        user_id = None

    monkeypatch.setattr(mod, "resolve_authenticated_user_context", lambda *a, **k: Identity())
    monkeypatch.setattr(mod, "is_chat_auth_enforced", lambda: True)
    monkeypatch.setattr(mod, "actor_project_id", lambda _req: "p1")

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/chat")

    class DummyChatService:
        def get_history_paginated(self, **kwargs):
            return {"conversation_id": kwargs["conversation_id"], "persona": None, "messages": []}

    app.state.chat_service = DummyChatService()

    client = TestClient(app)
    resp = client.get("/api/v1/chat/conv-1/history?limit=1")
    assert resp.status_code == 401


def test_history_404(monkeypatch):
    from app.services.chat_service import ConversationNotFoundError
    from app.api.v1.endpoints.chat.chat_history import router
    import app.api.v1.endpoints.chat.chat_history as mod

    class Dummy:
        def get_history(self, *a, **k):
            raise ConversationNotFoundError("conv-404")

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/chat")
    app.state.chat_service = Dummy()

    class Identity:
        user_id = "u1"

    mod.resolve_authenticated_user_context = lambda *a, **k: Identity()
    mod.is_chat_auth_enforced = lambda: False
    mod.actor_project_id = lambda _req: "p1"

    client = TestClient(app)
    resp = client.get("/api/v1/chat/conv-404/history")
    assert resp.status_code == 404


def test_history_access_denied_403(monkeypatch):
    from app.services.chat_service import ChatServiceError
    from app.api.v1.endpoints.chat.chat_history import router
    import app.api.v1.endpoints.chat.chat_history as mod

    class Dummy:
        def get_history(self, *a, **k):
            raise ChatServiceError("Access denied")

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/chat")
    app.state.chat_service = Dummy()

    class Identity:
        user_id = "u1"

    mod.resolve_authenticated_user_context = lambda *a, **k: Identity()
    mod.is_chat_auth_enforced = lambda: False
    mod.actor_project_id = lambda _req: "p1"

    client = TestClient(app)
    resp = client.get("/api/v1/chat/conv-1/history")
    assert resp.status_code == 403
