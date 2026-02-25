import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Logging config tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.infrastructure.logging_config import _normalize_legacy_structlog_event


def test_normalize_legacy_structlog_event_rewrites_log_info_message():
    event_dict = {"event": "log_info", "message": "hello", "task_id": "t1"}
    out = _normalize_legacy_structlog_event(None, None, event_dict)

    assert out["event"] == "hello"
    assert out["legacy_event"] == "log_info"
    assert "message" not in out
    assert out["task_id"] == "t1"


def test_normalize_legacy_structlog_event_noop_for_modern_events():
    event_dict = {"event": "router_terminal_sink", "task_id": "t1"}
    out = _normalize_legacy_structlog_event(None, None, event_dict)

    assert out["event"] == "router_terminal_sink"
    assert "legacy_event" not in out
