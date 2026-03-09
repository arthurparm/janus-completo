from app.services.chat.message_helpers import build_understanding_payload


def test_build_understanding_payload_summarizes_uploaded_file_reference():
    payload = build_understanding_payload("te mandei um arquivo")

    assert payload is not None
    assert payload["intent"] == "file_reference"
    assert payload["summary"] == "Usuario informou que enviou um arquivo para consulta."


def test_build_understanding_payload_summarizes_question_without_echoing_message():
    payload = build_understanding_payload("Consegue imaginar uma historia para Frieren?")

    assert payload is not None
    assert payload["intent"] == "question"
    assert payload["summary"] == "Usuario pediu uma historia sobre Frieren."
