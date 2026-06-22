import re
import hashlib
import base64
from typing import Any
from app.config import settings

# --- PII Patterns ---

_PII_PATTERNS = [
    (
        re.compile(r"\b[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE),
        "EMAIL",
        "[REDACTED_EMAIL]",
    ),
    (re.compile(r"\+?\d[\d\-\s\(\)]{7,}\d"), "PHONE", "[REDACTED_PHONE]"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "CPF", "[REDACTED_CPF]"),
    (re.compile(r"\b\d{11}\b"), "CPF", "[REDACTED_CPF]"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "CNPJ", "[REDACTED_CNPJ]"),
    (re.compile(r"\b\d{14}\b"), "CNPJ", "[REDACTED_CNPJ]"),
    (re.compile(r"\b(?:\d[ \-]*?){13,16}\b"), "CARD", "[REDACTED_CARD]"),
    # IPv4 (Internal/Private ranges primarily)
    (re.compile(r"\b(?:192\.168\.|10\.|172\.(?:1[6-9]|2[0-9]|3[0-1]))(?:\.\d{1,3}){2}\b"), "IP_INTERNAL", "[REDACTED_IP]"),
    # Private Keys (PEM header)
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----", re.IGNORECASE), "PRIVATE_KEY", "[REDACTED_KEY]"),
]


def redact_pii(text: str) -> tuple[str, list[str]]:
    """
    Remove informações sensíveis do texto baseado em padrões de regex.
    Returns:
        Tuple[redacted_text, detected_types]
    """
    if not text or not isinstance(text, str):
        return text, []
        
    types: list[str] = []
    redacted = text
    for pat, name, repl in _PII_PATTERNS:
        if pat.search(redacted):
            types.append(name)
            redacted = pat.sub(repl, redacted)
    return redacted, types

def redact_pii_text_only(text: str) -> str:
    """Wrapper para retornar apenas o texto, útil para logs."""
    redacted, _ = redact_pii(text)
    return redacted


# --- Encryption (Fernet) ---

_fernet_by_key_id: dict[str, Any] = {}


def _derive_fernet_key(key_material: str) -> str:
    k = str(key_material or "")
    if len(k) == 44:
        return k
    digest = hashlib.sha256(k.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def _get_keyring() -> dict[str, str]:
    try:
        return dict(getattr(settings, "MEMORY_KEYRING", {}) or {})
    except Exception:
        return {}


def get_active_key_id() -> str | None:
    active = str(getattr(settings, "MEMORY_ACTIVE_KEY_ID", "") or "").strip()
    if active:
        return active

    keyring = _get_keyring()
    if len(keyring) == 1:
        return next(iter(keyring.keys()))
    return None


def _get_fernet_for_key_id(key_id: str | None):
    if not key_id:
        return None
    cached = _fernet_by_key_id.get(key_id)
    if cached is not None:
        return cached
    try:
        from cryptography.fernet import Fernet  # type: ignore

        keyring = _get_keyring()
        material = keyring.get(str(key_id))
        if not material:
            return None
        f = Fernet(_derive_fernet_key(material))
        _fernet_by_key_id[key_id] = f
        return f
    except Exception:
        return None


def _get_legacy_fernet():
    try:
        from cryptography.fernet import Fernet  # type: ignore

        key = getattr(settings, "MEMORY_ENCRYPTION_KEY", None) or getattr(settings, "AUTH_JWT_SECRET", None)
        if not key:
            return None
        return Fernet(_derive_fernet_key(str(key)))
    except Exception:
        return None


def encrypt_text(plain_text: str, *, require_key: bool = False) -> tuple[str, str | None]:
    """
    Criptografa o texto usando Fernet se uma chave estiver configurada.
    Returns:
        Tuple[encrypted_text_or_original, method_name_or_None]
    """
    try:
        provider = str(getattr(settings, "MEMORY_ENCRYPTION_PROVIDER", "keyring") or "keyring").strip()
        if provider == "vault_transit":
            from app.core.infrastructure.vault_client import vault_client

            return vault_client.transit_encrypt(plaintext=plain_text), "vault_transit"

        active_key_id = get_active_key_id()
        f = _get_fernet_for_key_id(active_key_id) if active_key_id else None
        if f is None:
            f = _get_legacy_fernet()
        if f is None:
            if require_key:
                raise RuntimeError("Memory encryption keyring is not configured.")
            return plain_text, None

        return f.encrypt(plain_text.encode("utf-8")).decode("utf-8"), "fernet"
    except Exception:
        if require_key:
            raise RuntimeError("Failed to encrypt secret memory.")
        return plain_text, None


def decrypt_text(encrypted_text: str | None, metadata: dict[str, Any] | None = None) -> str:
    """
    Descriptografa o texto se o metadata indicar que foi criptografado com 'fernet'.
    """
    if encrypted_text is None:
        return ""
    enc_method = None
    enc_key_id = None
    try:
        if isinstance(metadata, dict):
            enc_method = metadata.get("enc")
            enc_key_id = metadata.get("kid")
    except Exception:
        enc_method = None
    if enc_method != "fernet":
        if enc_method == "vault_transit":
            try:
                from app.core.infrastructure.vault_client import vault_client

                return vault_client.transit_decrypt(ciphertext=str(encrypted_text))
            except Exception:
                return encrypted_text
        return encrypted_text

    candidates: list[Any] = []
    if enc_key_id:
        f = _get_fernet_for_key_id(str(enc_key_id))
        if f is not None:
            candidates.append(f)

    active_key_id = get_active_key_id()
    if active_key_id and str(enc_key_id or "") != str(active_key_id):
        f = _get_fernet_for_key_id(active_key_id)
        if f is not None:
            candidates.append(f)

    legacy = _get_legacy_fernet()
    if legacy is not None:
        candidates.append(legacy)

    keyring = _get_keyring()
    for kid in keyring.keys():
        if str(kid) in {str(enc_key_id or ""), str(active_key_id or "")}:
            continue
        f = _get_fernet_for_key_id(str(kid))
        if f is not None:
            candidates.append(f)

    for f in candidates:
        try:
            return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except Exception:
            continue
    return encrypted_text
