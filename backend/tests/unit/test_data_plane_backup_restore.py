from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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
    assert len(manifest["steps"]) == 3
    assert manifest["steps"][0]["component"] == "postgres"


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
