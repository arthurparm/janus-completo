import os
import pytest
from app.services.chat_service import ChatService
from app.repositories.chat_repository_sql import ChatRepositorySQL
from app.services.llm_service import LLMService


class DummyLLM(LLMService):
    def invoke_llm(self, prompt, role, priority, timeout_seconds=None, user_id=None, project_id=None):
        return {"response": "Olá 🌟", "provider": "dummy", "model": "m"}
    def select_provider(self, role, priority, user_id=None, project_id=None):
        return {"provider": "dummy", "model": "m"}
    def is_provider_open(self, provider: str) -> bool:
        return False


@pytest.mark.asyncio
async def test_utf8_and_heartbeat_emission():
    os.environ["CHAT_HEARTBEAT_INTERVAL_SECONDS"] = "1"
    repo = ChatRepositorySQL()
    svc = ChatService(repo, DummyLLM(), None)
    cid = svc.start_conversation("assistant", None, None)
    gen = svc.stream_message(conversation_id=cid, message="olá", role=None, priority=None)
    lines = [l async for l in gen]
    assert any(l.startswith("event: heartbeat") for l in lines)
    token_lines = [l for l in lines if l.startswith("event: token")]
    assert token_lines, lines
    # UTF-8 payload must contain emoji/acento
    datas = [l.split("data:")[-1] for l in token_lines]
    assert any("Olá" in d or "\u00e1" not in d for d in datas)