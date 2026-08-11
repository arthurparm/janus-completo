"""Shared chat-message validation used by REST and SSE transports."""

from __future__ import annotations

import os

from app.core.exceptions.chat_exceptions import MessageTooLargeError

DEFAULT_CHAT_MAX_MESSAGE_BYTES = 10 * 1024


def chat_max_message_bytes() -> int:
    raw = os.getenv("CHAT_MAX_MESSAGE_BYTES", str(DEFAULT_CHAT_MAX_MESSAGE_BYTES)).strip()
    try:
        configured = int(raw)
    except ValueError:
        return DEFAULT_CHAT_MAX_MESSAGE_BYTES
    return configured if configured > 0 else DEFAULT_CHAT_MAX_MESSAGE_BYTES


def message_size_bytes(message: str) -> int:
    return len(message.encode("utf-8"))


def validate_chat_message_size(message: str) -> int:
    size_bytes = message_size_bytes(message)
    max_bytes = chat_max_message_bytes()
    if size_bytes > max_bytes:
        raise MessageTooLargeError(size_bytes, max_bytes)
    return size_bytes
