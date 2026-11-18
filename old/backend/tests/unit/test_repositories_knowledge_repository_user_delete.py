from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.knowledge_repository import KnowledgeRepository


@pytest.mark.asyncio
async def test_delete_user_data_scopes_by_user_id():
    db = MagicMock()
    db.execute = AsyncMock()
    db.query = AsyncMock(return_value=[{"total": 0}])
    repo = KnowledgeRepository(db)

    remaining = await repo.delete_user_data("user-123")

    assert remaining == 0
    db.execute.assert_awaited_once()
    cypher, params = db.execute.call_args.args[:2]
    assert "user_id" in str(cypher)
    assert params == {"user_id": "user-123"}
    db.query.assert_awaited()

