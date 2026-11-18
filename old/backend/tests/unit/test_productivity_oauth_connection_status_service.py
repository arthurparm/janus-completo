from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.db import db
from app.services import productivity_oauth_connection_status_service as service


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("token", "granted", "expected_status", "expected_capabilities"),
    [
        (None, set(), "disconnected", {"calendar": False, "mail": False}),
        (
            object(),
            {"calendar.read", "calendar.write"},
            "configured",
            {"calendar": True, "mail": False},
        ),
        (object(), set(), "inconsistent", {"calendar": False, "mail": False}),
        (
            None,
            {"mail.read", "mail.send"},
            "inconsistent",
            {"calendar": False, "mail": True},
        ),
    ],
)
def test_connection_status_is_truthful_about_local_state_only(
    monkeypatch: pytest.MonkeyPatch,
    token: object | None,
    granted: set[str],
    expected_status: str,
    expected_capabilities: dict[str, bool],
) -> None:
    session = SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(db, "get_session_direct", lambda: session)
    monkeypatch.setattr(
        service,
        "OAuthTokenRepository",
        lambda supplied: SimpleNamespace(
            get=lambda **_kwargs: token if supplied is session else pytest.fail()
        ),
    )
    monkeypatch.setattr(
        service,
        "ConsentRepository",
        lambda supplied: SimpleNamespace(
            has_consent=lambda _user_id, scope: (
                scope in granted if supplied is session else pytest.fail()
            )
        ),
    )

    result = service.get_google_connection_status(user_id=7)

    assert result.local_status == expected_status
    assert result.capabilities == expected_capabilities
    assert result.provider_verified is False


def test_connection_status_closes_session_and_normalizes_storage_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[bool] = []
    session = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(db, "get_session_direct", lambda: session)
    monkeypatch.setattr(
        service,
        "OAuthTokenRepository",
        lambda _session: SimpleNamespace(
            get=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("database down"))
        ),
    )

    with pytest.raises(service.GoogleConnectionStatusUnavailableError):
        service.get_google_connection_status(user_id=7)

    assert closed == [True]
