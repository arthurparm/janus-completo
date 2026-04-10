import pytest

from app.core.exceptions.chat_exceptions import ChatServiceError
from app.services.chat.conversation_service import ConversationService


class _FakeRepo:
    def __init__(self):
        self.conv = {
            "persona": "assistant",
            "project_id": "proj-1",
            "messages": [{"timestamp": 1.0, "role": "user", "text": "hello"}],
        }
        self.last_paginated_limit = None
        self.rename_args = None
        self.delete_args = None
        self.update_args = None
        self.delete_message_args = None

    def start_conversation(self, persona, project_id):
        self.conv["persona"] = persona
        self.conv["user_id"] = user_id
        self.conv["project_id"] = project_id
        return "conv-1"

    def count_conversations(self):
        return 1

    def get_conversation(self, conversation_id):
        if conversation_id != "conv-1":
            raise ValueError("unknown conversation")
        return self.conv

    def get_history_paginated(self, conversation_id, limit, offset, before_ts, after_ts):
        self.last_paginated_limit = limit
        return {
            "messages": self.conv["messages"],
            "total_count": 1,
            "has_more": False,
            "next_offset": None,
            "limit": limit,
            "offset": offset,
        }

    def list_conversations(self, project_id=None, limit=50):
        return [{"conversation_id": "conv-1"}][:limit]

    def rename_conversation(self, conversation_id, new_title, project_id=None):
        self.rename_args = (conversation_id, new_title, project_id)

    def delete_conversation(self, conversation_id, project_id=None):
        self.delete_args = (conversation_id, project_id)

    def update_message_text(self, conversation_id, message_id, new_text):
        self.update_args = (conversation_id, message_id, new_text)

    def delete_message(self, conversation_id, message_id):
        self.delete_message_args = (conversation_id, message_id)


def test_validate_conversation_access_blocks_user_mismatch():
    service = ConversationService(_FakeRepo())
    conv = {"project_id": "proj-1"}

    with pytest.raises(ChatServiceError, match="user_id mismatch"):
        service.validate_conversation_access("conv-1", conv, project_id=None)


def test_get_history_paginated_caps_limit():
    repo = _FakeRepo()
    service = ConversationService(repo)

    result = service.get_history_paginated(
        conversation_id="conv-1",
        limit=999,
        project_id="proj-1",
    )

    assert repo.last_paginated_limit == 200
    assert result["conversation_id"] == "conv-1"
    assert result["total_count"] == 1
    assert len(result["messages"]) == 1


def test_get_history_reconciles_resolved_pending_actions(monkeypatch):
    repo = _FakeRepo()
    repo.conv["messages"] = [
        {
            "timestamp": 1.0,
            "role": "assistant",
            "text": "Pedido classificado como alto risco.",
            "confirmation": {
                "required": True,
                "reason": "high_risk",
                "pending_action_id": 42,
                "approve_endpoint": "/api/v1/pending_actions/action/42/approve",
                "reject_endpoint": "/api/v1/pending_actions/action/42/reject",
            },
            "understanding": {
                "requires_confirmation": True,
                "confirmation_reason": "high_risk",
                "confirmation": {
                    "required": True,
                    "pending_action_id": 42,
                    "approve_endpoint": "/api/v1/pending_actions/action/42/approve",
                    "reject_endpoint": "/api/v1/pending_actions/action/42/reject",
                },
            },
            "agent_state": {
                "state": "waiting_confirmation",
                "requires_confirmation": True,
                "reason": "high_risk",
            },
        }
    ]
    service = ConversationService(repo)

    class _ResolvedPendingAction:
        status = "approved"

    class _FakePendingActionRepo:
        def get(self, action_id):
            assert action_id == 42
            return _ResolvedPendingAction()

    monkeypatch.setattr(
        "app.repositories.pending_action_repository.PendingActionRepository",
        lambda *args, **kwargs: _FakePendingActionRepo(),
    )

    result = service.get_history("conv-1", project_id="proj-1")
    message = result["messages"][0]

    assert message["confirmation"]["required"] is False
    assert message["confirmation"]["status"] == "approved"
    assert "approve_endpoint" not in message["confirmation"]
    assert message["understanding"]["requires_confirmation"] is False
    assert message["understanding"]["confirmation"]["status"] == "approved"
    assert message["agent_state"]["state"] == "completed"
    assert message["agent_state"]["reason"] == "approved"


@pytest.mark.asyncio
async def test_crud_operations_delegate_to_repo():
    repo = _FakeRepo()
    service = ConversationService(repo)

    await service.rename_conversation("conv-1", "Novo titulo", project_id="proj-1")
    await service.delete_conversation("conv-1", project_id="proj-1")
    await service.update_message("conv-1", 10, "Novo texto")
    await service.delete_message("conv-1", 10)

    assert repo.rename_args == ("conv-1", "Novo titulo", "user-1", "proj-1")
    assert repo.delete_args == ("conv-1", "user-1", "proj-1")
    assert repo.update_args == ("conv-1", 10, "Novo texto", "user-1")
    assert repo.delete_message_args == ("conv-1", 10, "user-1")
