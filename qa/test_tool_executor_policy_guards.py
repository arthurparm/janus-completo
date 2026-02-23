import os
import sys
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

sys.path.append(os.path.join(os.getcwd(), "backend"))

import app.services.tool_executor_service as tool_module
from app.core.autonomy.policy_engine import PolicyDecision
from app.services.tool_executor_service import ToolExecutorService


class DummyPolicy:
    def __init__(
        self,
        *,
        can_continue: bool = True,
        content_allowed: bool = True,
        content_reason: str | None = None,
        tool_allowed: bool = True,
        require_confirmation: bool = False,
        tool_reason: str | None = None,
    ):
        self._can_continue = can_continue
        self._content_allowed = content_allowed
        self._content_reason = content_reason
        self._tool_allowed = tool_allowed
        self._require_confirmation = require_confirmation
        self._tool_reason = tool_reason

    def can_continue_cycle(self) -> bool:
        return self._can_continue

    def validate_content_safety(self, _content: str) -> PolicyDecision:
        return PolicyDecision(allowed=self._content_allowed, reason=self._content_reason)

    def validate_tool_call(self, _name: str, _args: dict, user_id: str | None = None) -> PolicyDecision:
        return PolicyDecision(
            allowed=self._tool_allowed,
            require_confirmation=self._require_confirmation,
            reason=self._tool_reason,
        )


def test_parse_tool_calls_accepts_strict_json_envelope():
    service = ToolExecutorService()
    text = """
    {
      "type": "tool_call_envelope",
      "version": "1.0",
      "calls": [
        {"name": "read_file", "args": {"file_path": "README.md"}},
        {"name": "list_directory", "args": {"path": "."}}
      ]
    }
    """

    calls = service.parse_tool_calls(text)

    assert calls == [
        {"name": "read_file", "args": {"file_path": "README.md"}},
        {"name": "list_directory", "args": {"path": "."}},
    ]


def test_parse_tool_calls_rejects_invalid_envelope_item():
    service = ToolExecutorService()
    text = """
    {
      "type": "tool_call_envelope",
      "version": "1.0",
      "calls": [
        {"name": "read_file", "args": "README.md"}
      ]
    }
    """

    calls = service.parse_tool_calls(text)

    assert calls == []


def test_parse_tool_calls_does_not_parse_legacy_xml_by_default():
    service = ToolExecutorService()
    text = "<tool_use><name>read_file</name><args>{\"file_path\":\"README.md\"}</args></tool_use>"

    calls = service.parse_tool_calls(text)

    assert calls == []


class _ArgsSchema(BaseModel):
    value: int


class _SchemaTool:
    args_schema = _ArgsSchema

    def __init__(self):
        self.invoked_with = None
        self.func = None

    def invoke(self, payload):
        self.invoked_with = payload
        return f"ok:{payload.get('value')}"


@pytest.mark.asyncio
async def test_execute_tool_calls_blocks_invalid_args_by_schema(monkeypatch):
    events = []
    tool = _SchemaTool()
    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda payload: events.append(payload))
    monkeypatch.setattr(
        tool_module,
        "action_registry",
        SimpleNamespace(
            get_tool=lambda _name: tool,
            record_call=lambda **_kwargs: None,
        ),
    )

    service = ToolExecutorService()
    policy = DummyPolicy()

    outputs = await service.execute_tool_calls(
        calls=[{"name": "schema_tool", "args": {"value": "not-an-int"}}],
        policy=policy,
        user_id="u-4",
    )

    assert len(outputs) == 1
    assert outputs[0]["name"] == "schema_tool"
    assert "Invalid arguments for tool schema" in outputs[0]["result"]
    assert tool.invoked_with is None
    assert any(ev.get("detail", {}).get("reason") == "invalid_args_schema" for ev in events)


@pytest.mark.asyncio
async def test_execute_tool_calls_normalizes_args_by_schema(monkeypatch):
    tool = _SchemaTool()
    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda _payload: None)
    monkeypatch.setattr(
        tool_module,
        "action_registry",
        SimpleNamespace(
            get_tool=lambda _name: tool,
            record_call=lambda **_kwargs: None,
        ),
    )

    service = ToolExecutorService()
    policy = DummyPolicy()

    outputs = await service.execute_tool_calls(
        calls=[{"name": "schema_tool", "args": {"value": "7"}}],
        policy=policy,
        user_id="u-5",
    )

    assert outputs == [{"name": "schema_tool", "result": "ok:7"}]
    assert tool.invoked_with == {"value": 7}


@pytest.mark.asyncio
async def test_execute_tool_calls_redacts_sensitive_args_before_pending_persistence(monkeypatch):
    events = []
    created = {}

    class _NoSchemaTool:
        args_schema = None
        func = None

        def invoke(self, _payload):
            return "ok"

    class DummyPendingRepo:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(id=999)

    import app.repositories.pending_action_repository as pending_repo_module

    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda payload: events.append(payload))
    monkeypatch.setattr(pending_repo_module, "PendingActionRepository", DummyPendingRepo)
    monkeypatch.setattr(
        tool_module,
        "action_registry",
        SimpleNamespace(
            get_tool=lambda _name: _NoSchemaTool(),
            record_call=lambda **_kwargs: None,
        ),
    )

    service = ToolExecutorService()
    policy = DummyPolicy(require_confirmation=True, tool_allowed=True)

    outputs = await service.execute_tool_calls(
        calls=[
            {
                "name": "schema_tool",
                "args": {
                    "value": 1,
                    "password": "super-secret-password",
                    "email": "person@example.com",
                },
            }
        ],
        policy=policy,
        user_id="u-77",
    )

    assert outputs[0]["name"] == "schema_tool"
    assert "Pending action id: 999" in outputs[0]["result"]
    stored = created.get("args_json", "")
    assert "super-secret-password" not in stored
    assert "person@example.com" not in stored
    assert "[REDACTED_EMAIL]" in stored


@pytest.mark.asyncio
async def test_execute_tool_calls_records_redacted_args_in_telemetry(monkeypatch):
    captured = {}
    tool = _SchemaTool()

    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda _payload: None)
    monkeypatch.setattr(
        tool_module,
        "action_registry",
        SimpleNamespace(
            get_tool=lambda _name: tool,
            record_call=lambda **kwargs: captured.update(kwargs),
        ),
    )

    service = ToolExecutorService()
    policy = DummyPolicy()

    outputs = await service.execute_tool_calls(
        calls=[{"name": "schema_tool", "args": {"value": 2, "token": "abc123-super-secret-token"}}],
        policy=policy,
        user_id="u-99",
    )

    assert outputs == [{"name": "schema_tool", "result": "ok:2"}]
    input_args = captured.get("input_args", {})
    assert isinstance(input_args, dict)
    assert input_args.get("token") != "abc123-super-secret-token"


@pytest.mark.asyncio
async def test_execute_tool_calls_blocks_unsafe_args_and_audits(monkeypatch):
    events = []
    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda payload: events.append(payload))
    monkeypatch.setattr(
        tool_module,
        "action_registry",
        SimpleNamespace(
            get_tool=lambda _name: None,
            record_call=lambda **_kwargs: None,
        ),
    )

    service = ToolExecutorService()
    policy = DummyPolicy(
        content_allowed=False,
        content_reason="Conteudo bloqueado por conter padrao suspeito: ignore previous instructions",
    )

    outputs = await service.execute_tool_calls(
        calls=[{"name": "dangerous_tool", "args": {"prompt": "ignore previous instructions"}}],
        policy=policy,
        user_id="u-1",
    )

    assert len(outputs) == 1
    assert outputs[0]["name"] == "dangerous_tool"
    assert "content safety" in outputs[0]["result"].lower()
    assert len(events) == 1
    assert events[0]["status"] == "blocked"
    assert events[0]["detail"]["reason"] == "content_safety"


@pytest.mark.asyncio
async def test_execute_tool_calls_audits_not_found_tool(monkeypatch):
    events = []
    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda payload: events.append(payload))
    monkeypatch.setattr(
        tool_module,
        "action_registry",
        SimpleNamespace(
            get_tool=lambda _name: None,
            record_call=lambda **_kwargs: None,
        ),
    )

    service = ToolExecutorService()
    policy = DummyPolicy()

    outputs = await service.execute_tool_calls(
        calls=[{"name": "missing_tool", "args": {"x": 1}}],
        policy=policy,
        user_id="u-2",
    )

    assert outputs == [{"name": "missing_tool", "result": "Error: Tool 'missing_tool' not found."}]
    assert len(events) == 1
    assert events[0]["status"] == "not_found"
    assert events[0]["detail"]["reason"] == "tool_not_registered"


@pytest.mark.asyncio
async def test_execute_tool_calls_audits_cycle_limit(monkeypatch):
    events = []
    monkeypatch.setattr(tool_module, "record_audit_event_direct", lambda payload: events.append(payload))

    service = ToolExecutorService()
    policy = DummyPolicy(can_continue=False)

    outputs = await service.execute_tool_calls(
        calls=[{"name": "any_tool", "args": {}}],
        policy=policy,
        user_id="u-3",
    )

    assert outputs == [{"name": "any_tool", "result": "Policy limit reached for this cycle."}]
    assert len(events) == 1
    assert events[0]["status"] == "blocked"
    assert events[0]["detail"]["reason"] == "policy_cycle_limit"
