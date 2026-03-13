from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if item.strip()]


@dataclass
class ShellRunner:
    def run(
        self,
        command: list[str],
        *,
        stdout_path: Path | None = None,
        input_path: Path | None = None,
    ) -> None:
        stdin = input_path.open("rb") if input_path else None
        stdout = stdout_path.open("wb") if stdout_path else subprocess.PIPE
        try:
            result = subprocess.run(
                command,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE,
                check=False,
            )
        finally:
            if stdin is not None:
                stdin.close()
            if stdout_path is not None and stdout not in (None, subprocess.PIPE):
                stdout.close()
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)} :: {stderr}")

    def capture_text(self, command: list[str]) -> str:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)} :: {stderr}")
        return (result.stdout or b"").decode("utf-8", errors="replace")


class DataPlaneBackupRestoreCLI:
    def __init__(self, args: argparse.Namespace, *, runner: ShellRunner | None = None) -> None:
        self.args = args
        self.runner = runner or ShellRunner()
        self.components = _split_csv(args.components) or ["postgres", "neo4j", "qdrant"]
        self.base_dir = _ensure_dir(Path(args.output_dir).resolve())
        self.run_id = getattr(args, "run_id", None) or _utc_stamp()
        self.run_dir = _ensure_dir(self.base_dir / self.run_id)
        self.manifest_path = self.run_dir / "manifest.json"
        self.manifest: dict[str, Any] = {
            "run_id": self.run_id,
            "mode": args.command,
            "created_at": datetime.now(UTC).isoformat(),
            "dry_run": bool(args.dry_run),
            "target_host": args.target_host,
            "source": self._build_source_descriptor(),
            "components": self.components,
            "versions": {},
            "artifacts": [],
            "checks": {},
            "steps": [],
        }

    def execute(self) -> dict[str, Any]:
        operation = getattr(self, f"_run_{self.args.command}")
        operation()
        self.manifest["versions"] = self._capture_versions()
        _json_dump(self.manifest_path, self.manifest)
        return self.manifest

    def _build_source_descriptor(self) -> dict[str, Any]:
        return {
            "target_host": self.args.target_host,
            "target_user": self.args.target_user,
            "postgres": {
                "dsn_provided": bool(self.args.postgres_dsn),
                "verify_dsn_provided": bool(self.args.postgres_verify_dsn),
                "container": self.args.postgres_container,
                "database": self.args.postgres_db,
                "user": self.args.postgres_user,
            },
            "neo4j": {
                "uri": self.args.neo4j_uri,
                "container": self.args.neo4j_container,
                "restore_container": self.args.neo4j_restore_container,
                "user": self.args.neo4j_user,
            },
            "qdrant": {
                "url": self.args.qdrant_url,
                "collections": _split_csv(self.args.qdrant_collections),
            },
        }

    def _capture_versions(self) -> dict[str, Any]:
        if self.args.dry_run:
            return {component: {"status": "skipped", "reason": "dry-run"} for component in self.components}

        versions: dict[str, Any] = {}
        if "postgres" in self.components:
            versions["postgres"] = self._detect_postgres_version()
        if "neo4j" in self.components:
            versions["neo4j"] = self._detect_neo4j_version()
        if "qdrant" in self.components:
            versions["qdrant"] = self._detect_qdrant_version()
        return versions

    def _detect_postgres_version(self) -> dict[str, Any]:
        query = text("SELECT version()")
        dsn = self.args.postgres_verify_dsn or self.args.postgres_dsn
        if dsn:
            engine = create_engine(dsn)
            try:
                with engine.connect() as connection:
                    version = connection.execute(query).scalar_one()
            finally:
                engine.dispose()
            return {"status": "ok", "version": str(version)}

        if not self.args.postgres_container:
            return {"status": "skipped", "reason": "missing-postgres-source"}

        command = self._docker_exec_command(
            self.args.postgres_container,
            f"psql -U {shlex.quote(self.args.postgres_user)} -d {shlex.quote(self.args.postgres_db)} -tAc 'SELECT version()'",
        )
        version = self.runner.capture_text(command).strip()
        return {"status": "ok", "version": version}

    def _detect_neo4j_version(self) -> dict[str, Any]:
        if not (self.args.neo4j_uri and self.args.neo4j_user and self.args.neo4j_password):
            return {"status": "skipped", "reason": "missing-neo4j-credentials"}
        driver = GraphDatabase.driver(
            self.args.neo4j_uri,
            auth=(self.args.neo4j_user, self.args.neo4j_password),
        )
        try:
            with driver.session() as session:
                record = session.run(
                    "CALL dbms.components() YIELD name, versions RETURN name, versions[0] AS version LIMIT 1"
                ).single()
        finally:
            driver.close()
        return {"status": "ok", "component": record["name"], "version": record["version"]}

    def _detect_qdrant_version(self) -> dict[str, Any]:
        if not self.args.qdrant_url:
            return {"status": "skipped", "reason": "missing-qdrant-url"}
        response = requests.get(
            f"{self._qdrant_base_url()}/",
            headers=self._qdrant_headers(),
            timeout=30,
            verify=not self.args.insecure,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "status": "ok",
            "title": payload.get("title"),
            "version": payload.get("version"),
            "commit": payload.get("commit"),
        }

    def _record_step(self, component: str, action: str, detail: dict[str, Any]) -> None:
        self.manifest["steps"].append({"component": component, "action": action, **detail})

    def _record_artifact(self, component: str, path: Path, extra: dict[str, Any] | None = None) -> None:
        payload = {
            "component": component,
            "path": str(path),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "sha256": _sha256_file(path) if path.exists() else None,
        }
        if extra:
            payload.update(extra)
        self.manifest["artifacts"].append(payload)

    def _run_backup(self) -> None:
        if "postgres" in self.components:
            self._backup_postgres()
        if "neo4j" in self.components:
            self._backup_neo4j()
        if "qdrant" in self.components:
            self._backup_qdrant()

    def _run_restore(self) -> None:
        if "postgres" in self.components:
            self._restore_postgres()
        if "neo4j" in self.components:
            self._restore_neo4j()
        if "qdrant" in self.components:
            self._restore_qdrant()

    def _run_verify(self) -> None:
        checks: dict[str, Any] = {}
        if "postgres" in self.components:
            checks["postgres"] = self._verify_postgres()
        if "neo4j" in self.components:
            checks["neo4j"] = self._verify_neo4j()
        if "qdrant" in self.components:
            checks["qdrant"] = self._verify_qdrant()
        self.manifest["checks"] = checks

    def _command_prefix(self) -> list[str]:
        if self.args.target_host:
            target = self.args.target_host
            if self.args.target_user:
                target = f"{self.args.target_user}@{target}"
            return ["ssh", target]
        return []

    def _docker_exec_command(self, container: str, command: str) -> list[str]:
        prefix = self._command_prefix()
        if prefix:
            return [*prefix, f"docker exec -i {shlex.quote(container)} sh -lc {shlex.quote(command)}"]
        return ["docker", "exec", "-i", container, "sh", "-lc", command]

    def _backup_postgres(self) -> None:
        artifact = self.run_dir / "postgres.dump"
        if self.args.dry_run:
            self._record_step(
                "postgres",
                "backup",
                {"artifact": str(artifact), "mode": "dry-run", "dsn": bool(self.args.postgres_dsn)},
            )
            return
        if self.args.postgres_dsn:
            command = ["pg_dump", "--format=custom", f"--dbname={self.args.postgres_dsn}"]
            self.runner.run(command, stdout_path=artifact)
        else:
            if not self.args.postgres_container:
                raise ValueError("postgres_container is required when postgres_dsn is not provided.")
            remote_cmd = (
                "pg_dump --format=custom "
                f"--username={shlex.quote(self.args.postgres_user)} "
                f"--dbname={shlex.quote(self.args.postgres_db)}"
            )
            command = self._docker_exec_command(self.args.postgres_container, remote_cmd)
            self.runner.run(command, stdout_path=artifact)
        self._record_artifact("postgres", artifact)

    def _restore_postgres(self) -> None:
        artifact = self._resolve_restore_artifact("postgres", ".dump")
        if self.args.dry_run:
            self._record_step("postgres", "restore", {"artifact": str(artifact), "mode": "dry-run"})
            return
        if not self.args.postgres_restore_dsn:
            raise ValueError("postgres_restore_dsn is required for restore.")
        command = [
            "pg_restore",
            "--clean",
            "--if-exists",
            f"--dbname={self.args.postgres_restore_dsn}",
            str(artifact),
        ]
        self.runner.run(command)
        self._record_step("postgres", "restore", {"artifact": str(artifact), "status": "completed"})

    def _verify_postgres(self) -> dict[str, Any]:
        if self.args.dry_run:
            return {"status": "skipped", "reason": "dry-run"}
        if not self.args.postgres_verify_dsn:
            return {"status": "skipped", "reason": "missing-postgres-verify-dsn"}
        engine = create_engine(self.args.postgres_verify_dsn)
        try:
            with engine.connect() as connection:
                value = connection.execute(
                    text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
                ).scalar_one()
        finally:
            engine.dispose()
        return {"status": "ok", "public_table_count": int(value or 0)}

    def _backup_neo4j(self) -> None:
        artifact = self.run_dir / "neo4j.dump"
        if self.args.dry_run:
            self._record_step(
                "neo4j",
                "backup",
                {"artifact": str(artifact), "mode": "dry-run", "container": self.args.neo4j_container},
            )
            return
        if not self.args.neo4j_container:
            raise ValueError("neo4j_container is required for backup.")
        remote_cmd = (
            "rm -f /tmp/neo4j.dump && "
            "neo4j-admin database dump neo4j --overwrite-destination=true --to-path=/tmp >/dev/null && "
            "cat /tmp/neo4j.dump"
        )
        command = self._docker_exec_command(self.args.neo4j_container, remote_cmd)
        self.runner.run(command, stdout_path=artifact)
        self._record_artifact("neo4j", artifact)

    def _restore_neo4j(self) -> None:
        artifact = self._resolve_restore_artifact("neo4j", ".dump")
        if self.args.dry_run:
            self._record_step("neo4j", "restore", {"artifact": str(artifact), "mode": "dry-run"})
            return
        if not self.args.neo4j_restore_container:
            raise ValueError("neo4j_restore_container is required for restore.")
        remote_cmd = (
            "cat > /tmp/neo4j.dump && "
            "neo4j-admin database load neo4j --overwrite-destination=true --from-path=/tmp >/dev/null"
        )
        command = self._docker_exec_command(self.args.neo4j_restore_container, remote_cmd)
        self.runner.run(command, input_path=artifact)
        self._record_step("neo4j", "restore", {"artifact": str(artifact), "status": "completed"})

    def _verify_neo4j(self) -> dict[str, Any]:
        if self.args.dry_run:
            return {"status": "skipped", "reason": "dry-run"}
        if not (self.args.neo4j_uri and self.args.neo4j_user and self.args.neo4j_password):
            return {"status": "skipped", "reason": "missing-neo4j-credentials"}
        driver = GraphDatabase.driver(
            self.args.neo4j_uri,
            auth=(self.args.neo4j_user, self.args.neo4j_password),
        )
        try:
            with driver.session() as session:
                node_count = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) AS total").single()["total"]
        finally:
            driver.close()
        return {
            "status": "ok",
            "node_count": int(node_count or 0),
            "relationship_count": int(rel_count or 0),
        }

    def _qdrant_headers(self) -> dict[str, str]:
        headers = {}
        if self.args.qdrant_api_key:
            headers["api-key"] = self.args.qdrant_api_key
        return headers

    def _qdrant_base_url(self) -> str:
        base = str(self.args.qdrant_url or "").strip().rstrip("/")
        if not base:
            raise ValueError("qdrant_url is required.")
        return base

    def _list_qdrant_collections(self) -> list[str]:
        response = requests.get(
            f"{self._qdrant_base_url()}/collections",
            headers=self._qdrant_headers(),
            timeout=30,
            verify=not self.args.insecure,
        )
        response.raise_for_status()
        payload = response.json()
        return [item["name"] for item in payload.get("result", {}).get("collections", [])]

    def _backup_qdrant(self) -> None:
        configured = _split_csv(self.args.qdrant_collections)
        collections = configured or ([] if self.args.dry_run else self._list_qdrant_collections())
        if self.args.dry_run:
            self._record_step(
                "qdrant",
                "backup",
                {
                    "collections": collections or ["<discover-at-runtime>"],
                    "mode": "dry-run",
                    "base_url": self._qdrant_base_url(),
                },
            )
            return
        for collection in collections:
            create_resp = requests.post(
                f"{self._qdrant_base_url()}/collections/{collection}/snapshots",
                headers=self._qdrant_headers(),
                timeout=60,
                verify=not self.args.insecure,
            )
            create_resp.raise_for_status()
            snapshot_name = create_resp.json().get("result", {}).get("name")
            if not snapshot_name:
                raise RuntimeError(f"Qdrant snapshot name missing for collection {collection}")
            download_resp = requests.get(
                f"{self._qdrant_base_url()}/collections/{collection}/snapshots/{snapshot_name}",
                headers=self._qdrant_headers(),
                timeout=300,
                verify=not self.args.insecure,
            )
            download_resp.raise_for_status()
            artifact = self.run_dir / f"qdrant-{collection}-{snapshot_name}"
            artifact.write_bytes(download_resp.content)
            self._record_artifact("qdrant", artifact, {"collection": collection})

    def _restore_qdrant(self) -> None:
        artifacts = sorted(self.run_dir.glob("qdrant-*"))
        if self.args.restore_dir:
            artifacts = sorted(Path(self.args.restore_dir).resolve().glob("qdrant-*"))
        if self.args.dry_run:
            self._record_step(
                "qdrant",
                "restore",
                {"artifacts": [str(path) for path in artifacts], "mode": "dry-run"},
            )
            return
        for artifact in artifacts:
            collection = artifact.name.split("-")[1]
            with artifact.open("rb") as fh:
                response = requests.post(
                    f"{self._qdrant_base_url()}/collections/{collection}/snapshots/upload",
                    headers=self._qdrant_headers(),
                    files={"snapshot": (artifact.name, fh, "application/octet-stream")},
                    timeout=300,
                    verify=not self.args.insecure,
                )
            response.raise_for_status()
            self._record_step("qdrant", "restore", {"artifact": str(artifact), "collection": collection, "status": "completed"})

    def _verify_qdrant(self) -> dict[str, Any]:
        if self.args.dry_run:
            return {"status": "skipped", "reason": "dry-run"}
        collections = self._list_qdrant_collections()
        details: dict[str, Any] = {}
        for collection in collections:
            response = requests.get(
                f"{self._qdrant_base_url()}/collections/{collection}",
                headers=self._qdrant_headers(),
                timeout=60,
                verify=not self.args.insecure,
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            details[collection] = {
                "points_count": int(result.get("points_count", 0) or 0),
                "indexed_vectors_count": int(result.get("indexed_vectors_count", 0) or 0),
            }
        return {"status": "ok", "collections": details}

    def _resolve_restore_artifact(self, component: str, suffix: str) -> Path:
        search_dir = Path(self.args.restore_dir).resolve() if self.args.restore_dir else self.run_dir
        if component == "qdrant":
            raise ValueError("Qdrant restore resolves multiple artifacts.")
        candidates = sorted(search_dir.glob(f"{component}*{suffix}"))
        if not candidates:
            raise FileNotFoundError(f"No restore artifact found for {component} in {search_dir}")
        return candidates[0]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup/restore/verify for Postgres, Neo4j and Qdrant.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument("--output-dir", default="outputs/qa/data-plane-backups")
    common_parent.add_argument("--restore-dir", default=None)
    common_parent.add_argument("--run-id", default=None)
    common_parent.add_argument("--components", default="postgres,neo4j,qdrant")
    common_parent.add_argument("--dry-run", action="store_true")
    common_parent.add_argument("--target-host", default=None)
    common_parent.add_argument("--target-user", default=None)
    common_parent.add_argument("--insecure", action="store_true")

    common_parent.add_argument("--postgres-dsn", default=None)
    common_parent.add_argument("--postgres-user", default=os.getenv("POSTGRES_USER", "janus"))
    common_parent.add_argument("--postgres-db", default=os.getenv("POSTGRES_DB", "janus_db"))
    common_parent.add_argument("--postgres-container", default="janus_postgres")
    common_parent.add_argument("--postgres-restore-dsn", default=None)
    common_parent.add_argument("--postgres-verify-dsn", default=None)

    common_parent.add_argument("--neo4j-container", default="janus_neo4j")
    common_parent.add_argument("--neo4j-restore-container", default="janus_neo4j_restore")
    common_parent.add_argument("--neo4j-uri", default=None)
    common_parent.add_argument("--neo4j-user", default=None)
    common_parent.add_argument("--neo4j-password", default=None)

    common_parent.add_argument("--qdrant-url", default=None)
    common_parent.add_argument("--qdrant-api-key", default=None)
    common_parent.add_argument("--qdrant-collections", default=None)

    for name in ("backup", "restore", "verify"):
        subparsers.add_parser(name, parents=[common_parent])

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = DataPlaneBackupRestoreCLI(args).execute()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
