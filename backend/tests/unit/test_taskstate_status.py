import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.autonomy.taskstate_status import (
    is_success_terminal_status,
    is_terminal_status,
    normalize_task_status,
)


def test_normalize_task_status_maps_aliases_to_canonical_values():
    assert normalize_task_status(None) == "in_progress"
    assert normalize_task_status("success") == "completed"
    assert normalize_task_status("done") == "completed"
    assert normalize_task_status("error") == "failed"
    assert normalize_task_status("canceled") == "cancelled"
    assert normalize_task_status("running") == "in_progress"


def test_is_terminal_status_recognizes_canonical_and_alias_values():
    assert is_terminal_status("completed") is True
    assert is_terminal_status("success") is True
    assert is_terminal_status("failed") is True
    assert is_terminal_status("blocked") is True
    assert is_terminal_status("cancelled") is True
    assert is_terminal_status("in_progress") is False
    assert is_terminal_status("pending") is False


def test_is_success_terminal_status_only_completed_family():
    assert is_success_terminal_status("completed") is True
    assert is_success_terminal_status("success") is True
    assert is_success_terminal_status("done") is True
    assert is_success_terminal_status("failed") is False
    assert is_success_terminal_status("blocked") is False
