#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from openapi_spec_validator import validate

PROFILES = ("public", "user", "control-plane")
ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "documentation" / "openapi" / "current"
POLICY_MANIFEST = ROOT / "backend" / "app" / "core" / "security" / "endpoint_policy_manifest.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _render_profile(profile: str) -> dict[str, Any]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(ROOT / "backend"),
            "JANUS_API_PROFILE": profile,
            "JANUS_SKIP_EXTERNAL_STARTUP": "true",
            "ENVIRONMENT": "development",
            "PYTHONUTF8": "1",
        }
    )
    command = [sys.executable, __file__, "--emit-profile", profile]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    return cast(dict[str, Any], json.loads(result.stdout.splitlines()[-1]))


def _emit_profile(expected: str) -> None:
    from app.main import app

    if app.state.api_profile.value != expected:
        raise SystemExit("profile settings were cached before snapshot generation")
    sys.stdout.write(json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True))


def _operation_map(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method.upper(), path): operation
        for path, path_item in spec.get("paths", {}).items()
        for method, operation in path_item.items()
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }


def _semantic_regressions(old: dict[str, Any], new: dict[str, Any], profile: str) -> list[str]:
    old_ops = _operation_map(old)
    new_ops = _operation_map(new)
    errors: list[str] = []
    if profile == "public":
        errors.extend(f"new public operation: {method} {path}" for method, path in new_ops.keys() - old_ops.keys())
    for key in old_ops.keys() & new_ops.keys():
        before, after = old_ops[key], new_ops[key]
        if before.get("security") and not after.get("security"):
            errors.append(f"authentication removed: {key[0]} {key[1]}")
        before_scopes = {
            scope for requirement in before.get("security", []) for scopes in requirement.values() for scope in scopes
        }
        after_scopes = {
            scope for requirement in after.get("security", []) for scopes in requirement.values() for scope in scopes
        }
        if not before_scopes.issubset(after_scopes):
            errors.append(f"scope reduced: {key[0]} {key[1]}")
        if before.get("x-janus-ownership") != "none" and after.get("x-janus-ownership") == "none":
            errors.append(f"ownership removed: {key[0]} {key[1]}")
    return errors


def _profile_move_regressions(
    old_specs: dict[str, dict[str, Any]], new_specs: dict[str, dict[str, Any]]
) -> list[str]:
    rank = {"public": 0, "user": 1, "control-plane": 2}
    old_locations = {
        operation: profile
        for profile, spec in old_specs.items()
        for operation in _operation_map(spec)
    }
    new_locations = {
        operation: profile
        for profile, spec in new_specs.items()
        for operation in _operation_map(spec)
    }
    return [
        f"operation moved {old_locations[operation]} -> {new_locations[operation]}: "
        f"{operation[0]} {operation[1]}"
        for operation in old_locations.keys() & new_locations.keys()
        if rank[new_locations[operation]] < rank[old_locations[operation]]
    ]


def _policy_matrix(specs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "method": method,
                "path": path,
                "operation_id": operation.get("operationId"),
                "profile": profile,
                "principals": operation.get("x-janus-principals", []),
                "scopes": operation.get("x-janus-scopes", []),
                "ownership": operation.get("x-janus-ownership"),
                "human_delegable": operation.get("x-janus-human-delegable", False),
            }
            for profile, spec in specs.items()
            for (method, path), operation in _operation_map(spec).items()
        ],
        key=lambda item: (item["profile"], item["path"], item["method"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-profile", choices=PROFILES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--archive-version")
    parser.add_argument("--compare-dir", type=Path)
    parser.add_argument("--git-ref")
    args = parser.parse_args()
    if args.emit_profile:
        _emit_profile(args.emit_profile)
        return 0

    rendered = {profile: _render_profile(profile) for profile in PROFILES}
    for spec in rendered.values():
        validate(spec)
    operation_sets = {profile: set(_operation_map(spec)) for profile, spec in rendered.items()}
    for left in PROFILES:
        for right in PROFILES:
            if left < right and operation_sets[left].intersection(operation_sets[right]):
                raise SystemExit(f"OpenAPI profiles overlap: {left} and {right}")

    canonical_matrix = json.loads(POLICY_MANIFEST.read_text(encoding="utf-8"))
    rendered_matrix = _policy_matrix(rendered)
    if rendered_matrix != canonical_matrix:
        raise SystemExit("generated OpenAPI policy matrix differs from canonical endpoint manifest")

    if args.check:
        stale = [
            profile
            for profile, spec in rendered.items()
            if not (CURRENT / f"{profile}.openapi.json").exists()
            or (CURRENT / f"{profile}.openapi.json").read_text(encoding="utf-8") != _canonical(spec)
        ]
        if stale:
            raise SystemExit("stale OpenAPI snapshots: " + ", ".join(stale))
        matrix_path = CURRENT / "endpoint-policy-matrix.json"
        if not matrix_path.exists() or matrix_path.read_text(encoding="utf-8") != _canonical(
            canonical_matrix
        ):
            raise SystemExit("stale endpoint policy matrix")
    else:
        CURRENT.mkdir(parents=True, exist_ok=True)
        for profile, spec in rendered.items():
            (CURRENT / f"{profile}.openapi.json").write_text(_canonical(spec), encoding="utf-8")
        (CURRENT / "endpoint-policy-matrix.json").write_text(
            _canonical(canonical_matrix), encoding="utf-8"
        )

    if args.compare_dir:
        compare_errors: list[str] = []
        compared_specs: dict[str, dict[str, Any]] = {}
        for profile, spec in rendered.items():
            old_path = args.compare_dir / f"{profile}.openapi.json"
            if old_path.exists():
                compared_specs[profile] = json.loads(old_path.read_text())
                compare_errors.extend(
                    _semantic_regressions(compared_specs[profile], spec, profile)
                )
        compare_errors.extend(_profile_move_regressions(compared_specs, rendered))
        if compare_errors:
            raise SystemExit(
                "security OpenAPI regression:\n" + "\n".join(sorted(compare_errors))
            )

    if args.git_ref:
        git_errors: list[str] = []
        git_specs: dict[str, dict[str, Any]] = {}
        with tempfile.TemporaryDirectory():
            for profile in PROFILES:
                source = f"documentation/openapi/current/{profile}.openapi.json"
                previous = subprocess.run(
                    ["git", "show", f"{args.git_ref}:{source}"],
                    cwd=ROOT,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                )
                if previous.returncode != 0:
                    continue
                old = json.loads(previous.stdout)
                git_specs[profile] = old
                git_errors.extend(_semantic_regressions(old, rendered[profile], profile))
        git_errors.extend(_profile_move_regressions(git_specs, rendered))
        if git_errors:
            raise SystemExit(
                "security OpenAPI regression:\n" + "\n".join(sorted(git_errors))
            )

    if args.archive_version:
        history = ROOT / "documentation" / "openapi" / "history" / args.archive_version
        history.mkdir(parents=True, exist_ok=True)
        for profile, spec in rendered.items():
            target = history / f"{profile}.openapi.json"
            content = _canonical(spec)
            if target.exists() and target.read_text(encoding="utf-8") != content:
                raise SystemExit(f"append-only history conflict: {target}")
            target.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
