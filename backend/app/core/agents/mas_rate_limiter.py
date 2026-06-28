import time

import structlog

logger = structlog.get_logger(__name__)


class MASRateLimiter:
    MAX_TOOL_CALLS_PER_CONVERSATION = 20
    MAX_AGENTS_PER_PROJECT = 5
    RESET_TIMEOUT = 60

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._last_activity: dict[str, float] = {}

    def check(self, conversation_id: str, count: int = 1) -> tuple[bool, str]:
        now = time.time()
        self._cleanup(now)

        if conversation_id not in self._counters:
            self._counters[conversation_id] = 0
            self._last_activity[conversation_id] = now

        self._counters[conversation_id] += count
        self._last_activity[conversation_id] = now

        if self._counters[conversation_id] > self.MAX_TOOL_CALLS_PER_CONVERSATION:
            return False, f"Rate limit exceeded: max {self.MAX_TOOL_CALLS_PER_CONVERSATION} tool calls per conversation"

        return True, ""

    def reset(self, conversation_id: str) -> None:
        self._counters.pop(conversation_id, None)
        self._last_activity.pop(conversation_id, None)

    def _cleanup(self, now: float) -> None:
        stale = [
            cid for cid, last in self._last_activity.items()
            if now - last > self.RESET_TIMEOUT
        ]
        for cid in stale:
            self._counters.pop(cid, None)
            self._last_activity.pop(cid, None)

    def get_count(self, conversation_id: str) -> int:
        return self._counters.get(conversation_id, 0)


mas_rate_limiter = MASRateLimiter()
