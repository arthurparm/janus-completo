import os
import sys
from dataclasses import dataclass

import pytest

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.reflexion_service import ReflexionService


class _DummyRepo:
    def __init__(self, payload):
        self._payload = payload

    async def run_cycle(self, task, config):
        return self._payload


@pytest.mark.asyncio
async def test_reflexion_service_normalizes_integer_steps_and_contract():
    payload = {
        "success": True,
        "result": "ok",
        "score": 0.91,
        "steps": [1, 2],
        "lessons": ["L1"],
        "elapsed_seconds": None,
    }
    service = ReflexionService(repo=_DummyRepo(payload))

    result = await service.run_reflexion_cycle("task", {"success_threshold": 0.8})

    assert result["success"] is True
    assert result["best_result"] == "ok"
    assert result["best_score"] == pytest.approx(0.91)
    assert result["iterations"] == 2
    assert result["lessons_learned"] == ["L1"]
    assert isinstance(result["elapsed_seconds"], float)
    assert len(result["steps"]) == 2
    assert result["steps"][0]["iteration"] == 1
    assert result["steps"][1]["iteration"] == 2
    assert result["steps"][0]["action"] == ""
    assert result["steps"][0]["improvements"] == []


@dataclass
class _LocalStep:
    iteration: int
    action: str
    observation: str
    reflection: str
    score: float
    improvements: list[str]
    timestamp: float


@pytest.mark.asyncio
async def test_reflexion_service_accepts_dataclass_steps():
    payload = {
        "success": False,
        "result": "draft",
        "score": 0.5,
        "steps": [
            _LocalStep(
                iteration=1,
                action="attempt",
                observation="obs",
                reflection="refl",
                score=0.5,
                improvements=["retry"],
                timestamp=123.0,
            )
        ],
        "lessons": [],
    }
    service = ReflexionService(repo=_DummyRepo(payload))

    result = await service.run_reflexion_cycle("task", {"success_threshold": 0.8})

    assert result["iterations"] == 1
    assert result["steps"][0]["action"] == "attempt"
    assert result["steps"][0]["observation"] == "obs"
    assert result["steps"][0]["reflection"] == "refl"
    assert result["steps"][0]["score"] == pytest.approx(0.5)
