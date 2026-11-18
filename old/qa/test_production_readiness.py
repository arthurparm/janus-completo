from __future__ import annotations

import json

from tooling.production_readiness import validate_baseline, validate_env_files


def test_validate_baseline_accepts_repo_baseline():
    baseline = json.loads(
        open(
            "documentation/operations/production-readiness.baseline.json",
            encoding="utf-8",
        ).read()
    )

    assert validate_baseline(baseline) == []


def test_validate_env_files_rejects_placeholders_from_examples(tmp_path):
    baseline = {
        "baseline_id": "test",
        "topology": {"hosts": [{"name": "pc1", "role": "api", "rollout_wave": 1, "validations": ["oidc"]}]},
        "critical_secrets": [
            {
                "name": "ADMIN_FACADE_CLIENT_SECRET",
                "source": "secret-manager",
                "owner": "platform",
                "rotation": "90d",
                "hosts": ["pc1"],
                "evidence": "present",
            }
        ],
        "identity_gate": {
            "real_idp_required": True,
            "federation_required": True,
            "per_host_validation_required": True,
            "required_env": ["OIDC_ISSUER", "OIDC_SERVICE_TOKEN_URL", "OIDC_ADMIN_GROUP"],
        },
        "release_gate": {
            "blockers": ["identity"],
            "sequence": [{"order": 1, "id": "review", "description": "review", "evidence": "checklist"}],
        },
        "evidence_bundle": ["outputs/qa/production_readiness_report.md"],
    }
    env_file = tmp_path / "example.env"
    env_file.write_text(
        "\n".join(
            [
                "OIDC_ISSUER=https://idp.example.invalid",
                "OIDC_SERVICE_TOKEN_URL=https://localhost/token",
                "OIDC_ADMIN_GROUP=janus-administrators",
                "ADMIN_FACADE_CLIENT_SECRET=__REQUIRED__",
            ]
        ),
        encoding="utf-8",
    )

    errors = validate_env_files(baseline, [env_file])

    assert any("placeholder" in error for error in errors)
    assert any("localhost" in error for error in errors)
