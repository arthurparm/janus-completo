import os
import sys

import pytest

sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.memory.memory_core import MemoryCore
from app.models.schemas import Experience


class _Settings:
    MEMORY_QUOTA_WINDOW_SECONDS = 3600
    MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 2
    MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN = 1024
    MEMORY_MAX_CONTENT_CHARS = 20000


def _exp(content: str, origin: str = "chat") -> Experience:
    return Experience(type="episodic", content=content, metadata={"origin": origin})


def test_memory_quota_rejects_when_item_limit_exceeded():
    settings = _Settings()
    settings.MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 1
    settings.MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN = 1024
    memory = MemoryCore(client=object(), config=settings)

    first = _exp("hello")
    second = _exp("world")

    memory._check_quota(first)
    memory._update_quota(first)

    with pytest.raises(ValueError, match="item quota exceeded"):
        memory._check_quota(second)


def test_memory_quota_rejects_when_byte_limit_exceeded():
    settings = _Settings()
    settings.MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 10
    settings.MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN = 5
    memory = MemoryCore(client=object(), config=settings)

    first = _exp("1234")
    second = _exp("12")

    memory._check_quota(first)
    memory._update_quota(first)

    with pytest.raises(ValueError, match="byte quota exceeded"):
        memory._check_quota(second)


def test_memory_quota_window_resets(monkeypatch):
    settings = _Settings()
    settings.MEMORY_QUOTA_WINDOW_SECONDS = 1
    settings.MEMORY_QUOTA_MAX_ITEMS_PER_ORIGIN = 1
    settings.MEMORY_QUOTA_MAX_BYTES_PER_ORIGIN = 1024
    memory = MemoryCore(client=object(), config=settings)

    times = iter([1000.0, 1000.0, 1002.0])
    import app.core.memory.memory_core as memory_module

    monkeypatch.setattr(memory_module.time, "time", lambda: next(times))

    first = _exp("a")
    second = _exp("b")

    memory._check_quota(first)
    memory._update_quota(first)
    memory._check_quota(second)
