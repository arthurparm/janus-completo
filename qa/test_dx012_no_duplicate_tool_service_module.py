import os
import sys
from pathlib import Path

sys.path.append(os.path.join(os.getcwd(), "backend"))


def test_tool_service_improved_module_was_removed():
    duplicate_path = Path("backend/app/services/tool_service_improved.py")
    assert not duplicate_path.exists()
