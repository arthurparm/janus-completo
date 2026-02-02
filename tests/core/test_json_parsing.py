import pytest
import json
from janus.app.core.agents.utils import parse_json_strict


class TestJsonParsing:
    def test_strict_json(self):
        """Test parsing valid JSON string directly."""
        content = '{"key": "value", "list": [1, 2, 3]}'
        result = parse_json_strict(content)
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_markdown_json_block(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        content = '```json\n{"key": "value"}\n```'
        result = parse_json_strict(content)
        assert result == {"key": "value"}

    def test_markdown_plain_block(self):
        """Test parsing JSON wrapped in plain code blocks."""
        content = '```\n{"key": "value"}\n```'
        result = parse_json_strict(content)
        assert result == {"key": "value"}

    def test_json_list(self):
        """Test parsing a JSON list."""
        content = "[1, 2, 3]"
        result = parse_json_strict(content)
        assert result == [1, 2, 3]

    def test_dirty_json(self):
        """Test parsing JSON with some surrounding whitespace/text handled by regex."""
        content = 'Sure, here is the JSON:\n```json\n{"key": "value"}\n```'
        result = parse_json_strict(content)
        assert result == {"key": "value"}

    def test_invalid_json_raises_error(self):
        """Test that truly invalid JSON raises JSONDecodeError."""
        content = '{"key": "value"'  # Missing closing brace
        with pytest.raises(json.JSONDecodeError):
            parse_json_strict(content)

    def test_invalid_text_raises_error(self):
        """Test that plain text raises JSONDecodeError."""
        content = "This is just text not json"
        with pytest.raises(json.JSONDecodeError):
            parse_json_strict(content)
