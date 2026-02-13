import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.join(os.getcwd(), "janus"))

import app.core.autonomy.policy_engine as policy_module
from app.core.autonomy.policy_engine import PolicyConfig, PolicyEngine, RiskProfile
from app.core.tools.action_module import PermissionLevel, ToolCategory, ToolMetadata


def _patch_registry(monkeypatch, metadata: ToolMetadata):
    registry = SimpleNamespace(
        get_tool=lambda name: object() if name == metadata.name else None,
        get_metadata=lambda name: metadata if name == metadata.name else None,
        check_rate_limit=lambda _name, user_id=None: True,
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
