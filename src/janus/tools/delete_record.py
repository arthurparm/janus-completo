from __future__ import annotations

from collections.abc import Mapping

from janus.tools.read_record import ToolSpec
from janus.util.codec import JanusError


DELETE_RECORD = ToolSpec(
    name="delete_record",
    risk_class="escrita_irreversivel",
    permission="delete_record",
    cost=1,
    argument_names=("record_id", "idempotency_key"),
)


def plain_language(record_id: str) -> tuple[str, str]:
    action = f"Apagar o registro {record_id}"
    effect = f"O registro {record_id} deixa de existir e não há como desfazer."
    return action, effect


class DeleteRecordTool:
    def __init__(self) -> None:
        self._calls: list[str] = []

    def calls(self) -> tuple[str, ...]:
        return tuple(self._calls)

    def execute(self, arguments: Mapping[str, str]) -> None:
        # Fase A não envia a escrita. A chamada fica visível e não há efeito.
        self._calls.append(arguments["idempotency_key"])
        raise JanusError("escrita irreversível não executa")