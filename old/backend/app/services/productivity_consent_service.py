from __future__ import annotations

from typing import Protocol


class ConsentReader(Protocol):
    def has_consent(self, user_id: int, scope: str) -> bool: ...


class ProductivityConsentRequiredError(Exception):
    """The owner did not grant or has revoked the requested external effect."""


def require_productivity_consent(
    repo: ConsentReader,
    *,
    user_id: int | str,
    scope: str,
) -> None:
    try:
        resolved_user_id = int(user_id)
    except (TypeError, ValueError) as exc:
        raise ProductivityConsentRequiredError("Consentimento do usuário inválido.") from exc
    if not repo.has_consent(resolved_user_id, scope):
        raise ProductivityConsentRequiredError(f"Consent required: {scope}")
