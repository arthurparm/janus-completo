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

_fernet_obj = None


def _get_fernet():
    global _fernet_obj
    if _fernet_obj is not None:
        return _fernet_obj
    try:
        from cryptography.fernet import Fernet  # type: ignore

        key = getattr(settings, "MEMORY_ENCRYPTION_KEY", None)
        if not key:
            return None
        # Aceita chave Fernet URL-safe base64 ou frase secreta (deriva via SHA-256)
        k = str(key)
        if len(k) == 44:
            fkey = k
        else:
            digest = hashlib.sha256(k.encode("utf-8")).digest()
            fkey = base64.urlsafe_b64encode(digest).decode("utf-8")
        _fernet_obj = Fernet(fkey)
        return _fernet_obj
    except Exception:
        return None


def encrypt_text(plain_text: str) -> tuple[str, str | None]:
    """
    Criptografa o texto usando Fernet se uma chave estiver configurada.
    Returns:
        Tuple[encrypted_text_or_original, method_name_or_None]
    """
    f = _get_fernet()
    if f is None:
        return plain_text, None
    try:
        return f.encrypt(plain_text.encode("utf-8")).decode("utf-8"), "fernet"
    except Exception:
        return plain_text, None


def decrypt_text(encrypted_text: str | None, metadata: dict[str, Any] | None = None) -> str:
    """
    Descriptografa o texto se o metadata indicar que foi criptografado com 'fernet'.
    """
    if encrypted_text is None:
        return ""
    enc_method = None
    try:
        if isinstance(metadata, dict):
            enc_method = metadata.get("enc")
    except Exception:
        enc_method = None
    if enc_method != "fernet":
        return encrypted_text
    f = _get_fernet()
    if f is None:
        # Sem chave disponível: retorna texto como está
        return encrypted_text
    try:
        return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception:
        # Falha na decriptação: retorna o texto bruto
        return encrypted_text
