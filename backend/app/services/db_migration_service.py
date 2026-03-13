from typing import Any

import structlog
from app.db import db
from app.models.user_models import Consent
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


class DBMigrationService:
    def _get_session(self) -> Session:
        return db.get_session_direct()

    def _execute_ddl(self, s: Session, sql: str, change_id: str, applied: list[str]) -> None:
        s.execute(text(sql))
        commit = getattr(s, "commit", None)
        if callable(commit):
            commit()
        applied.append(change_id)

    def _index_exists(self, s: Session, table: str, index_name: str) -> bool:
        try:
            insp = inspect(s.get_bind())
            indexes = insp.get_indexes(table) or []
            return any(idx.get("name") == index_name for idx in indexes)
        except Exception:
            return False

    def _constraint_exists(self, s: Session, table: str, constraint_name: str) -> bool:
        try:
            insp = inspect(s.get_bind())
            uniques = insp.get_unique_constraints(table) or []
            return any(uq.get("name") == constraint_name for uq in uniques)
        except Exception:
            return False

    def _column_exists(self, s: Session, table: str, column: str) -> bool:
        try:
            insp = inspect(s.get_bind())
            cols = insp.get_columns(table) or []
            return any(col.get("name") == column for col in cols)
        except Exception:
            return False

    def _dialect_name(self, s: Session) -> str:
        try:
            bind = s.get_bind()
            name = (bind.dialect.name if bind and bind.dialect else "") or ""
            return str(name).lower()
        except Exception:
            return ""

    def _unique_constraint_sql(
        self, *, dialect: str, table: str, constraint: str, columns_csv: str
    ) -> str:
        if dialect in ("mysql", "mariadb"):
            return f"ALTER TABLE {table} ADD CONSTRAINT {constraint} UNIQUE KEY ({columns_csv})"
        return f"ALTER TABLE {table} ADD CONSTRAINT {constraint} UNIQUE ({columns_csv})"

    def _details_json_column_sql(self, *, dialect: str) -> str:
        if dialect in ("postgresql", "postgres"):
            return "ALTER TABLE audit_events ADD COLUMN details_json JSONB NULL"
        return "ALTER TABLE audit_events ADD COLUMN details_json TEXT NULL"

    def _message_json_column_sql(self, *, dialect: str, column: str) -> str:
        if dialect in ("postgresql", "postgres"):
            return f"ALTER TABLE messages ADD COLUMN {column} JSONB NULL"
        return f"ALTER TABLE messages ADD COLUMN {column} TEXT NULL"

    def _knowledge_spaces_table_sql(self, *, dialect: str) -> str:
        pk_sql = "id SERIAL PRIMARY KEY" if dialect in ("postgresql", "postgres") else "id INTEGER PRIMARY KEY AUTOINCREMENT"
        return f"""
                    CREATE TABLE IF NOT EXISTS knowledge_spaces (
                        {pk_sql},
                        knowledge_space_id VARCHAR(255) NOT NULL UNIQUE,
                        user_id VARCHAR(128) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        source_type VARCHAR(64) NOT NULL DEFAULT 'documentation',
                        source_id VARCHAR(255) NULL,
                        edition_or_version VARCHAR(128) NULL,
                        language VARCHAR(32) NULL,
                        parent_collection_id VARCHAR(255) NULL,
                        description TEXT NULL,
                        consolidation_status VARCHAR(32) NOT NULL DEFAULT 'not_started',
                        consolidation_summary TEXT NULL,
                        last_consolidated_at TIMESTAMP NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """

    def validate_schema(self) -> dict[str, Any]:
        s = self._get_session()
        try:
            checks: list[dict[str, Any]] = []
            consent_table = Consent.__tablename__

            def add(table: str, name: str, kind: str, exists: bool) -> None:
                checks.append({"table": table, "name": name, "kind": kind, "exists": exists})

            add(
                "users",
                "idx_user_lookup",
                "index",
                self._index_exists(s, "users", "idx_user_lookup"),
            )
            add(
                "profiles",
                "idx_profile_user",
                "index",
                self._index_exists(s, "profiles", "idx_profile_user"),
            )
            add(
                "sessions",
                "idx_session_user",
                "index",
                self._index_exists(s, "sessions", "idx_session_user"),
            )
            add(
                "messages",
                "idx_message_session_ts",
                "index",
                self._index_exists(s, "messages", "idx_message_session_ts"),
            )
            for column in (
                "knowledge_space_id",
                "mode_used",
                "base_used",
                "citations_json",
                "citation_status_json",
                "ui_json",
                "source_scope_json",
                "gaps_or_conflicts_json",
                "understanding_json",
                "confirmation_json",
                "agent_state_json",
                "delivery_status",
                "failure_classification",
                "provider",
                "model",
            ):
                add("messages", column, "column", self._column_exists(s, "messages", column))
            add(
                "roles",
                "unique_role_name",
                "constraint",
                self._constraint_exists(s, "roles", "unique_role_name"),
            )
            add(
                "users",
                "username",
                "column",
                self._column_exists(s, "users", "username"),
            )
            add(
                "users",
                "password_hash",
                "column",
                self._column_exists(s, "users", "password_hash"),
            )
            add(
                "users",
                "cpf_hash",
                "column",
                self._column_exists(s, "users", "cpf_hash"),
            )
            add(
                "users",
                "password_reset_token_hash",
                "column",
                self._column_exists(s, "users", "password_reset_token_hash"),
            )
            add(
                "users",
                "password_reset_expires_at",
                "column",
                self._column_exists(s, "users", "password_reset_expires_at"),
            )
            add(
                "users",
                "unique_user_username",
                "constraint",
                self._constraint_exists(s, "users", "unique_user_username"),
            )
            add(
                "users",
                "unique_user_email",
                "constraint",
                self._constraint_exists(s, "users", "unique_user_email"),
            )
            add(
                "users",
                "unique_user_external_id",
                "constraint",
                self._constraint_exists(s, "users", "unique_user_external_id"),
            )
            add(
                "users",
                "unique_user_cpf_hash",
                "constraint",
                self._constraint_exists(s, "users", "unique_user_cpf_hash"),
            )
            add(
                "pending_actions",
                "simulation_summary_json",
                "column",
                self._column_exists(s, "pending_actions", "simulation_summary_json"),
            )
            add(
                "pending_actions",
                "simulation_generated_at",
                "column",
                self._column_exists(s, "pending_actions", "simulation_generated_at"),
            )
            add(
                "pending_actions",
                "simulation_version",
                "column",
                self._column_exists(s, "pending_actions", "simulation_version"),
            )
            for column in (
                "knowledge_space_id",
                "source_type",
                "source_id",
                "edition_or_version",
                "language",
                "parent_collection_id",
            ):
                add(
                    "document_manifests",
                    column,
                    "column",
                    self._column_exists(s, "document_manifests", column),
                )
            add(
                "knowledge_spaces",
                "knowledge_space_id",
                "column",
                self._column_exists(s, "knowledge_spaces", "knowledge_space_id"),
            )
            add(
                "knowledge_spaces",
                "idx_knowledge_spaces_user",
                "index",
                self._index_exists(s, "knowledge_spaces", "idx_knowledge_spaces_user"),
            )
            add(
                "knowledge_spaces",
                "idx_knowledge_spaces_user_status",
                "index",
                self._index_exists(s, "knowledge_spaces", "idx_knowledge_spaces_user_status"),
            )
            add(
                consent_table,
                "unique_user_privacy_scope_consent",
                "constraint",
                self._constraint_exists(s, consent_table, "unique_user_privacy_scope_consent"),
            )
            add(
                consent_table,
                "idx_privacy_consent_user_scope",
                "index",
                self._index_exists(s, consent_table, "idx_privacy_consent_user_scope"),
            )
            ok = all(c["exists"] for c in checks)
            return {"status": "ok" if ok else "missing", "checks": checks}
        finally:
            s.close()

    def migrate_schema(self) -> dict[str, Any]:
        s = self._get_session()
        applied: list[str] = []
        try:
            dialect = self._dialect_name(s)
            consent_table = Consent.__tablename__
            if not self._index_exists(s, "users", "idx_user_lookup"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_user_lookup ON users (email, external_id)",
                    "users.idx_user_lookup",
                    applied,
                )
            if not self._column_exists(s, "users", "username"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE users ADD COLUMN username VARCHAR(50) NULL",
                    "users.username",
                    applied,
                )
            if not self._column_exists(s, "users", "password_hash"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE users ADD COLUMN password_hash TEXT NULL",
                    "users.password_hash",
                    applied,
                )
            if not self._column_exists(s, "users", "cpf_hash"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE users ADD COLUMN cpf_hash VARCHAR(128) NULL",
                    "users.cpf_hash",
                    applied,
                )
            if not self._column_exists(s, "users", "password_reset_token_hash"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE users ADD COLUMN password_reset_token_hash VARCHAR(128) NULL",
                    "users.password_reset_token_hash",
                    applied,
                )
            if not self._column_exists(s, "users", "password_reset_expires_at"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP NULL",
                    "users.password_reset_expires_at",
                    applied,
                )
            if not self._constraint_exists(s, "users", "unique_user_email"):
                self._execute_ddl(
                    s,
                    self._unique_constraint_sql(
                        dialect=dialect,
                        table="users",
                        constraint="unique_user_email",
                        columns_csv="email",
                    ),
                    "users.unique_user_email",
                    applied,
                )
            if not self._constraint_exists(s, "users", "unique_user_username"):
                self._execute_ddl(
                    s,
                    self._unique_constraint_sql(
                        dialect=dialect,
                        table="users",
                        constraint="unique_user_username",
                        columns_csv="username",
                    ),
                    "users.unique_user_username",
                    applied,
                )
            if not self._constraint_exists(s, "users", "unique_user_external_id"):
                self._execute_ddl(
                    s,
                    self._unique_constraint_sql(
                        dialect=dialect,
                        table="users",
                        constraint="unique_user_external_id",
                        columns_csv="external_id",
                    ),
                    "users.unique_user_external_id",
                    applied,
                )
            if not self._constraint_exists(s, "users", "unique_user_cpf_hash"):
                self._execute_ddl(
                    s,
                    self._unique_constraint_sql(
                        dialect=dialect,
                        table="users",
                        constraint="unique_user_cpf_hash",
                        columns_csv="cpf_hash",
                    ),
                    "users.unique_user_cpf_hash",
                    applied,
                )
            if not self._column_exists(s, "pending_actions", "simulation_summary_json"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE pending_actions ADD COLUMN simulation_summary_json TEXT NULL",
                    "pending_actions.simulation_summary_json",
                    applied,
                )
            if not self._column_exists(s, "pending_actions", "simulation_generated_at"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE pending_actions ADD COLUMN simulation_generated_at TIMESTAMP NULL",
                    "pending_actions.simulation_generated_at",
                    applied,
                )
            if not self._column_exists(s, "pending_actions", "simulation_version"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE pending_actions ADD COLUMN simulation_version VARCHAR(20) NULL",
                    "pending_actions.simulation_version",
                    applied,
                )
            if not self._index_exists(s, "profiles", "idx_profile_user"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_profile_user ON profiles (user_id)",
                    "profiles.idx_profile_user",
                    applied,
                )
            if not self._index_exists(s, "sessions", "idx_session_user"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_session_user ON sessions (user_id, updated_at)",
                    "sessions.idx_session_user",
                    applied,
                )
            if not self._index_exists(s, "messages", "idx_message_session_ts"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_message_session_ts ON messages (session_id, timestamp)",
                    "messages.idx_message_session_ts",
                    applied,
                )
            json_column_sql = "JSONB" if dialect in ("postgresql", "postgres") else "TEXT"
            for column in (
                "citations_json",
                "citation_status_json",
                "ui_json",
                "understanding_json",
                "confirmation_json",
                "agent_state_json",
            ):
                if not self._column_exists(s, "messages", column):
                    self._execute_ddl(
                        s,
                        f"ALTER TABLE messages ADD COLUMN {column} {json_column_sql} NULL",
                        f"messages.{column}",
                        applied,
                    )
            if not self._column_exists(s, "messages", "delivery_status"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE messages ADD COLUMN delivery_status VARCHAR(32) NULL",
                    "messages.delivery_status",
                    applied,
                )
            if not self._column_exists(s, "messages", "failure_classification"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE messages ADD COLUMN failure_classification VARCHAR(32) NULL",
                    "messages.failure_classification",
                    applied,
                )
            if not self._column_exists(s, "messages", "provider"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE messages ADD COLUMN provider VARCHAR(100) NULL",
                    "messages.provider",
                    applied,
                )
            if not self._column_exists(s, "messages", "model"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE messages ADD COLUMN model VARCHAR(120) NULL",
                    "messages.model",
                    applied,
                )
            if not self._constraint_exists(s, "roles", "unique_role_name"):
                self._execute_ddl(
                    s,
                    self._unique_constraint_sql(
                        dialect=dialect,
                        table="roles",
                        constraint="unique_role_name",
                        columns_csv="name",
                    ),
                    "roles.unique_role_name",
                    applied,
                )
            if not self._constraint_exists(s, consent_table, "unique_user_privacy_scope_consent"):
                self._execute_ddl(
                    s,
                    self._unique_constraint_sql(
                        dialect=dialect,
                        table=consent_table,
                        constraint="unique_user_privacy_scope_consent",
                        columns_csv="user_id, scope",
                    ),
                    f"{consent_table}.unique_user_privacy_scope_consent",
                    applied,
                )
            if not self._index_exists(s, consent_table, "idx_privacy_consent_user_scope"):
                self._execute_ddl(
                    s,
                    f"CREATE INDEX idx_privacy_consent_user_scope ON {consent_table} (user_id, scope)",
                    f"{consent_table}.idx_privacy_consent_user_scope",
                    applied,
                )
            try:
                self._execute_ddl(
                    s,
                    self._knowledge_spaces_table_sql(dialect=dialect),
                    "knowledge_spaces.create_table",
                    applied,
                )
            except Exception:
                pass
            if not self._index_exists(s, "knowledge_spaces", "idx_knowledge_spaces_user"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_knowledge_spaces_user ON knowledge_spaces (user_id)",
                    "knowledge_spaces.idx_knowledge_spaces_user",
                    applied,
                )
            if not self._index_exists(s, "knowledge_spaces", "idx_knowledge_spaces_user_status"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_knowledge_spaces_user_status ON knowledge_spaces (user_id, consolidation_status)",
                    "knowledge_spaces.idx_knowledge_spaces_user_status",
                    applied,
                )
            knowledge_space_columns = {
                "sections_total": "ALTER TABLE knowledge_spaces ADD COLUMN sections_total INTEGER NOT NULL DEFAULT 0",
                "sections_indexed": "ALTER TABLE knowledge_spaces ADD COLUMN sections_indexed INTEGER NOT NULL DEFAULT 0",
                "sections_skipped_as_noise": "ALTER TABLE knowledge_spaces ADD COLUMN sections_skipped_as_noise INTEGER NOT NULL DEFAULT 0",
                "canonical_frames_total": "ALTER TABLE knowledge_spaces ADD COLUMN canonical_frames_total INTEGER NOT NULL DEFAULT 0",
                "consolidation_quality_score": "ALTER TABLE knowledge_spaces ADD COLUMN consolidation_quality_score VARCHAR(32) NULL",
            }
            for column, sql in knowledge_space_columns.items():
                if not self._column_exists(s, "knowledge_spaces", column):
                    self._execute_ddl(
                        s,
                        sql,
                        f"knowledge_spaces.{column}",
                        applied,
                    )
            document_manifest_columns = {
                "knowledge_space_id": "ALTER TABLE document_manifests ADD COLUMN knowledge_space_id VARCHAR(255) NULL",
                "source_type": "ALTER TABLE document_manifests ADD COLUMN source_type VARCHAR(64) NULL",
                "source_id": "ALTER TABLE document_manifests ADD COLUMN source_id VARCHAR(255) NULL",
                "doc_role": "ALTER TABLE document_manifests ADD COLUMN doc_role VARCHAR(32) NULL",
                "edition_or_version": "ALTER TABLE document_manifests ADD COLUMN edition_or_version VARCHAR(128) NULL",
                "language": "ALTER TABLE document_manifests ADD COLUMN language VARCHAR(32) NULL",
                "parent_collection_id": "ALTER TABLE document_manifests ADD COLUMN parent_collection_id VARCHAR(255) NULL",
            }
            for column, sql in document_manifest_columns.items():
                if not self._column_exists(s, "document_manifests", column):
                    self._execute_ddl(
                        s,
                        sql,
                        f"document_manifests.{column}",
                        applied,
                    )
            if not self._index_exists(s, "document_manifests", "idx_document_manifests_space"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_document_manifests_space ON document_manifests (user_id, knowledge_space_id)",
                    "document_manifests.idx_document_manifests_space",
                    applied,
                )
            message_text_columns = {
                "knowledge_space_id": "ALTER TABLE messages ADD COLUMN knowledge_space_id VARCHAR(255) NULL",
                "mode_used": "ALTER TABLE messages ADD COLUMN mode_used VARCHAR(64) NULL",
                "base_used": "ALTER TABLE messages ADD COLUMN base_used VARCHAR(64) NULL",
            }
            for column, sql in message_text_columns.items():
                if not self._column_exists(s, "messages", column):
                    self._execute_ddl(
                        s,
                        sql,
                        f"messages.{column}",
                        applied,
                    )
            for column in ("source_scope_json", "gaps_or_conflicts_json"):
                if not self._column_exists(s, "messages", column):
                    self._execute_ddl(
                        s,
                        self._message_json_column_sql(dialect=dialect, column=column),
                        f"messages.{column}",
                        applied,
                    )
            # AuditEvent evolution
            try:
                s.execute(text("ALTER TABLE audit_events ADD COLUMN justification TEXT NULL"))
                applied.append("audit_events.add_justification")
            except Exception:
                pass
            try:
                s.execute(text(self._details_json_column_sql(dialect=dialect)))
                applied.append("audit_events.add_details_json")
            except Exception:
                pass
            try:
                s.execute(text("CREATE INDEX idx_audit_action ON audit_events (action)"))
                applied.append("audit_events.idx_audit_action")
            except Exception:
                pass
            try:
                s.commit()
            except Exception:
                pass
            return {"status": "applied", "changes": applied}
        except Exception as e:
            logger.error("DB migration failed", exc_info=e)
            return {"status": "error", "detail": str(e), "changes": applied}
        finally:
            s.close()


db_migration_service = DBMigrationService()
