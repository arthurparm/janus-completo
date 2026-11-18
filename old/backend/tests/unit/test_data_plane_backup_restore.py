from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module():
    script_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "data_plane_backup_restore.py"
    )
    spec = importlib.util.spec_from_file_location("data_plane_backup_restore", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_backup_dry_run_writes_manifest(tmp_path):
    module = _load_module()
    parser = module.build_parser()

    args = parser.parse_args(
        [
            "backup",
            "--dry-run",
            "--output-dir",
            str(tmp_path),
            "--qdrant-url",
            "http://127.0.0.1:6333",
            "--components",
            "postgres,neo4j,qdrant",
        ]
    )

    manifest = module.DataPlaneBackupRestoreCLI(args).execute()

    assert manifest["mode"] == "backup"
    assert manifest["dry_run"] is True
    assert len(manifest["steps"]) == 3
    assert manifest["artifacts"] == []
    assert manifest["source"]["qdrant"]["url"] == "http://127.0.0.1:6333"
    assert manifest["versions"]["postgres"]["reason"] == "dry-run"
    assert (Path(tmp_path) / manifest["run_id"] / "manifest.json").exists()


def test_restore_dry_run_uses_restore_dir(tmp_path):
    module = _load_module()
    restore_dir = tmp_path / "restore"
    restore_dir.mkdir()
    (restore_dir / "postgres.dump").write_bytes(b"dummy")
    (restore_dir / "neo4j.dump").write_bytes(b"dummy")
    (restore_dir / "qdrant-janus_episodic_memory-snapshot").write_bytes(b"dummy")

    parser = module.build_parser()
    args = parser.parse_args(
        [
            "restore",
            "--dry-run",
            "--output-dir",
            str(tmp_path / "output"),
            "--restore-dir",
            str(restore_dir),
            "--qdrant-url",
            "http://127.0.0.1:6333",
        ]
    )

    manifest = module.DataPlaneBackupRestoreCLI(args).execute()

    assert manifest["mode"] == "restore"
    restore_steps = [step for step in manifest["steps"] if step["action"] == "restore"]
    integrity_steps = [step for step in manifest["steps"] if step["action"] == "integrity-check"]
    assert len(restore_steps) == 3
    assert len(integrity_steps) == 3
    assert restore_steps[0]["component"] == "postgres"
    assert integrity_steps[0]["status"] == "skipped"


def test_verify_manifest_records_detected_versions(tmp_path, monkeypatch):
    module = _load_module()
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "verify",
            "--output-dir",
            str(tmp_path),
            "--components",
            "postgres,neo4j,qdrant",
            "--postgres-verify-dsn",
            "postgresql+psycopg2://user:pass@localhost/db",
            "--neo4j-uri",
            "bolt://localhost:7687",
            "--neo4j-user",
            "neo4j",
            "--neo4j-password",
            "secret",
            "--qdrant-url",
            "http://127.0.0.1:6333",
        ]
    )

    cli = module.DataPlaneBackupRestoreCLI(args)
    monkeypatch.setattr(
        cli,
        "_verify_postgres",
        lambda: {"status": "ok", "public_table_count": 40},
    )
    monkeypatch.setattr(
        cli,
        "_verify_neo4j",
        lambda: {"status": "ok", "node_count": 10, "relationship_count": 20},
    )
    monkeypatch.setattr(
        cli,
        "_verify_qdrant",
        lambda: {"status": "ok", "collections": {"janus_episodic_memory": {"points_count": 359}}},
    )
    monkeypatch.setattr(
        cli,
        "_capture_versions",
        lambda: {
            "postgres": {"status": "ok", "version": "PostgreSQL 16.4"},
            "neo4j": {"status": "ok", "component": "Neo4j Kernel", "version": "5.26.0"},
            "qdrant": {"status": "ok", "version": "1.16.2", "commit": "abc123"},
        },
    )

    manifest = cli.execute()

    assert manifest["checks"]["postgres"]["public_table_count"] == 40
    assert manifest["versions"]["postgres"]["version"] == "PostgreSQL 16.4"
    assert manifest["versions"]["neo4j"]["version"] == "5.26.0"
    assert manifest["versions"]["qdrant"]["version"] == "1.16.2"


def test_qdrant_verify_uses_ca_cert_path(tmp_path):
    module = _load_module()
    ca_cert = tmp_path / "ca.pem"
    ca_cert.write_text("dummy", encoding="utf-8")
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "verify",
            "--output-dir",
            str(tmp_path / "out"),
            "--components",
            "qdrant",
            "--qdrant-url",
            "https://localhost:6333",
            "--qdrant-ca-cert",
            str(ca_cert),
        ]
    )

    cli = module.DataPlaneBackupRestoreCLI(args)

    assert cli._qdrant_verify() == str(ca_cert.resolve())
    assert cli.manifest["source"]["qdrant"]["ca_cert_provided"] is True


def test_qdrant_insecure_overrides_ca_cert(tmp_path):
    module = _load_module()
    ca_cert = tmp_path / "ca.pem"
    ca_cert.write_text("dummy", encoding="utf-8")
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "verify",
            "--output-dir",
            str(tmp_path / "out"),
            "--components",
            "qdrant",
            "--qdrant-url",
            "https://localhost:6333",
            "--qdrant-ca-cert",
            str(ca_cert),
            "--insecure",
        ]
    )

    cli = module.DataPlaneBackupRestoreCLI(args)

    assert cli._qdrant_verify() is False


def test_resolve_qdrant_artifact_collection_prefers_manifest(tmp_path):
    module = _load_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    artifact = run_dir / "qdrant-collection-with-hyphen-snapshot-20260713.snapshot"
    artifact.write_bytes(b"dummy")
    (run_dir / "manifest.json").write_text(
        '{"artifacts":[{"component":"qdrant","path":"'
        + str(artifact).replace("\\", "\\\\")
        + '","collection":"collection-with-hyphen"}]}',
        encoding="utf-8",
    )
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "restore",
            "--output-dir",
            str(tmp_path / "out"),
            "--restore-dir",
            str(run_dir),
            "--components",
            "qdrant",
            "--qdrant-url",
            "https://localhost:6333",
        ]
    )

    cli = module.DataPlaneBackupRestoreCLI(args)

    assert cli._resolve_qdrant_artifact_collection(artifact) == "collection-with-hyphen"


def test_restore_integrity_check_accepts_matching_sha256(tmp_path):
    module = _load_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    artifact = run_dir / "qdrant-janus_episodic_memory-snapshot"
    artifact.write_bytes(b"snapshot-bytes")
    sha256 = module._sha256_file(artifact)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "component": "qdrant",
                        "path": str(artifact),
                        "collection": "janus_episodic_memory",
                        "sha256": sha256,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "restore",
            "--output-dir",
            str(tmp_path / "out"),
            "--restore-dir",
            str(run_dir),
            "--components",
            "qdrant",
            "--qdrant-url",
            "https://localhost:6333",
            "--dry-run",
        ]
    )

    manifest = module.DataPlaneBackupRestoreCLI(args).execute()

    integrity_steps = [step for step in manifest["steps"] if step["action"] == "integrity-check"]
    assert len(integrity_steps) == 1
    assert integrity_steps[0]["status"] == "ok"
    assert integrity_steps[0]["sha256"] == sha256


def test_restore_integrity_check_rejects_mismatched_sha256(tmp_path):
    module = _load_module()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    artifact = run_dir / "qdrant-janus_episodic_memory-snapshot"
    artifact.write_bytes(b"snapshot-bytes")
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "component": "qdrant",
                        "path": str(artifact),
                        "collection": "janus_episodic_memory",
                        "sha256": "0" * 64,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "restore",
            "--output-dir",
            str(tmp_path / "out"),
            "--restore-dir",
            str(run_dir),
            "--components",
            "qdrant",
            "--qdrant-url",
            "https://localhost:6333",
            "--dry-run",
        ]
    )

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        module.DataPlaneBackupRestoreCLI(args).execute()


def _write_run_manifest(base: Path, run_id: str, created_at: str) -> Path:
    run_dir = base / run_id
    run_dir.mkdir()
    (run_dir / "manifest.json").write_text(
        json.dumps({"run_id": run_id, "created_at": created_at, "mode": "backup"}),
        encoding="utf-8",
    )
    return run_dir


def test_prune_dry_run_reports_candidates_without_deleting(tmp_path):
    module = _load_module()
    _write_run_manifest(tmp_path, "new", "2026-07-13T12:00:00+00:00")
    old_run = _write_run_manifest(tmp_path, "old", "2026-06-01T12:00:00+00:00")
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "prune",
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "prune-report",
            "--retention-days",
            "7",
            "--retain-last",
            "1",
        ]
    )

    manifest = module.DataPlaneBackupRestoreCLI(args).execute()

    assert old_run.exists()
    assert manifest["checks"]["prune"]["mode"] == "dry-run"
    assert manifest["checks"]["prune"]["candidate_count"] == 1
    assert manifest["steps"][0]["status"] == "would-delete"


def test_prune_apply_deletes_only_candidates(tmp_path):
    module = _load_module()
    kept = _write_run_manifest(tmp_path, "new", "2026-07-13T12:00:00+00:00")
    old_run = _write_run_manifest(tmp_path, "old", "2026-06-01T12:00:00+00:00")
    parser = module.build_parser()
    args = parser.parse_args(
        [
            "prune",
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "prune-apply-report",
            "--retention-days",
            "7",
            "--retain-last",
            "1",
            "--prune-apply",
        ]
    )

    manifest = module.DataPlaneBackupRestoreCLI(args).execute()

    assert kept.exists()
    assert not old_run.exists()
    assert manifest["checks"]["prune"]["mode"] == "apply"
    assert manifest["steps"][0]["status"] == "deleted"
