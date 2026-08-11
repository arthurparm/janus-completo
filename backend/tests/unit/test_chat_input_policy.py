import pytest
from app.core.exceptions.chat_exceptions import MessageTooLargeError
from app.services.chat.input_policy import (
    DEFAULT_CHAT_MAX_MESSAGE_BYTES,
    chat_max_message_bytes,
    message_size_bytes,
    validate_chat_message_size,
)


def test_chat_message_size_uses_utf8_bytes_and_returns_accepted_size(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_MAX_MESSAGE_BYTES", "4")

    assert message_size_bytes("á") == 2
    assert validate_chat_message_size("áá") == 4


def test_chat_message_size_rejects_above_shared_limit(monkeypatch) -> None:
    monkeypatch.setenv("CHAT_MAX_MESSAGE_BYTES", "3")

    with pytest.raises(MessageTooLargeError):
        validate_chat_message_size("áá")


@pytest.mark.parametrize("configured", ["invalid", "0", "-1"])
def test_invalid_or_non_positive_limit_falls_back_to_safe_default(
    monkeypatch,
    configured: str,
) -> None:
    monkeypatch.setenv("CHAT_MAX_MESSAGE_BYTES", configured)

    assert chat_max_message_bytes() == DEFAULT_CHAT_MAX_MESSAGE_BYTES
