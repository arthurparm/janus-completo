from __future__ import annotations

from pathlib import Path

from janus.adapter import Proposal
from janus.entry import Budget, OpenRunRequest
from janus.loop import Runtime


class ManualClock:
    def __init__(self, current: int = 0) -> None:
        self.current = current

    def now_ms(self) -> int:
        return self.current


def read_runtime(root: Path) -> Runtime:
    return Runtime(root, {"alpha": "conteudo-alpha"}, ManualClock())


def read_proposal() -> Proposal:
    return Proposal.from_mapping("read_record", {"record_id": "alpha"}, "ler")


def delete_proposal(key: str) -> Proposal:
    return Proposal.from_mapping("delete_record", {"record_id": "alpha", "idempotency_key": key}, "")


def alpha_request(permission: str = "read_record", *, max_steps: int = 3) -> OpenRunRequest:
    budget = Budget(max_steps, 1000, 3)
    return OpenRunRequest("arthur", permission, budget, True, "model-a", "ler o registro alpha")
