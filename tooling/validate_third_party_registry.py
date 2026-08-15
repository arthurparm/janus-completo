"""Validate documentation/compliance/third-parties-register.json against its schema.

Uses pydantic (already a first-class backend dependency) instead of hand-rolled
dict-walking so the shape of a provider entry is declared once and every error
message comes from the same, consistent validator machinery.
"""

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

ProviderCategory = Literal["llm", "oauth", "web_search", "auth", "infra_external", "analytics"]


class ProviderEntry(BaseModel):
    id: str = Field(min_length=1)
    category: ProviderCategory
    provider_keys: list[str] = Field(min_length=1)
    hosts: list[str] = Field(default_factory=list)
    code_refs: list[str] = Field(default_factory=list)

    @field_validator("provider_keys")
    @classmethod
    def _no_blank_provider_keys(cls, values: list[str]) -> list[str]:
        if any(not str(v or "").strip() for v in values):
            raise ValueError("provider_keys must not contain empty entries")
        return values

    @field_validator("hosts")
    @classmethod
    def _normalize_hosts(cls, values: list[str]) -> list[str]:
        normalized = [str(h or "").strip().lower().strip(".") for h in values]
        if any(not h for h in normalized):
            raise ValueError("hosts must not contain empty entries")
        return normalized


class ThirdPartyRegistry(BaseModel):
    classification: Literal["internal-only"]
    providers: list[ProviderEntry]

    @model_validator(mode="after")
    def _no_duplicates(self) -> "ThirdPartyRegistry":
        _assert_unique((p.id for p in self.providers), "id")
        _assert_unique((k for p in self.providers for k in p.provider_keys), "provider_key")
        _assert_unique((h for p in self.providers for h in p.hosts), "host")
        return self


def _assert_unique(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {label}: {value}")
        seen.add(value)


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_registry(repo_root: Path, registry_path: Path) -> list[str]:
    payload = _read_json(registry_path)
    try:
        registry = ThirdPartyRegistry.model_validate(payload)
    except ValidationError as exc:
        return [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        ]

    errors: list[str] = []
    for provider in registry.providers:
        for rel_path in provider.code_refs:
            if not (repo_root / rel_path).resolve().exists():
                errors.append(f"{provider.id}: missing code_refs file {rel_path}")
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    registry_path = repo_root / "documentation" / "compliance" / "third-parties-register.json"
    if len(sys.argv) > 1:
        registry_path = (repo_root / sys.argv[1]).resolve()

    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 2

    errors = _validate_registry(repo_root=repo_root, registry_path=registry_path)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
