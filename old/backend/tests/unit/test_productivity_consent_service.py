from __future__ import annotations

import pytest

from app.services.productivity_consent_service import (
    ProductivityConsentRequiredError,
    require_productivity_consent,
)


class _ConsentReader:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls: list[tuple[int, str]] = []

    def has_consent(self, user_id: int, scope: str) -> bool:
        self.calls.append((user_id, scope))
        return self.allowed


def test_consent_is_checked_for_the_resolved_owner_and_scope() -> None:
    reader = _ConsentReader(True)

    require_productivity_consent(reader, user_id="42", scope="mail.send")

    assert reader.calls == [(42, "mail.send")]


def test_missing_or_invalid_consent_is_denied() -> None:
    with pytest.raises(ProductivityConsentRequiredError, match="calendar.write"):
        require_productivity_consent(
            _ConsentReader(False), user_id=42, scope="calendar.write"
        )
    with pytest.raises(ProductivityConsentRequiredError, match="inválido"):
        require_productivity_consent(_ConsentReader(True), user_id="", scope="mail.send")
