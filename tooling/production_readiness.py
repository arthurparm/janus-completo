#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_PATH = REPO_ROOT / "documentation" / "operations" / "production-readiness.baseline.json"
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
PLACEHOLDER_MARKERS = ("__required__", ".invalid", "change_me", "changeme")
IDENTITY_URL_KEYS = (
    "OIDC_ISSUER",
    "OIDC_JWKS_URL",
    "OIDC_AUTHORIZATION_ENDPOINT",
    "OIDC_SERVICE_ISSUER",
    "OIDC_SERVICE_JWKS_URL",
    "OIDC_SERVICE_TOKEN_URL",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object at the root")
    return payload


def _parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _hostname(value: str) -> str:
    parsed = urlparse(str(value).strip())
    return (parsed.hostname or "").strip().lower()


def _looks_placeholder(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def validate_baseline(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not str(payload.get("baseline_id", "")).strip():
        errors.append("baseline_id is required")

    topology = payload.get("topology")
    if not isinstance(topology, dict):
        errors.append("topology must be an object")
        return errors

    hosts = topology.get("hosts")
    if not isinstance(hosts, list) or not hosts:
        errors.append("topology.hosts must be a non-empty list")
    else:
        seen_host_names: set[str] = set()
        for index, host in enumerate(hosts, start=1):
            if not isinstance(host, dict):
                errors.append(f"topology.hosts[{index}] must be an object")
                continue
            name = str(host.get("name", "")).strip()
            role = str(host.get("role", "")).strip()
            wave = host.get("rollout_wave")
            validations = host.get("validations")
            if not name:
                errors.append(f"topology.hosts[{index}].name is required")
            elif name in seen_host_names:
                errors.append(f"duplicate host name: {name}")
            else:
                seen_host_names.add(name)
            if not role:
                errors.append(f"topology.hosts[{index}].role is required")
            if not isinstance(wave, int) or wave < 1:
                errors.append(f"topology.hosts[{index}].rollout_wave must be an integer >= 1")
            if not isinstance(validations, list) or not validations:
                errors.append(f"topology.hosts[{index}].validations must be a non-empty list")

    secrets = payload.get("critical_secrets")
    if not isinstance(secrets, list) or not secrets:
        errors.append("critical_secrets must be a non-empty list")
    else:
        secret_names: set[str] = set()
        for index, secret in enumerate(secrets, start=1):
            if not isinstance(secret, dict):
                errors.append(f"critical_secrets[{index}] must be an object")
                continue
            name = str(secret.get("name", "")).strip()
            if not name:
                errors.append(f"critical_secrets[{index}].name is required")
            elif name in secret_names:
                errors.append(f"duplicate critical secret: {name}")
            else:
                secret_names.add(name)
            for field_name in ("source", "owner", "rotation", "evidence"):
                if not str(secret.get(field_name, "")).strip():
                    errors.append(f"critical_secrets[{index}].{field_name} is required")
            hosts_for_secret = secret.get("hosts")
            if not isinstance(hosts_for_secret, list) or not hosts_for_secret:
                errors.append(f"critical_secrets[{index}].hosts must be a non-empty list")

    identity_gate = payload.get("identity_gate")
    if not isinstance(identity_gate, dict):
        errors.append("identity_gate must be an object")
    else:
        for field_name in ("real_idp_required", "federation_required", "per_host_validation_required"):
            if identity_gate.get(field_name) is not True:
                errors.append(f"identity_gate.{field_name} must be true")
        required_env = identity_gate.get("required_env")
        if not isinstance(required_env, list) or not required_env:
            errors.append("identity_gate.required_env must be a non-empty list")

    release_gate = payload.get("release_gate")
    if not isinstance(release_gate, dict):
        errors.append("release_gate must be an object")
    else:
        blockers = release_gate.get("blockers")
        if not isinstance(blockers, list) or not blockers:
            errors.append("release_gate.blockers must be a non-empty list")
        sequence = release_gate.get("sequence")
        if not isinstance(sequence, list) or not sequence:
            errors.append("release_gate.sequence must be a non-empty list")
        else:
            expected_order = 1
            ids_seen: set[str] = set()
            for index, step in enumerate(sequence, start=1):
                if not isinstance(step, dict):
                    errors.append(f"release_gate.sequence[{index}] must be an object")
                    continue
                step_id = str(step.get("id", "")).strip()
                description = str(step.get("description", "")).strip()
                evidence = str(step.get("evidence", "")).strip()
                order = step.get("order")
                if not step_id:
                    errors.append(f"release_gate.sequence[{index}].id is required")
                elif step_id in ids_seen:
                    errors.append(f"duplicate release step id: {step_id}")
                else:
                    ids_seen.add(step_id)
                if not description:
                    errors.append(f"release_gate.sequence[{index}].description is required")
                if not evidence:
                    errors.append(f"release_gate.sequence[{index}].evidence is required")
                if order != expected_order:
                    errors.append(
                        f"release_gate.sequence[{index}].order must be {expected_order}, got {order!r}"
                    )
                expected_order += 1

    evidence_bundle = payload.get("evidence_bundle")
    if not isinstance(evidence_bundle, list) or not evidence_bundle:
        errors.append("evidence_bundle must be a non-empty list")

    return errors


def validate_env_files(payload: dict[str, Any], env_files: list[Path]) -> list[str]:
    errors: list[str] = []
    required_env = [
        str(item).strip()
        for item in (payload.get("identity_gate", {}).get("required_env") or [])
        if str(item).strip()
    ]
    critical_secret_names = {
        str(item.get("name", "")).strip()
        for item in (payload.get("critical_secrets") or [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }

    for env_file in env_files:
        data = _parse_env_file(env_file)
        for key in required_env:
            if not data.get(key, "").strip():
                errors.append(f"{env_file.name}: missing required identity key {key}")
        for key in critical_secret_names:
            value = data.get(key, "").strip()
            if not value:
                errors.append(f"{env_file.name}: missing critical secret {key}")
            elif _looks_placeholder(value):
                errors.append(f"{env_file.name}: {key} still uses placeholder or empty value")

        for key in IDENTITY_URL_KEYS:
            value = data.get(key, "").strip()
            if not value:
                continue
            if not value.lower().startswith("https://"):
                errors.append(f"{env_file.name}: {key} must use HTTPS")
                continue
            host = _hostname(value)
            if host in BLOCKED_HOSTS:
                errors.append(f"{env_file.name}: {key} must not target local host {host}")
            if ".invalid" in host:
                errors.append(f"{env_file.name}: {key} must not use placeholder host {host}")

    return errors


def build_report(payload: dict[str, Any], errors: list[str], env_files: list[Path]) -> dict[str, Any]:
    return {
        "status": "ok" if not errors else "failed",
        "baseline_id": payload.get("baseline_id", ""),
        "validated_env_files": [str(path) for path in env_files],
        "host_count": len(payload.get("topology", {}).get("hosts") or []),
        "critical_secret_count": len(payload.get("critical_secrets") or []),
        "release_step_count": len(payload.get("release_gate", {}).get("sequence") or []),
        "errors": errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Production Readiness Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Baseline: `{report['baseline_id']}`",
        f"- Hosts: `{report['host_count']}`",
        f"- Critical secrets: `{report['critical_secret_count']}`",
        f"- Release steps: `{report['release_step_count']}`",
    ]
    env_files = report.get("validated_env_files") or []
    if env_files:
        lines.append(f"- Env files: `{', '.join(env_files)}`")
    if report["errors"]:
        lines.extend(["", "## Errors"])
        for error in report["errors"]:
            lines.append(f"- {error}")
    else:
        lines.extend(
            [
                "",
                "## Checks",
                "- Baseline schema is internally consistent.",
                "- Identity gate, critical secrets and release sequence are present.",
                "- Optional env files passed the local placeholder/HTTPS validation gate.",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the repository production-readiness baseline and optional env files."
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE_PATH),
        help="Path to the production-readiness baseline JSON file.",
    )
    parser.add_argument(
        "--env-file",
        dest="env_files",
        action="append",
        default=[],
        help="Optional env file to validate against the identity/secret gate. Can be used multiple times.",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--out", default="", help="Optional output file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline_path = Path(args.baseline)
    payload = _load_json(baseline_path)
    env_files = [Path(path) for path in args.env_files]
    errors = validate_baseline(payload)
    if env_files:
        errors.extend(validate_env_files(payload, env_files))
    report = build_report(payload, errors, env_files)
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.format == "markdown":
        content = render_markdown(report)
    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(str(output_path))
    else:
        print(content, end="")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
