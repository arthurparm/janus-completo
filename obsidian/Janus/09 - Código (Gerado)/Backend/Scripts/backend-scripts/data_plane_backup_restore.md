---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "backend/scripts/data_plane_backup_restore.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# data_plane_backup_restore

## Arquivos-fonte
- `backend/scripts/data_plane_backup_restore.py`

## Símbolos
- function: `_utc_stamp()` -> `str`
- function: `_ensure_dir(path: Path)` -> `Path`
- function: `_sha256_file(path: Path)` -> `str`
- function: `_json_dump(path: Path, payload: dict[str, Any])` -> `None`
- function: `_split_csv(raw: str | None)` -> `list[str]`
- class: `ShellRunner`
- method: `ShellRunner.run(self, command: list[str], *, stdout_path: Path | None = None, input_path: Path | None = None)` -> `None`
- method: `ShellRunner.capture_text(self, command: list[str])` -> `str`
- class: `DataPlaneBackupRestoreCLI`
- method: `DataPlaneBackupRestoreCLI.__init__(self, args: argparse.Namespace, *, runner: ShellRunner | None = None)` -> `None`
- method: `DataPlaneBackupRestoreCLI.execute(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._build_source_descriptor(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._capture_versions(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._detect_postgres_version(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._detect_neo4j_version(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._detect_qdrant_version(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._record_step(self, component: str, action: str, detail: dict[str, Any])` -> `None`
- method: `DataPlaneBackupRestoreCLI._record_artifact(self, component: str, path: Path, extra: dict[str, Any] | None = None)` -> `None`
- method: `DataPlaneBackupRestoreCLI._run_backup(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._run_restore(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._run_verify(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._command_prefix(self)` -> `list[str]`
- method: `DataPlaneBackupRestoreCLI._docker_exec_command(self, container: str, command: str)` -> `list[str]`
- method: `DataPlaneBackupRestoreCLI._backup_postgres(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._restore_postgres(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._verify_postgres(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._backup_neo4j(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._restore_neo4j(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._verify_neo4j(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._qdrant_headers(self)` -> `dict[str, str]`
- method: `DataPlaneBackupRestoreCLI._qdrant_base_url(self)` -> `str`
- method: `DataPlaneBackupRestoreCLI._list_qdrant_collections(self)` -> `list[str]`
- method: `DataPlaneBackupRestoreCLI._backup_qdrant(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._restore_qdrant(self)` -> `None`
- method: `DataPlaneBackupRestoreCLI._verify_qdrant(self)` -> `dict[str, Any]`
- method: `DataPlaneBackupRestoreCLI._resolve_restore_artifact(self, component: str, suffix: str)` -> `Path`
- function: `build_parser()` -> `argparse.ArgumentParser`
- function: `main(argv: list[str] | None = None)` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
