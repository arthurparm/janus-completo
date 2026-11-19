from janus.tools.delete_record import DELETE_RECORD, DeleteRecordTool
from janus.tools.read_record import READ_RECORD, ReadRecordTool, ToolOutput, ToolSpec

ALLOWLIST: dict[str, ToolSpec] = {
    READ_RECORD.name: READ_RECORD,
    DELETE_RECORD.name: DELETE_RECORD,
}


def tool_cost(name: str) -> int:
    spec = ALLOWLIST.get(name)
    if spec is None:
        return 0
    return spec.cost


__all__ = [
    "ALLOWLIST",
    "DELETE_RECORD",
    "DeleteRecordTool",
    "READ_RECORD",
    "ReadRecordTool",
    "ToolOutput",
    "ToolSpec",
    "tool_cost",
]
