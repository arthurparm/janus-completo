from app.services.chat.message_helpers import split_ui


def test_split_ui_returns_original_text_and_no_ui_payload():
    text = '<janus-ui type="table">{"columns":["A"],"rows":[{"A":"1"}]}</janus-ui> resultado'
    clean_text, ui = split_ui(text)

    assert clean_text == text
    assert ui is None


def test_split_ui_handles_empty_string():
    clean_text, ui = split_ui("")

    assert clean_text == ""
    assert ui is None
