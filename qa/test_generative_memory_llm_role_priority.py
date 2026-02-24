import os
import sys

import pytest

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.llm import ModelPriority, ModelRole
from app.core.memory.generative_memory import GenerativeMemoryService


class DummyLLMService:
    def __init__(self):
        self.calls = []

    async def invoke_llm(self, **kwargs):
        self.calls.append(kwargs)
        return {"response": "7"}


@pytest.mark.asyncio
async def test_calculate_importance_uses_valid_llm_enums():
    service = GenerativeMemoryService()
    llm = DummyLLMService()
    service._llm_service = llm

    score = await service._calculate_importance("memory test")

    assert score == 7.0
    assert len(llm.calls) == 1
    assert llm.calls[0]["role"] == ModelRole.REASONER
    assert llm.calls[0]["priority"] == ModelPriority.FAST_AND_CHEAP
