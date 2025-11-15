from typing import Set

ALLOWED_CONSENT_SCOPES: Set[str] = {
    "calendar.read",
    "calendar.write",
    "mail.read",
    "mail.send",
    "notes.read",
    "notes.write",
}

def is_valid_scope(scope: str) -> bool:
    return scope in ALLOWED_CONSENT_SCOPES