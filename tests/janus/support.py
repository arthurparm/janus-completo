from __future__ import annotations


class ManualClock:
    def __init__(self, current: int = 0) -> None:
        self.current = current

    def now_ms(self) -> int:
        return self.current
