from app.core.llm.sanitizer import ContentSanitizer


class _Settings:
    IDENTITY_ENFORCEMENT_ENABLED = True
    AGENT_IDENTITY_NAME = "Janus"
    APP_NAME = "Janus"


class _DisabledSettings:
    IDENTITY_ENFORCEMENT_ENABLED = False
    AGENT_IDENTITY_NAME = "Janus"
    APP_NAME = "Janus"


def test_sanitizer_rewrites_self_identification_to_janus():
    sanitizer = ContentSanitizer(_Settings())
    raw = "As an AI language model, I am GPT-4 from OpenAI."

    result = sanitizer.sanitize(raw)

    assert "Janus" in result
    assert "GPT-4" not in result
    assert "OpenAI" not in result
    assert "AI language model" not in result


def test_sanitizer_preserves_technical_provider_reference():
    sanitizer = ContentSanitizer(_Settings())
    raw = "Para usar a OpenAI API, configure OPENAI_API_KEY."

    result = sanitizer.sanitize(raw)

    assert "OpenAI API" in result
    assert "OPENAI_API_KEY" in result


def test_sanitizer_rewrites_portuguese_self_context():
    sanitizer = ContentSanitizer(_Settings())
    raw = "Sou o assistente rodando em Gemini 2.0 para responder mais rapido."

    result = sanitizer.sanitize(raw)

    assert "Gemini" not in result
    assert "Janus" in result


def test_sanitizer_removes_role_prefix():
    sanitizer = ContentSanitizer(_Settings())
    raw = "Assistant: Sou Janus."

    result = sanitizer.sanitize(raw)

    assert result == "Sou Janus."


def test_sanitizer_returns_original_when_enforcement_is_disabled():
    sanitizer = ContentSanitizer(_DisabledSettings())
    raw = "I am GPT-4 from OpenAI."

    result = sanitizer.sanitize(raw)

    assert result == raw
