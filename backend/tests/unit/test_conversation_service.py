import pytest

from app.core.exceptions.chat_exceptions import ChatServiceError
from app.services.chat.conversation_service import ConversationService


class _FakeRepo:
    def __init__(self):
        self.conv = {
            "persona": "assistant",
            "user_id": "user-1",
            "project_id": "proj-1",
            "messages": [{"timestamp": 1.0, "role": "user", "text": "hello"}],
        }
        self.last_paginated_limit = None
        self.rename_args = None
        self.delete_args = None
        self.update_args = None
        self.delete_message_args = None

    def start_conversation(self, persona, user_id, project_id):
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

    def list_conversations(self, user_id=None, project_id=None, limit=50):
        return [{"conversation_id": "conv-1"}][:limit]

    def rename_conversation(self, conversation_id, new_title, user_id=None, project_id=None):
        self.rename_args = (conversation_id, new_title, user_id, project_id)

    def delete_conversation(self, conversation_id, user_id=None, project_id=None):
        self.delete_args = (conversation_id, user_id, project_id)

    def update_message_text(self, conversation_id, message_id, new_text, user_id=None):
        self.update_args = (conversation_id, message_id, new_text, user_id)

    def delete_message(self, conversation_id, message_id, user_id=None):
        self.delete_message_args = (conversation_id, message_id, user_id)


def test_validate_conversation_access_blocks_user_mismatch():
    service = ConversationService(_FakeRepo())
    conv = {"user_id": "owner-1", "project_id": "proj-1"}

    with pytest.raises(ChatServiceError, match="user_id mismatch"):
        service.validate_conversation_access("conv-1", conv, user_id="other-user", project_id=None)


def test_get_history_paginated_caps_limit():
    repo = _FakeRepo()
    service = ConversationService(repo)

    result = service.get_history_paginated(
        conversation_id="conv-1",
        limit=999,
        user_id="user-1",
        project_id="proj-1",
    )

    assert repo.last_paginated_limit == 200
    assert result["conversation_id"] == "conv-1"
    assert result["total_count"] == 1
    assert len(result["messages"]) == 1


@pytest.mark.asyncio
async def test_crud_operations_delegate_to_repo():
    repo = _FakeRepo()
    service = ConversationService(repo)

    await service.rename_conversation("conv-1", "Novo titulo", user_id="user-1", project_id="proj-1")
    await service.delete_conversation("conv-1", user_id="user-1", project_id="proj-1")
    await service.update_message("conv-1", 10, "Novo texto", user_id="user-1")
    await service.delete_message("conv-1", 10, user_id="user-1")

    assert repo.rename_args == ("conv-1", "Novo titulo", "user-1", "proj-1")
    assert repo.delete_args == ("conv-1", "user-1", "proj-1")
    assert repo.update_args == ("conv-1", 10, "Novo texto", "user-1")
    assert repo.delete_message_args == ("conv-1", 10, "user-1")
