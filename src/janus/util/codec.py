from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from typing import Literal

MAX_TEXT = 4000
_TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-:@")
_HEX = set("0123456789abcdef")


class JanusError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def require_token(value: str, label: str) -> None:
    if value == "" or any(char not in _TOKEN_CHARS for char in value):
        raise JanusError(f"{label} inválido")


def require_text(value: str, label: str) -> None:
    if value.strip() == "" or len(value) > MAX_TEXT:
        raise JanusError(f"{label} inválido")


def require_id(value: str, label: str) -> None:
    if len(value) != 32 or any(char not in _HEX for char in value):
        raise JanusError(f"{label} inválido")


def canonical_json(arguments: Mapping[str, str]) -> str:
    return json.dumps(dict(arguments), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def format_timestamp(now_ms: int) -> str:
    seconds, millis = divmod(now_ms, 1000)
    base = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(seconds))
    return f"{base}.{millis:03d}Z"


def parse_json(text: str) -> object:
    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError as error:
        raise JanusError("json inválido") from error
    return loaded


def as_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise JanusError(f"{label} precisa ser objeto")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise JanusError(f"{label} tem chave inválida")
        result[key] = item
    return result


def exact_keys(obj: dict[str, object], keys: tuple[str, ...], label: str) -> None:
    if set(obj) != set(keys):
        raise JanusError(f"{label} fora do contrato")


def required(obj: dict[str, object], key: str) -> object:
    if key not in obj:
        raise JanusError(f"{key} ausente")
    return obj[key]


def as_str(value: object, label: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise JanusError(f"{label} inválido")
    if not allow_empty and value == "":
        raise JanusError(f"{label} ausente")
    if len(value) > MAX_TEXT:
        raise JanusError(f"{label} longo")
    return value


def as_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise JanusError(f"{label} inválido")
    return value


def as_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise JanusError(f"{label} inválido")
    return value


def as_count(value: object, label: str) -> int:
    number = as_int(value, label)
    if number < 0:
        raise JanusError(f"{label} inválido")
    return number


def as_optional_str(value: object, label: str) -> str | None:
    if value is None:
        return None
    return as_str(value, label, allow_empty=False)


def as_string_map(value: object, label: str) -> tuple[tuple[str, str], ...]:
    raw = as_object(value, label)
    pairs: list[tuple[str, str]] = []
    for key, item in raw.items():
        require_token(key, label)
        pairs.append((key, as_str(item, label, allow_empty=True)))
    return tuple(sorted(pairs))


GateName = Literal["permitir", "negar", "pedir"]


def as_id(value: object, label: str) -> str:
    text = as_str(value, label, allow_empty=False)
    require_id(text, label)
    return text


def as_timestamp(value: object, label: str) -> str:
    text = as_str(value, label, allow_empty=False)
    if len(text) != 24 or text[10] != "T" or not text.endswith("Z"):
        raise JanusError(f"{label} inválido")
    return text


def as_gate(value: object, label: str) -> GateName:
    text = as_str(value, label, allow_empty=False)
    if text == "permitir":
        return "permitir"
    if text == "negar":
        return "negar"
    if text == "pedir":
        return "pedir"
    raise JanusError(f"{label} inválido")
