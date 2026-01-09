from typing import Any

import structlog

from app.db.mysql_config import mysql_db

logger = structlog.get_logger(__name__)


class DBMigrationService:
    def _get_session(self):
        return mysql_db.get_session_direct()

    def _index_exists(self, s, table: str, index_name: str) -> bool:
        try:
            sql = "SELECT COUNT(1) AS cnt FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND INDEX_NAME = :idx"
            r = s.execute(sql, {"table": table, "idx": index_name}).fetchone()
            return bool(r and int(r[0]) > 0)
        except Exception:
            return False

    def _constraint_exists(self, s, table: str, constraint_name: str) -> bool:
        try:
            sql = "SELECT COUNT(1) AS cnt FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND CONSTRAINT_NAME = :cname"
            r = s.execute(sql, {"table": table, "cname": constraint_name}).fetchone()
            return bool(r and int(r[0]) > 0)
        except Exception:
            return False

    def validate_schema(self) -> dict[str, Any]:
        s = self._get_session()
        try:
            checks: list[dict[str, Any]] = []

            def add(table: str, name: str, kind: str, exists: bool):
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
                "consents",
                "unique_user_scope_consent",
                "constraint",
                self._constraint_exists(s, "consents", "unique_user_scope_consent"),
            )
            add(
                "consents",
                "idx_consent_user_scope",
                "index",
                self._index_exists(s, "consents", "idx_consent_user_scope"),
            )
            ok = all(c["exists"] for c in checks)
            return {"status": "ok" if ok else "missing", "checks": checks}
        finally:
            s.close()

    def migrate_schema(self) -> dict[str, Any]:
        s = self._get_session()
        applied: list[str] = []
        try:
            if not self._index_exists(s, "users", "idx_user_lookup"):
                s.execute("ALTER TABLE users ADD INDEX idx_user_lookup (email, external_id)")
                applied.append("users.idx_user_lookup")
            if not self._index_exists(s, "profiles", "idx_profile_user"):
                s.execute("ALTER TABLE profiles ADD INDEX idx_profile_user (user_id)")
                applied.append("profiles.idx_profile_user")
            if not self._index_exists(s, "sessions", "idx_session_user"):
                s.execute("ALTER TABLE sessions ADD INDEX idx_session_user (user_id, updated_at)")
                applied.append("sessions.idx_session_user")
            if not self._index_exists(s, "messages", "idx_message_session_ts"):
                s.execute(
                    "ALTER TABLE messages ADD INDEX idx_message_session_ts (session_id, timestamp)"
                )
                applied.append("messages.idx_message_session_ts")
            if not self._constraint_exists(s, "roles", "unique_role_name"):
                s.execute("ALTER TABLE roles ADD CONSTRAINT unique_role_name UNIQUE KEY (name)")
                applied.append("roles.unique_role_name")
            if not self._constraint_exists(s, "consents", "unique_user_scope_consent"):
                s.execute(
                    "ALTER TABLE consents ADD CONSTRAINT unique_user_scope_consent UNIQUE KEY (user_id, scope)"
                )
                applied.append("consents.unique_user_scope_consent")
            if not self._index_exists(s, "consents", "idx_consent_user_scope"):
                s.execute("ALTER TABLE consents ADD INDEX idx_consent_user_scope (user_id, scope)")
                applied.append("consents.idx_consent_user_scope")
            # AuditEvent evolution
            try:
                s.execute("ALTER TABLE audit_events ADD COLUMN justification TEXT NULL")
                applied.append("audit_events.add_justification")
            except Exception:
                pass
            try:
                s.execute("ALTER TABLE audit_events ADD COLUMN details_json TEXT NULL")
                applied.append("audit_events.add_details_json")
            except Exception:
                pass
            try:
                s.execute("ALTER TABLE audit_events ADD INDEX idx_audit_action (action)")
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
