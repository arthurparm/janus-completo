from app.core.agents.utils import parse_json_lenient


def test_parse_json_lenient_plain_object():
    parsed = parse_json_lenient('{"approved": true}')
    assert isinstance(parsed, dict)
    assert parsed["approved"] is True


def test_parse_json_lenient_markdown_block():
    text = "```json\n{\"recommendations\": []}\n```"
    parsed = parse_json_lenient(text)
    assert parsed == {"recommendations": []}


def test_parse_json_lenient_embedded_object():
    text = "Result:\n{\"approved\": false, \"reason\": \"x\"}\nThanks"
    parsed = parse_json_lenient(text)
    assert parsed["approved"] is False


def test_parse_json_lenient_embedded_array():
    text = "Prefix [1, 2, 3] suffix"
    parsed = parse_json_lenient(text)
    assert parsed == [1, 2, 3]
