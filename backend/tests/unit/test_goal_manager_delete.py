import os
import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Autonomy backend tests require Python 3.10+", allow_module_level=True)

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.autonomy.goal_manager import GoalManager


def test_delete_goal_returns_false_when_goal_does_not_exist():
    class _FakeRepo:
        def get_goal(self, _goal_id):
            return None

        def delete_goal(self, _goal_id):
            return False

    manager = GoalManager(memory_service=None, goal_repo=_FakeRepo())
    assert manager.delete_goal("missing-goal") is False
