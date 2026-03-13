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
