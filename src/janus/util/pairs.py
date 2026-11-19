from __future__ import annotations

from janus.util.codec import MAX_TEXT, JanusError, require_token


def normalize_pairs(pairs: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise JanusError("argumento repetido")
    normalized: list[tuple[str, str]] = []
    for key, value in pairs:
        require_token(key, "argumento")
        if len(value) > MAX_TEXT:
            raise JanusError("argumento longo")
        normalized.append((key, value))
    return tuple(sorted(normalized))


def pairs_json(pairs: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(pairs)
