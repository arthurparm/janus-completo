import os
import sys
import time
from logging.handlers import RotatingFileHandler

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Logging config tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.infrastructure.logging_config import (
    _normalize_legacy_structlog_event,
    cleanup_rotated_log_files,
    setup_logging,
)


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


def test_normalize_legacy_structlog_event_flattens_dict_event():
    event_dict = {
        "event": {"event": "write_file_success", "path": "/tmp/x", "bytes": 12},
        "level": "info",
    }
    out = _normalize_legacy_structlog_event(None, None, event_dict)

    assert out["event"] == "write_file_success"
    assert out["path"] == "/tmp/x"
    assert out["bytes"] == 12
    assert out["level"] == "info"


def test_setup_logging_uses_rotating_file_handlers(monkeypatch, tmp_path):
    import app.core.infrastructure.logging_config as logging_module

    monkeypatch.setattr(logging_module.settings, "LOG_FILE_MAX_BYTES", 2048)
    monkeypatch.setattr(logging_module.settings, "LOG_FILE_BACKUP_COUNT", 3)

    setup_logging(log_file=str(tmp_path / "janus.log"))

    handlers = [h for h in logging_module.logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]
    assert len(handlers) >= 2
    assert all(h.maxBytes == 2048 for h in handlers)
    assert all(h.backupCount == 3 for h in handlers)


def test_cleanup_rotated_log_files_removes_only_old_rotated_files(tmp_path):
    main_log = tmp_path / "janus.log"
    rotated_old = tmp_path / "janus.log.1"
    rotated_new = tmp_path / "janus.log.2"

    main_log.write_text("active")
    rotated_old.write_text("old")
    rotated_new.write_text("new")

    now = time.time()
    old_time = now - (15 * 24 * 60 * 60)
    recent_time = now - (2 * 24 * 60 * 60)
    os.utime(rotated_old, (old_time, old_time))
    os.utime(rotated_new, (recent_time, recent_time))

    result = cleanup_rotated_log_files(str(main_log), retention_days=7)
    assert result["removed"] == 1
    assert result["scanned"] >= 2
    assert main_log.exists()
    assert not rotated_old.exists()
    assert rotated_new.exists()


def test_cleanup_rotated_log_files_requires_positive_retention(tmp_path):
    main_log = tmp_path / "janus.log"
    main_log.write_text("active")

    with pytest.raises(ValueError):
        cleanup_rotated_log_files(str(main_log), retention_days=0)
