from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from qa.auth_test_support import actor_from_test_request, issue_test_actor_token


def _headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_test_actor_token(user_id)}"}


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_notes_round_trip_is_isolated_by_authenticated_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.endpoints.productivity import (
        get_consent_repo,
        get_knowledge_facade,
        get_productivity_notes_repo,
    )
    from app.core.security import containment_middleware
    from app.main import app

    class _NotesRepository:
        def __init__(self) -> None:
            self.notes: dict[str, list[dict[str, Any]]] = {}

        def add_note(self, user_id: str, note: dict[str, Any]) -> int:
            items = self.notes.setdefault(str(user_id), [])
            items.append(dict(note))
            return len(items)

        def list_notes(self, user_id: str) -> list[dict[str, Any]]:
            return list(self.notes.get(str(user_id), []))

    repository = _NotesRepository()
    original_overrides = dict(app.dependency_overrides)
    monkeypatch.setattr(
        containment_middleware,
        "get_actor_context",
        actor_from_test_request,
    )
    app.dependency_overrides[get_productivity_notes_repo] = lambda: repository
    app.dependency_overrides[get_consent_repo] = lambda: object()
    app.dependency_overrides[get_knowledge_facade] = lambda: object()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/api/v1/productivity/notes/add",
                json={"note": {"title": "privada", "content": "somente usuário 1"}},
                headers=_headers(1),
            )
            owner_view = await client.get(
                "/api/v1/productivity/notes", headers=_headers(1)
            )
            other_view = await client.get(
                "/api/v1/productivity/notes", headers=_headers(2)
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)

    assert created.status_code == 200
    assert created.json() == {"status": "ok", "count": 1}
    assert owner_view.json() == {
        "notes": [{"title": "privada", "content": "somente usuário 1"}]
    }
    assert other_view.json() == {"notes": []}
    assert repository.notes == {
        "1": [{"title": "privada", "content": "somente usuário 1"}]
    }
