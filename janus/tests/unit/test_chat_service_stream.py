import json
import asyncio
from app.services.chat_service import ChatService
from app.repositories.chat_repository_sql import ChatRepositorySQL
from app.services.llm_service import LLMService


class DummyLLM(LLMService):
    def invoke_llm(self, prompt, role, priority, timeout_seconds=None, user_id=None, project_id=None):
        return {"response": "ok", "provider": "dummy", "model": "m"}


@pytest.mark.asyncio
async def test_stream_message_emits_token_and_done():
    repo = ChatRepositorySQL()
    svc = ChatService(repo, DummyLLM(), None)
    cid = svc.start_conversation("assistant", None, None)
    gen = svc.stream_message(conversation_id=cid, message="hello", role=None, priority=None)
    lines = [l async for l in gen]
    assert any(l.startswith("event: token") for l in lines)
    assert any(l.startswith("event: done") for l in lines)


@pytest.mark.asyncio
async def test_stream_message_rejects_large_message():
    repo = ChatRepositorySQL()
    svc = ChatService(repo, DummyLLM(), None)
    cid = svc.start_conversation("assistant", None, None)
    big = "x" * (11 * 1024)
    gen = svc.stream_message(conversation_id=cid, message=big, role=None, priority=None)
    lines = [l async for l in gen]
    err = [l for l in lines if l.startswith("event: error")]
    assert err, lines
    payloads = [l.split("data:")[-1].strip() for l in err]
    parsed = [json.loads(p) for p in payloads]
    assert any(p.get("code") == "MessageTooLarge" for p in parsed)
