import pytest
import asyncio
from app.services.chat_service import ChatService
from app.repositories.chat_repository_sql import ChatRepositorySQL


class DummyLLMService:
  def __init__(self, open_state=True):
    self._open = open_state
  def select_provider(self, role, priority, user_id=None, project_id=None):
    return {"provider": "dummy", "model": "m"}
  def is_provider_open(self, provider: str) -> bool:
    return True
  def invoke_llm(self, **kwargs):
    return {"response": "ok", "provider": "dummy", "model": "m"}


@pytest.mark.asyncio
async def test_cb_early_block_emits_error_circuit_open():
  repo = ChatRepositorySQL()
  svc = ChatService(repo, DummyLLMService(), None)
  cid = svc.start_conversation("assistant", None, None)
  gen = svc.stream_message(conversation_id=cid, message="hello", role=None, priority=None)
  lines = [l async for l in gen]
  errs = [l for l in lines if l.startswith("event: error")]
  assert errs, lines
  payloads = [l.split("data:")[-1].strip() for l in errs]
  assert any("CircuitOpen" in p for p in payloads)