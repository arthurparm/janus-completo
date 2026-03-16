import asyncio

from app.core.llm import ModelPriority, ModelRole
from app.services.llm_service import LLMService


class _FakeRepo:
    def __init__(self):
        self.calls = []

    async def invoke_llm(self, prompt, role, priority, timeout_seconds, **kwargs):
        self.calls.append(
            {
                "prompt": prompt,
                "role": role,
                "priority": priority,
                "timeout_seconds": timeout_seconds,
                **kwargs,
            }
        )
        return {"response": "ok", "provider": "ollama", "model": "qwen2.5:14b"}


def test_invoke_llm_preserves_strict_ollama_policy_overrides():
    repo = _FakeRepo()
    service = LLMService(repo=repo)

    asyncio.run(
        service.invoke_llm(
            prompt="teste",
            role=ModelRole.KNOWLEDGE_CURATOR,
            priority=ModelPriority.HIGH_QUALITY,
            timeout_seconds=30,
            policy_overrides={
                "provider": "ollama",
                "model": "qwen2.5:14b",
                "strict_provider": True,
                "disable_failover": True,
                "disable_response_cache": True,
            },
        )
    )

    assert len(repo.calls) == 1
    call = repo.calls[0]
    assert call["llm_config"]["provider"] == "ollama"
    assert call["llm_config"]["model"] == "qwen2.5:14b"
    assert call["llm_config"]["strict_provider"] is True
    assert call["llm_config"]["disable_failover"] is True
    assert call["llm_config"]["disable_response_cache"] is True
