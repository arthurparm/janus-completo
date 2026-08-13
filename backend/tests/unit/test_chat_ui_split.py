from app.services.chat.message_helpers import split_ui


def test_split_ui_extracts_table_payload_and_strips_tag_from_text():
    text = (
        'Aqui esta a comparacao: <janus-ui type="table" title="Comparison">'
        '{"columns":["Name","Role"],"rows":[{"Name":"Janus","Role":"AI"}]}'
        "</janus-ui> Espero que ajude."
    )
    clean_text, ui = split_ui(text)

    assert clean_text == "Aqui esta a comparacao:  Espero que ajude."
    assert ui == {
        "type": "table",
        "data": {"columns": ["Name", "Role"], "rows": [{"Name": "Janus", "Role": "AI"}]},
        "title": "Comparison",
    }


def test_split_ui_includes_description_when_present():
    text = '<janus-ui type="card" title="Status" description="resumo">{"text":"ok"}</janus-ui>'
    _, ui = split_ui(text)

    assert ui["description"] == "resumo"


def test_split_ui_ignores_unknown_type():
    text = '<janus-ui type="video">{"url":"x"}</janus-ui>'
    clean_text, ui = split_ui(text)

    assert clean_text == text
    assert ui is None


def test_split_ui_ignores_malformed_json():
    text = '<janus-ui type="table">{not valid json}</janus-ui>'
    clean_text, ui = split_ui(text)

    assert clean_text == text
    assert ui is None


def test_split_ui_returns_original_text_when_no_tag_present():
    text = "resposta comum sem marcador de UI"
    clean_text, ui = split_ui(text)

    assert clean_text == text
    assert ui is None


def test_split_ui_handles_empty_string():
    clean_text, ui = split_ui("")

    assert clean_text == ""
    assert ui is None


def test_split_ui_ignores_tag_missing_type_attribute():
    text = '<janus-ui title="x">{"a":1}</janus-ui>'
    clean_text, ui = split_ui(text)

    assert clean_text == text
    assert ui is None
