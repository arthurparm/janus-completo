from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import SecretStr

from app.services.productivity_oauth_state_service import (
    GOOGLE_PRODUCTIVITY_CONSENTS,
    GOOGLE_PRODUCTIVITY_SCOPES,
    OAuthStateError,
    issue_google_oauth_state,
    resolve_google_oauth_config,
    verify_google_oauth_state,
)


def test_mail_capability_matches_read_and_send_consents() -> None:
    assert GOOGLE_PRODUCTIVITY_SCOPES["mail"].split() == [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    assert GOOGLE_PRODUCTIVITY_CONSENTS["mail"] == ("mail.read", "mail.send")


def test_oauth_config_extracts_secret_values_without_masking() -> None:
    config = type(
        "Config",
        (),
        {
            "GOOGLE_OAUTH_CLIENT_ID": SecretStr("client-id"),
            "GOOGLE_OAUTH_CLIENT_SECRET": SecretStr("client-secret"),
            "GOOGLE_OAUTH_REDIRECT_URI": "https://janus.example/callback",
        },
    )()

    assert resolve_google_oauth_config(config) == (
        "client-id",
        "client-secret",
        "https://janus.example/callback",
    )


def test_oauth_state_round_trip_is_actor_scoped_and_nonce_backed() -> None:
    first = issue_google_oauth_state(
        signing_secret="state-secret",
        actor_id=7,
        scope="calendar",
        now=1_000,
    )
    second = issue_google_oauth_state(
        signing_secret="state-secret",
        actor_id=7,
        scope="calendar",
        now=1_000,
    )

    verified = verify_google_oauth_state(
        first,
        signing_secret="state-secret",
        actor_id=7,
        now=1_300,
    )

    assert verified.actor_id == "7"
    assert verified.scope == "calendar"
    assert verified.issued_at == 1_000
    assert first != second


@pytest.mark.parametrize(  # type: ignore[untyped-decorator]
    ("mutation", "actor_id", "now", "message"),
    [
        (lambda value: ("A" if value[0] != "A" else "B") + value[1:], 7, 1_001, "adulterado"),
        (lambda value: value, 8, 1_001, "outro usuário"),
        (lambda value: value, 7, 1_601, "expirado"),
        (lambda value: value, 7, 900, "expirado"),
    ],
)
def test_oauth_state_rejects_tampering_wrong_actor_and_invalid_time(
    mutation: Callable[[str], str],
    actor_id: int,
    now: int,
    message: str,
) -> None:
    state = issue_google_oauth_state(
        signing_secret="state-secret",
        actor_id=7,
        scope="mail",
        now=1_000,
    )

    with pytest.raises(OAuthStateError, match=message):
        verify_google_oauth_state(
            mutation(state),
            signing_secret="state-secret",
            actor_id=actor_id,
            now=now,
        )
