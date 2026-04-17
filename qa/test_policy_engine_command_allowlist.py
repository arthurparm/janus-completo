import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.join(os.getcwd(), "backend"))

import app.core.autonomy.policy_engine as policy_module
from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine, RiskProfile
from app.core.tools.action_module import PermissionLevel, ToolCategory, ToolMetadata


def _patch_registry(monkeypatch, metadata: ToolMetadata):
    registry = SimpleNamespace(
        get_tool=lambda name, **kwargs: object() if name == metadata.name else None,
        get_metadata=lambda name, **kwargs: metadata if name == metadata.name else None,
        check_rate_limit=lambda _name, **kwargs: True,
    )
    monkeypatch.setattr(policy_module, "action_registry", registry)


def test_policy_engine_blocks_command_with_blocklisted_token(monkeypatch):
    meta = ToolMetadata(
        name="execute_shell",
        category=ToolCategory.SYSTEM,
        description="shell",
        permission_level=PermissionLevel.DANGEROUS,
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            auto_confirm=False,
            allowlist={"execute_shell"},
            command_allowlist={"echo ", "dir"},
        )
    )
    decision = engine.validate_tool_call("execute_shell", {"command": "rm -rf /tmp/demo"})

    assert decision.allowed is False
    assert "blocked" in str(decision.reason).lower()


def test_policy_engine_requires_confirmation_for_sensitive_command_without_allowlist(monkeypatch):
    meta = ToolMetadata(
        name="execute_shell",
        category=ToolCategory.SYSTEM,
        description="shell",
        permission_level=PermissionLevel.DANGEROUS,
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            auto_confirm=False,
            allowlist={"execute_shell"},
            command_allowlist=set(),
        )
    )
    decision = engine.validate_tool_call("execute_shell", {"command": "echo hello"})

    assert decision.allowed is False
    assert decision.require_confirmation is True


def test_policy_engine_blocks_tool_outside_capability_allowlist(monkeypatch):
    meta = ToolMetadata(
        name="browse_url",
        category=ToolCategory.WEB,
        description="browse",
        permission_level=PermissionLevel.SAFE,
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            capability_allowlist={"filesystem"},
        )
    )
    decision = engine.validate_tool_call("browse_url", {"url": "https://example.com"})

    assert decision.allowed is False
    assert "capability" in str(decision.reason).lower()


def test_policy_engine_fail_closed_for_sensitive_command_without_allowlist(monkeypatch):
    meta = ToolMetadata(
        name="execute_shell",
        category=ToolCategory.SYSTEM,
        description="shell",
        permission_level=PermissionLevel.DANGEROUS,
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            auto_confirm=True,
            allowlist={"execute_shell"},
            command_allowlist=set(),
        )
    )
    decision = engine.validate_tool_call("execute_shell", {"command": "echo hello"})

    assert decision.allowed is False
    assert "allowlist" in str(decision.reason).lower()


def test_policy_engine_blocks_tool_without_scope_tag_when_scope_allowlist_enabled(monkeypatch):
    meta = ToolMetadata(
        name="browse_url",
        category=ToolCategory.WEB,
        description="browse",
        permission_level=PermissionLevel.SAFE,
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            scope_allowlist={"calendar.read"},
        )
    )
    decision = engine.validate_tool_call("browse_url", {"url": "https://example.com"})

    assert decision.allowed is False
    assert "scope" in str(decision.reason).lower()


def test_policy_engine_blocks_tool_outside_scope_allowlist(monkeypatch):
    meta = ToolMetadata(
        name="calendar_write",
        category=ToolCategory.API,
        description="calendar write",
        permission_level=PermissionLevel.WRITE,
        tags=["scope:calendar.write", "personal"],
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            scope_allowlist={"calendar.read"},
        )
    )
    decision = engine.validate_tool_call("calendar_write", {"event": "demo"})

    assert decision.allowed is False
    assert "outside allowlist" in str(decision.reason).lower()


def test_policy_engine_allows_tool_inside_scope_allowlist(monkeypatch):
    meta = ToolMetadata(
        name="calendar_read",
        category=ToolCategory.API,
        description="calendar read",
        permission_level=PermissionLevel.READ_ONLY,
        tags=["scope:calendar.read", "personal"],
    )
    _patch_registry(monkeypatch, meta)

    engine = PolicyEngine(
        PolicyConfig(
            risk_profile=RiskProfile.BALANCED,
            scope_allowlist={"calendar.read"},
        )
    )
    decision = engine.validate_tool_call("calendar_read", {"window": "today"})

    assert decision.allowed is True
