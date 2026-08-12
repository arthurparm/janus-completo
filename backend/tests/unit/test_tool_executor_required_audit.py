from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.services.tool_executor_service as service_module
from app.config import settings
from app.services.tool_executor_service import ToolExecutorService


class _AllowedPolicy:
    def can_continue_cycle(self) -> bool:
        return True

    def validate_content_safety(self, _args: str):
        return SimpleNamespace(allowed=True, reason=None)

    def simulate_tool_call(self, _name: str, _args: dict):
        return None

    def validate_tool_call(self, _name: str, _args: dict, *, user_id: str | None):
        return SimpleNamespace(allowed=True, require_confirmation=False, reason=None)


class _Tool:
    args_schema = None

    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, _args: dict):
        self.calls += 1
        return "real-result"


class _FailingTool(_Tool):
    async def ainvoke(self, _args: dict):
        self.calls += 1
        raise RuntimeError("provider unavailable")


def _configure_registry(monkeypatch, tool: _Tool) -> None:
    monkeypatch.setattr(service_module.action_registry, "get_tool", lambda _name: tool)
    monkeypatch.setattr(
        service_module.action_registry,
        "get_metadata",
        lambda _name: SimpleNamespace(permission_level=SimpleNamespace(value="read_only")),
    )
    monkeypatch.setattr(service_module.action_registry, "record_call", lambda **_kwargs: None)


@pytest.mark.asyncio
async def test_tool_execution_is_blocked_when_required_precheck_audit_fails(monkeypatch):
    tool = _Tool()
    _configure_registry(monkeypatch, tool)
    monkeypatch.setattr(settings, "TOOL_DAILY_QUOTAS", {})
    monkeypatch.setattr(settings, "TOOL_SLIDING_WINDOW_QUOTAS", {})
    audit_calls: list[dict[str, object]] = []

    def _audit(event, *, required=False, **_kwargs):
        audit_calls.append({"event": event, "required": required})
        return False

    monkeypatch.setattr(service_module, "record_audit_event_direct", _audit)

    result = await ToolExecutorService().execute_tool_calls(
        [{"name": "read_data", "args": {}}],
        policy=_AllowedPolicy(),  # type: ignore[arg-type]
        user_id="7",
    )

    assert tool.calls == 0
    assert "required audit event" in result[0]["result"]
    assert audit_calls[0]["required"] is True
    assert audit_calls[0]["event"]["status"] == "approved"  # type: ignore[index]


@pytest.mark.asyncio
async def test_tool_execution_records_approval_and_outcome(monkeypatch):
    tool = _Tool()
    _configure_registry(monkeypatch, tool)
    monkeypatch.setattr(settings, "TOOL_DAILY_QUOTAS", {})
    monkeypatch.setattr(settings, "TOOL_SLIDING_WINDOW_QUOTAS", {})
    audit_calls: list[dict[str, object]] = []

    def _audit(event, *, required=False, **_kwargs):
        audit_calls.append({"event": event, "required": required})
        return True

    monkeypatch.setattr(service_module, "record_audit_event_direct", _audit)

    result = await ToolExecutorService().execute_tool_calls(
        [{"name": "read_data", "args": {}}],
        policy=_AllowedPolicy(),  # type: ignore[arg-type]
        user_id="7",
    )

    assert tool.calls == 1
    assert result == [{"name": "read_data", "result": "real-result"}]
    assert [call["event"]["status"] for call in audit_calls] == [  # type: ignore[index]
        "approved",
        "succeeded",
    ]
    assert audit_calls[0]["required"] is True
    assert audit_calls[1]["required"] is False


@pytest.mark.asyncio
async def test_tool_failure_records_failed_outcome(monkeypatch):
    tool = _FailingTool()
    _configure_registry(monkeypatch, tool)
    monkeypatch.setattr(settings, "TOOL_DAILY_QUOTAS", {})
    monkeypatch.setattr(settings, "TOOL_SLIDING_WINDOW_QUOTAS", {})
    statuses: list[str] = []

    def _audit(event, *, required=False, **_kwargs):
        statuses.append(event["status"])
        return True

    monkeypatch.setattr(service_module, "record_audit_event_direct", _audit)
    monkeypatch.setattr(service_module.action_registry, "get_namespace", lambda _name: "core")

    result = await ToolExecutorService().execute_tool_calls(
        [{"name": "read_data", "args": {}}],
        policy=_AllowedPolicy(),  # type: ignore[arg-type]
        user_id="7",
    )

    assert tool.calls == 1
    assert "Tool Error" in result[0]["result"]
    assert statuses == ["approved", "failed"]
