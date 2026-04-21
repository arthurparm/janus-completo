from typing import Any

import structlog
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db import db
from app.models.user_models import Consent

logger = structlog.get_logger(__name__)


class DBMigrationService:
    def _get_session(self) -> Session:
        return db.get_session_direct()

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
                s.execute(text("CREATE INDEX idx_user_lookup ON users (email, external_id)"))
                applied.append("users.idx_user_lookup")
            if not self._column_exists(s, "users", "username"):
                s.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50) NULL"))
                applied.append("users.username")
            if not self._column_exists(s, "users", "password_hash"):
                s.execute(text("ALTER TABLE users ADD COLUMN password_hash TEXT NULL"))
                applied.append("users.password_hash")
            if not self._column_exists(s, "users", "password_reset_token_hash"):
                s.execute(text("ALTER TABLE users ADD COLUMN password_reset_token_hash VARCHAR(128) NULL"))
                applied.append("users.password_reset_token_hash")
            if not self._column_exists(s, "users", "password_reset_expires_at"):
                s.execute(text("ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP NULL"))
                applied.append("users.password_reset_expires_at")
            if not self._constraint_exists(s, "users", "unique_user_email"):
                s.execute(
                    text(
                        self._unique_constraint_sql(
                            dialect=dialect,
                            table="users",
                            constraint="unique_user_email",
                            columns_csv="email",
                        )
                    )
                )
                applied.append("users.unique_user_email")
            if not self._constraint_exists(s, "users", "unique_user_username"):
                s.execute(
                    text(
                        self._unique_constraint_sql(
                            dialect=dialect,
                            table="users",
                            constraint="unique_user_username",
                            columns_csv="username",
                        )
                    )
                )
                applied.append("users.unique_user_username")
            if not self._constraint_exists(s, "users", "unique_user_external_id"):
                s.execute(
                    text(
                        self._unique_constraint_sql(
                            dialect=dialect,
                            table="users",
                            constraint="unique_user_external_id",
                            columns_csv="external_id",
                        )
                    )
                )
                applied.append("users.unique_user_external_id")
            if not self._column_exists(s, "pending_actions", "simulation_summary_json"):
                s.execute(text("ALTER TABLE pending_actions ADD COLUMN simulation_summary_json TEXT NULL"))
                applied.append("pending_actions.simulation_summary_json")
            if not self._column_exists(s, "pending_actions", "simulation_generated_at"):
                s.execute(text("ALTER TABLE pending_actions ADD COLUMN simulation_generated_at TIMESTAMP NULL"))
                applied.append("pending_actions.simulation_generated_at")
            if not self._column_exists(s, "pending_actions", "simulation_version"):
                s.execute(text("ALTER TABLE pending_actions ADD COLUMN simulation_version VARCHAR(20) NULL"))
                applied.append("pending_actions.simulation_version")
            if not self._index_exists(s, "profiles", "idx_profile_user"):
                s.execute(text("CREATE INDEX idx_profile_user ON profiles (user_id)"))
                applied.append("profiles.idx_profile_user")
            if not self._index_exists(s, "sessions", "idx_session_user"):
                s.execute(text("CREATE INDEX idx_session_user ON sessions (user_id, updated_at)"))
                applied.append("sessions.idx_session_user")
            if not self._index_exists(s, "messages", "idx_message_session_ts"):
                s.execute(text("CREATE INDEX idx_message_session_ts ON messages (session_id, timestamp)"))
                applied.append("messages.idx_message_session_ts")
            if not self._constraint_exists(s, "roles", "unique_role_name"):
                s.execute(
                    text(
                        self._unique_constraint_sql(
                            dialect=dialect,
                            table="roles",
                            constraint="unique_role_name",
                            columns_csv="name",
                        )
                    )
                )
                applied.append("roles.unique_role_name")
            if not self._constraint_exists(s, consent_table, "unique_user_privacy_scope_consent"):
                s.execute(
                    text(
                        self._unique_constraint_sql(
                            dialect=dialect,
                            table=consent_table,
                            constraint="unique_user_privacy_scope_consent",
                            columns_csv="user_id, scope",
                        )
                    )
                )
                applied.append(f"{consent_table}.unique_user_privacy_scope_consent")
            if not self._index_exists(s, consent_table, "idx_privacy_consent_user_scope"):
                s.execute(
                    text(
                        f"CREATE INDEX idx_privacy_consent_user_scope ON {consent_table} (user_id, scope)"
                    )
                )
                applied.append(f"{consent_table}.idx_privacy_consent_user_scope")
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
            return {"status": "applied", "changes": applied}
        except Exception as e:
            logger.error("DB migration failed", exc_info=e)
            return {"status": "error", "detail": str(e), "changes": applied}
        finally:
            s.close()


db_migration_service = DBMigrationService()
