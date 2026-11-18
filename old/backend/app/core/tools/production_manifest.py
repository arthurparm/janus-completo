from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from app.core.security.security_alerts import emit_security_alert
from app.core.tools.action_module import PermissionLevel, ToolCategory, action_registry
from app.core.tools.safe_tools import APPROVED_TOOLS


@dataclass(frozen=True, slots=True)
class ProductionToolEntry:
    name: str
    version: str
    source_sha256: str
    owner: str
    permission: str
    roles: tuple[str, ...]
    environments: tuple[str, ...]
    prerequisites: tuple[str, ...]


def _manifest_path() -> Path:
    return Path(__file__).with_name("production_tool_manifest.json")


def _source_hash() -> str:
    return hashlib.sha256(Path(__file__).with_name("safe_tools.py").read_bytes()).hexdigest()


def load_production_manifest() -> dict[str, ProductionToolEntry]:
    raw = json.loads(_manifest_path().read_text(encoding="utf-8"))
    source_hash = str(raw["source_sha256"])
    entries = {
        item["name"]: ProductionToolEntry(
            name=item["name"],
            version=item["version"],
            source_sha256=source_hash,
            owner=item["owner"],
            permission=item["permission"],
            roles=tuple(item["roles"]),
            environments=tuple(item["environments"]),
            prerequisites=tuple(item["prerequisites"]),
        )
        for item in raw["tools"]
    }
    expected_names = {tool.name for tool in APPROVED_TOOLS}
    if set(entries) != expected_names:
        raise RuntimeError("production tool manifest does not match approved tool implementation")
    actual_hash = _source_hash()
    if any(entry.source_sha256 != actual_hash for entry in entries.values()):
        emit_security_alert("production_tool_hash_mismatch", {"source": "safe_tools.py"})
        raise RuntimeError("production tool source hash does not match homologated manifest")
    return entries


def register_production_tools() -> None:
    entries = load_production_manifest()
    action_registry.clear_and_lock_manifest(frozenset(entries))
    for tool in APPROVED_TOOLS:
        entry = entries[tool.name]
        action_registry.register(
            tool,
            category=ToolCategory.SYSTEM if tool.name in {"get_current_datetime", "render_ui_component"} else ToolCategory.DATABASE,
            permission_level=PermissionLevel.READ_ONLY,
            namespace="production",
            code_signature=entry.source_sha256,
            tags=["homologated", entry.version],
        )
    if {tool.name for tool in action_registry.list_tools()} != set(entries):
        raise RuntimeError("production registry differs from homologated manifest")
