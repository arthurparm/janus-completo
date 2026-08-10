import json
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
            foreign_keys = insp.get_foreign_keys(table) or []
            return any(
                constraint.get("name") == constraint_name
                for constraint in (*uniques, *foreign_keys)
            )
        except Exception:
            return False

    def _column_exists(self, s: Session, table: str, column: str) -> bool:
        try:
            insp = inspect(s.get_bind())
            cols = insp.get_columns(table) or []
            return any(col.get("name") == column for col in cols)
        except Exception:
            return False

    def _column_nullable(self, s: Session, table: str, column: str) -> bool | None:
        try:
            insp = inspect(s.get_bind())
            cols = insp.get_columns(table) or []
            for col in cols:
                if col.get("name") == column:
                    nullable = col.get("nullable")
                    if nullable is None:
                        return None
                    return bool(nullable)
        except Exception:
            return None
        return None

    def _table_exists(self, s: Session, table: str) -> bool:
        try:
            insp = inspect(s.get_bind())
            return bool(insp.has_table(table))
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

    def _prepare_outbox_lease_schema(
        self, s: Session, *, dialect: str, applied: list[str]
    ) -> None:
        if not self._table_exists(s, "outbox_events"):
            return

        column_sql = {
            "message_id": "VARCHAR(64) NULL",
            "claimed_by": "VARCHAR(128) NULL",
            "claim_token": "VARCHAR(64) NULL",
            "claimed_at": "TIMESTAMP NULL",
            "lease_until": "TIMESTAMP NULL",
        }
        for column, sql_type in column_sql.items():
            if not self._column_exists(s, "outbox_events", column):
                self._execute_ddl(
                    s,
                    f"ALTER TABLE outbox_events ADD COLUMN {column} {sql_type}",
                    f"outbox_events.{column}",
                    applied,
                )

        message_id_expression = (
            "CONCAT('outbox-', CAST(id AS CHAR))"
            if dialect in ("mysql", "mariadb")
            else "'outbox-' || CAST(id AS VARCHAR)"
        )
        s.execute(
            text(
                "UPDATE outbox_events "
                f"SET message_id = {message_id_expression} "
                "WHERE message_id IS NULL"
            )
        )
        s.execute(
            text(
                "UPDATE outbox_events SET lease_until = CURRENT_TIMESTAMP "
                "WHERE status = 'processing' AND lease_until IS NULL"
            )
        )

        if not self._index_exists(s, "outbox_events", "uq_outbox_message_id"):
            self._execute_ddl(
                s,
                "CREATE UNIQUE INDEX uq_outbox_message_id ON outbox_events (message_id)",
                "outbox_events.uq_message_id",
                applied,
            )
        if not self._index_exists(s, "outbox_events", "idx_outbox_status_lease"):
            self._execute_ddl(
                s,
                "CREATE INDEX idx_outbox_status_lease "
                "ON outbox_events (status, lease_until)",
                "outbox_events.idx_status_lease",
                applied,
            )

        if self._column_nullable(s, "outbox_events", "message_id") is not False:
            if dialect in ("postgresql", "postgres"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE outbox_events ALTER COLUMN message_id SET NOT NULL",
                    "outbox_events.message_id_not_null",
                    applied,
                )
            elif dialect in ("mysql", "mariadb"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE outbox_events MODIFY COLUMN message_id VARCHAR(64) NOT NULL",
                    "outbox_events.message_id_not_null",
                    applied,
                )

    def _prepare_chat_stream_ledger_schema(
        self, s: Session, *, dialect: str, applied: list[str]
    ) -> None:
        if dialect not in ("postgresql", "postgres"):
            return
        if not self._table_exists(s, "chat_stream_runs"):
            self._execute_ddl(
                s,
                """
                CREATE TABLE chat_stream_runs (
                    id VARCHAR(36) PRIMARY KEY,
                    owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    request_id VARCHAR(128) NOT NULL,
                    request_fingerprint VARCHAR(64) NOT NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'pending',
                    producer_token VARCHAR(64) NULL,
                    lease_until TIMESTAMP NULL,
                    last_event_sequence INTEGER NOT NULL DEFAULT 0,
                    error_code VARCHAR(64) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    expires_at TIMESTAMP NOT NULL,
                    CONSTRAINT uq_chat_stream_owner_session_request
                        UNIQUE (owner_user_id, session_id, request_id)
                )
                """,
                "chat_stream_runs.table",
                applied,
            )
        if not self._table_exists(s, "chat_stream_events"):
            self._execute_ddl(
                s,
                """
                CREATE TABLE chat_stream_events (
                    id SERIAL PRIMARY KEY,
                    run_id VARCHAR(36) NOT NULL
                        REFERENCES chat_stream_runs(id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_chat_stream_event_sequence UNIQUE (run_id, sequence)
                )
                """,
                "chat_stream_events.table",
                applied,
            )
        for table, index_name, sql in (
            (
                "chat_stream_runs",
                "idx_chat_stream_run_status_lease",
                "CREATE INDEX idx_chat_stream_run_status_lease "
                "ON chat_stream_runs (status, lease_until)",
            ),
            (
                "chat_stream_runs",
                "idx_chat_stream_run_owner_created",
                "CREATE INDEX idx_chat_stream_run_owner_created "
                "ON chat_stream_runs (owner_user_id, created_at)",
            ),
            (
                "chat_stream_events",
                "idx_chat_stream_event_cursor",
                "CREATE INDEX idx_chat_stream_event_cursor "
                "ON chat_stream_events (run_id, sequence)",
            ),
        ):
            if not self._index_exists(s, table, index_name):
                self._execute_ddl(s, sql, f"{table}.{index_name}", applied)

    def _prepare_chat_study_schema(
        self, s: Session, *, dialect: str, applied: list[str]
    ) -> None:
        if dialect not in ("postgresql", "postgres"):
            return
        if not self._table_exists(s, "chat_study_runs"):
            self._execute_ddl(
                s,
                """
                CREATE TABLE chat_study_runs (
                    id VARCHAR(36) PRIMARY KEY,
                    owner_user_id VARCHAR(128) NOT NULL,
                    conversation_id VARCHAR(128) NOT NULL,
                    message_id VARCHAR(128) NOT NULL,
                    question TEXT NOT NULL,
                    request_fingerprint VARCHAR(64) NOT NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1,
                    worker_token VARCHAR(64) NULL,
                    lease_until TIMESTAMP NULL,
                    placeholder_message TEXT NULL,
                    failure_classification VARCHAR(64) NULL,
                    final_response_json JSONB NULL,
                    error TEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    CONSTRAINT uq_chat_study_owner_conversation_message
                        UNIQUE (owner_user_id, conversation_id, message_id)
                )
                """,
                "chat_study_runs.table",
                applied,
            )
        for column, sql_type in (
            ("worker_token", "VARCHAR(64) NULL"),
            ("lease_until", "TIMESTAMP NULL"),
        ):
            if not self._column_exists(s, "chat_study_runs", column):
                self._execute_ddl(
                    s,
                    f"ALTER TABLE chat_study_runs ADD COLUMN {column} {sql_type}",
                    f"chat_study_runs.{column}",
                    applied,
                )
        if not self._index_exists(
            s,
            "chat_study_runs",
            "idx_chat_study_status_lease",
        ):
            self._execute_ddl(
                s,
                "CREATE INDEX idx_chat_study_status_lease "
                "ON chat_study_runs (status, lease_until)",
                "chat_study_runs.idx_chat_study_status_lease",
                applied,
            )

    def _prepare_chat_rest_idempotency_schema(
        self, s: Session, *, dialect: str, applied: list[str]
    ) -> None:
        if dialect not in ("postgresql", "postgres"):
            return
        if not self._table_exists(s, "chat_rest_runs"):
            self._execute_ddl(
                s,
                """
                CREATE TABLE chat_rest_runs (
                    id VARCHAR(36) PRIMARY KEY,
                    owner_user_id VARCHAR(128) NOT NULL,
                    conversation_id VARCHAR(128) NOT NULL,
                    request_id VARCHAR(128) NOT NULL,
                    request_fingerprint VARCHAR(64) NOT NULL,
                    status VARCHAR(24) NOT NULL DEFAULT 'pending',
                    producer_token VARCHAR(64) NULL,
                    lease_until TIMESTAMP NULL,
                    result_json JSONB NULL,
                    error_code VARCHAR(64) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    expires_at TIMESTAMP NOT NULL,
                    CONSTRAINT uq_chat_rest_owner_conversation_request
                        UNIQUE (owner_user_id, conversation_id, request_id)
                )
                """,
                "chat_rest_runs.table",
                applied,
            )
        for index_name, sql in (
            (
                "idx_chat_rest_status_lease",
                "CREATE INDEX idx_chat_rest_status_lease "
                "ON chat_rest_runs (status, lease_until)",
            ),
            (
                "idx_chat_rest_owner_created",
                "CREATE INDEX idx_chat_rest_owner_created "
                "ON chat_rest_runs (owner_user_id, created_at)",
            ),
        ):
            if not self._index_exists(s, "chat_rest_runs", index_name):
                self._execute_ddl(
                    s,
                    sql,
                    f"chat_rest_runs.{index_name}",
                    applied,
                )
    def _migrate_seeded_agent_configs_to_cloud(self, s: Session, applied: list[str]) -> None:
        if not self._table_exists(s, "agent_configurations"):
            return
        result = s.execute(
            text(
                "UPDATE agent_configurations "
                "SET llm_provider = 'openai', llm_model = 'gpt-5.6-luna' "
                "WHERE created_by = 'system' AND llm_provider IN ('ollama', 'local')"
            )
        )
        if int(getattr(result, "rowcount", 0) or 0) > 0:
            s.commit()
            applied.append("agent_configurations.system_cloud_only")

    def _count_null_pending_action_user_ids(self, s: Session) -> int | None:
        if not self._table_exists(s, "pending_actions"):
            return None
        if not self._column_exists(s, "pending_actions", "user_id"):
            return None
        try:
            row = s.execute(
                text("SELECT COUNT(*) FROM pending_actions WHERE user_id IS NULL")
            ).first()
            if not row:
                return 0
            return int(row[0] or 0)
        except Exception:
            return None

    def _pending_action_user_id_not_null_sql(self, *, dialect: str) -> str | None:
        if dialect in ("postgresql", "postgres"):
            return "ALTER TABLE pending_actions ALTER COLUMN user_id SET NOT NULL"
        if dialect in ("mysql", "mariadb"):
            return "ALTER TABLE pending_actions MODIFY COLUMN user_id VARCHAR(128) NOT NULL"
        return None

    def _backfill_pending_action_user_ids(self, s: Session, applied: list[str]) -> None:
        if not self._table_exists(s, "pending_actions") or not self._table_exists(s, "sessions"):
            return
        if not self._column_exists(s, "pending_actions", "user_id"):
            return
        if not self._column_exists(s, "pending_actions", "args_json"):
            return
        rows = s.execute(
            text("SELECT id, args_json FROM pending_actions WHERE user_id IS NULL")
        ).fetchall()
        if not rows:
            return

        updated = 0
        blocked = 0
        for row in rows:
            action_id = row[0]
            args_json = row[1]
            try:
                payload = json.loads(args_json) if args_json else {}
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                payload = {}

            conversation_id = payload.get("conversation_id")
            conversation_id_text = str(conversation_id or "").strip()
            if not conversation_id_text:
                blocked += 1
                continue
            try:
                session_id = int(conversation_id_text)
            except Exception:
                blocked += 1
                continue

            owner_row = s.execute(
                text("SELECT user_id FROM sessions WHERE id = :session_id"),
                {"session_id": session_id},
            ).first()
            owner_user_id = owner_row[0] if owner_row else None
            if owner_user_id is None:
                blocked += 1
                continue

            result = s.execute(
                text(
                    "UPDATE pending_actions SET user_id = :user_id "
                    "WHERE id = :action_id AND user_id IS NULL"
                ),
                {"user_id": str(owner_user_id), "action_id": int(action_id)},
            )
            updated += int(getattr(result, "rowcount", 0) or 0)

        if updated:
            commit = getattr(s, "commit", None)
            if callable(commit):
                commit()
        if updated or blocked:
            applied.append("pending_actions.user_id_backfill")
        logger.info(
            "pending_actions_user_id_backfill_completed",
            updated=updated,
            blocked=blocked,
        )

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
                "chat_stream_runs",
                "uq_chat_stream_owner_session_request",
                "constraint",
                self._constraint_exists(
                    s,
                    "chat_stream_runs",
                    "uq_chat_stream_owner_session_request",
                ),
            )
            add(
                "chat_stream_runs",
                "idx_chat_stream_run_status_lease",
                "index",
                self._index_exists(
                    s,
                    "chat_stream_runs",
                    "idx_chat_stream_run_status_lease",
                ),
            )
            add(
                "chat_stream_events",
                "idx_chat_stream_event_cursor",
                "index",
                self._index_exists(
                    s,
                    "chat_stream_events",
                    "idx_chat_stream_event_cursor",
                ),
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
                "unique_user_email",
                "constraint",
                self._constraint_exists(s, "users", "unique_user_email"),
            )
            add(
                "pending_actions",
                "user_id",
                "column",
                self._column_exists(s, "pending_actions", "user_id"),
            )
            add(
                "pending_actions",
                "user_id_not_null",
                "constraint",
                self._column_nullable(s, "pending_actions", "user_id") is False,
            )
            add(
                "pending_actions",
                "ownerless_rows_eliminated",
                "data",
                (self._count_null_pending_action_user_ids(s) or 0) == 0,
            )
            add(
                "pending_actions",
                "simulation_summary_json",
                "column",
                self._column_exists(s, "pending_actions", "simulation_summary_json"),
            )
            add(
                "pending_actions",
                "idx_pending_actions_status_user",
                "index",
                self._index_exists(s, "pending_actions", "idx_pending_actions_status_user"),
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
            add(
                "data_governance_records",
                "data_governance_records",
                "table",
                self._table_exists(s, "data_governance_records"),
            )
            for idx in ("idx_data_gov_resource", "idx_data_gov_user", "idx_data_gov_retention"):
                add(
                    "data_governance_records",
                    idx,
                    "index",
                    self._index_exists(s, "data_governance_records", idx),
                )
            for column in (
                "message_id",
                "claimed_by",
                "claim_token",
                "claimed_at",
                "lease_until",
            ):
                add(
                    "outbox_events",
                    column,
                    "column",
                    self._column_exists(s, "outbox_events", column),
                )
            add(
                "outbox_events",
                "uq_outbox_message_id",
                "index",
                self._index_exists(s, "outbox_events", "uq_outbox_message_id"),
            )
            add(
                "outbox_events",
                "idx_outbox_status_lease",
                "index",
                self._index_exists(s, "outbox_events", "idx_outbox_status_lease"),
            )
            ok = all(c["exists"] for c in checks)
            return {"status": "ok" if ok else "missing", "checks": checks}
        finally:
            s.close()

    def _count_experiment_owner_orphans(self, s: Session) -> int | None:
        if not self._table_exists(s, "experiments"):
            return None
        if not self._column_exists(s, "experiments", "owner_user_id"):
            return None
        try:
            row = s.execute(
                text("SELECT COUNT(*) FROM experiments WHERE owner_user_id IS NULL")
            ).first()
            if not row:
                return 0
            return int(row[0] or 0)
        except Exception:
            return None

    def _count_duplicate_profiles(self, s: Session) -> int | None:
        if not self._table_exists(s, "profiles"):
            return None
        try:
            row = s.execute(
                text(
                    "SELECT COUNT(*) FROM (SELECT user_id FROM profiles "
                    "GROUP BY user_id HAVING COUNT(*) > 1) duplicates"
                )
            ).first()
            if not row:
                return 0
            return int(row[0] or 0)
        except Exception:
            return None

    def _unresolved_auth_migration_quarantine(self, s: Session) -> dict[str, Any]:
        if not self._table_exists(s, "auth_migration_quarantine"):
            return {"total": 0, "by_resource_type": {}}
        try:
            rows = s.execute(
                text(
                    "SELECT resource_type, COUNT(*) AS total "
                    "FROM auth_migration_quarantine "
                    "WHERE resolved_at IS NULL "
                    "GROUP BY resource_type "
                    "ORDER BY resource_type"
                )
            ).fetchall()
        except Exception:
            return {"total": 0, "by_resource_type": {}}

        by_resource_type: dict[str, int] = {}
        total = 0
        for row in rows or []:
            resource_type = str(row[0] or "").strip()
            count = int(row[1] or 0)
            if not resource_type:
                continue
            by_resource_type[resource_type] = count
            total += count
        return {"total": total, "by_resource_type": by_resource_type}

    def _constraint_readiness_snapshot(self, s: Session) -> dict[str, Any]:
        pending_actions_null_rows = self._count_null_pending_action_user_ids(s)
        auth_owner_orphans = self._count_experiment_owner_orphans(s)
        duplicate_profiles = self._count_duplicate_profiles(s)
        unresolved_auth_quarantine = self._unresolved_auth_migration_quarantine(s)

        blockers: list[str] = []
        if pending_actions_null_rows and pending_actions_null_rows > 0:
            blockers.append(
                f"pending_actions.user_id ainda possui {pending_actions_null_rows} registros sem owner"
            )
        if auth_owner_orphans and auth_owner_orphans > 0:
            blockers.append(
                f"experiments.owner_user_id ainda possui {auth_owner_orphans} registros sem backfill"
            )
        if duplicate_profiles and duplicate_profiles > 0:
            blockers.append(
                f"profiles ainda possui {duplicate_profiles} usuarios com perfis duplicados"
            )
        if unresolved_auth_quarantine["total"] > 0:
            blockers.append(
                "auth_migration_quarantine ainda possui registros pendentes: "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in sorted(
                        unresolved_auth_quarantine["by_resource_type"].items()
                    )
                )
            )

        return {
            "ready_for_constraints": not blockers,
            "blockers": blockers,
            "pending_actions_user_id_null_rows": pending_actions_null_rows,
            "auth_owner_orphans": auth_owner_orphans,
            "duplicate_profiles": duplicate_profiles,
            "auth_migration_quarantine": unresolved_auth_quarantine,
        }

    def _prepare_postgres_auth_constraint_data(
        self, s: Session, applied: list[str]
    ) -> dict[str, Any]:
        auth_owner_orphans: int | None = None
        duplicate_profiles: int | None = None

        s.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS auth_migration_quarantine (
                    resource_type VARCHAR(64) NOT NULL,
                    resource_id VARCHAR(255) NOT NULL,
                    reason VARCHAR(255) NOT NULL,
                    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL,
                    PRIMARY KEY (resource_type, resource_id)
                )
                """
            )
        )
        applied.append("auth_migration_quarantine.table")

        if self._table_exists(s, "experiments") and not self._column_exists(
            s, "experiments", "owner_user_id"
        ):
            s.execute(text("ALTER TABLE experiments ADD COLUMN owner_user_id INTEGER NULL"))
            applied.append("experiments.owner_user_id")

        if self._table_exists(s, "experiments") and self._column_exists(
            s, "experiments", "owner_user_id"
        ):
            s.execute(
                text(
                    """
                    UPDATE experiments e
                    SET owner_user_id = e.user_id::INTEGER
                    FROM users u
                    WHERE e.owner_user_id IS NULL
                      AND e.user_id ~ '^[0-9]+$'
                      AND u.id = e.user_id::INTEGER
                    """
                )
            )
            auth_owner_orphans = self._count_experiment_owner_orphans(s)
            s.execute(
                text(
                    """
                    INSERT INTO auth_migration_quarantine(resource_type, resource_id, reason)
                    SELECT 'experiment', id::TEXT, 'owner_user_id could not be backfilled'
                    FROM experiments WHERE owner_user_id IS NULL
                    ON CONFLICT (resource_type, resource_id) DO UPDATE
                    SET reason = EXCLUDED.reason, detected_at = CURRENT_TIMESTAMP,
                        resolved_at = NULL
                    """
                )
            )
            s.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_experiment_owner_status "
                    "ON experiments (owner_user_id, status)"
                )
            )
            applied.append("experiments.owner_backfill")
            applied.append("experiments.owner_orphans_quarantined")
            if auth_owner_orphans == 0:
                s.execute(
                    text(
                        "UPDATE auth_migration_quarantine SET resolved_at = CURRENT_TIMESTAMP "
                        "WHERE resource_type = 'experiment' AND resolved_at IS NULL"
                    )
                )

        if self._table_exists(s, "profiles"):
            duplicate_profiles = self._count_duplicate_profiles(s)
            s.execute(
                text(
                    """
                    INSERT INTO auth_migration_quarantine(resource_type, resource_id, reason)
                    SELECT 'profile', user_id::TEXT, 'multiple profiles for one user'
                    FROM profiles GROUP BY user_id HAVING COUNT(*) > 1
                    ON CONFLICT (resource_type, resource_id) DO UPDATE
                    SET reason = EXCLUDED.reason, detected_at = CURRENT_TIMESTAMP,
                        resolved_at = NULL
                    """
                )
            )
            applied.append("profiles.duplicate_scan")
            if duplicate_profiles == 0:
                s.execute(
                    text(
                        "UPDATE auth_migration_quarantine SET resolved_at = CURRENT_TIMESTAMP "
                        "WHERE resource_type = 'profile' AND resolved_at IS NULL"
                    )
                )

        return {
            "auth_owner_orphans": auth_owner_orphans,
            "duplicate_profiles": duplicate_profiles,
        }

    def prepare_constraint_data(self) -> dict[str, Any]:
        s = self._get_session()
        applied: list[str] = []
        try:
            dialect = self._dialect_name(s)
            auth_owner_orphans: int | None = None
            duplicate_profiles: int | None = None

            if not self._column_exists(s, "pending_actions", "user_id"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE pending_actions ADD COLUMN user_id VARCHAR(128) NULL",
                    "pending_actions.user_id",
                    applied,
                )
            if not self._index_exists(s, "pending_actions", "idx_pending_actions_status_user"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_pending_actions_status_user ON pending_actions (status, user_id)",
                    "pending_actions.idx_pending_actions_status_user",
                    applied,
                )
            self._backfill_pending_action_user_ids(s, applied)

            if dialect in ("postgresql", "postgres"):
                postgres_prep = self._prepare_postgres_auth_constraint_data(s, applied)
                auth_owner_orphans = postgres_prep["auth_owner_orphans"]
                duplicate_profiles = postgres_prep["duplicate_profiles"]

            commit = getattr(s, "commit", None)
            if callable(commit):
                commit()

            snapshot = self._constraint_readiness_snapshot(s)
            return {
                "status": "prepared",
                "changes": applied,
                "auth_owner_orphans": (
                    auth_owner_orphans
                    if auth_owner_orphans is not None
                    else snapshot["auth_owner_orphans"]
                ),
                "duplicate_profiles": (
                    duplicate_profiles
                    if duplicate_profiles is not None
                    else snapshot["duplicate_profiles"]
                ),
                **snapshot,
            }
        except Exception as e:
            logger.error("DB prepare constraint data failed", exc_info=e)
            rollback = getattr(s, "rollback", None)
            if callable(rollback):
                rollback()
            snapshot = self._constraint_readiness_snapshot(s)
            return {
                "status": "error",
                "detail": "Internal error during constraint preparation",
                "changes": applied,
                **snapshot,
            }
        finally:
            s.close()

    def validate_constraint_readiness(self) -> dict[str, Any]:
        s = self._get_session()
        try:
            snapshot = self._constraint_readiness_snapshot(s)
            return {
                "status": "ready" if snapshot["ready_for_constraints"] else "blocked",
                **snapshot,
            }
        finally:
            s.close()

    def apply_prepared_constraints(self) -> dict[str, Any]:
        s = self._get_session()
        applied: list[str] = []
        pending_actions_user_id_not_null_enforced = False
        try:
            snapshot = self._constraint_readiness_snapshot(s)
            if not snapshot["ready_for_constraints"]:
                return {
                    "status": "blocked",
                    "changes": applied,
                    "pending_actions_user_id_not_null_enforced": False,
                    **snapshot,
                }

            dialect = self._dialect_name(s)
            if self._column_exists(s, "pending_actions", "user_id") and self._column_nullable(
                s, "pending_actions", "user_id"
            ) is not False:
                not_null_sql = self._pending_action_user_id_not_null_sql(dialect=dialect)
                if not_null_sql:
                    self._execute_ddl(
                        s,
                        not_null_sql,
                        "pending_actions.user_id_not_null",
                        applied,
                    )
                    pending_actions_user_id_not_null_enforced = True

            if dialect in ("postgresql", "postgres"):
                if self._table_exists(s, "experiments") and self._column_exists(
                    s, "experiments", "owner_user_id"
                ):
                    if not self._constraint_exists(s, "experiments", "fk_experiments_owner_user"):
                        s.execute(
                            text(
                                "ALTER TABLE experiments ADD CONSTRAINT "
                                "fk_experiments_owner_user FOREIGN KEY (owner_user_id) "
                                "REFERENCES users(id) ON DELETE RESTRICT"
                            )
                        )
                        applied.append("experiments.owner_user_fk")
                    if self._column_nullable(s, "experiments", "owner_user_id") is not False:
                        s.execute(
                            text(
                                "ALTER TABLE experiments ALTER COLUMN owner_user_id SET NOT NULL"
                            )
                        )
                        applied.append("experiments.owner_user_not_null")

                if self._table_exists(s, "profiles") and not self._index_exists(
                    s, "profiles", "unique_profile_user"
                ):
                    s.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS unique_profile_user "
                            "ON profiles (user_id)"
                        )
                    )
                    applied.append("profiles.unique_user")

            commit = getattr(s, "commit", None)
            if callable(commit):
                commit()

            snapshot = self._constraint_readiness_snapshot(s)
            return {
                "status": "applied",
                "changes": applied,
                "pending_actions_user_id_not_null_enforced": pending_actions_user_id_not_null_enforced,
                **snapshot,
            }
        except Exception as e:
            logger.error("DB apply prepared constraints failed", exc_info=e)
            rollback = getattr(s, "rollback", None)
            if callable(rollback):
                rollback()
            snapshot = self._constraint_readiness_snapshot(s)
            return {
                "status": "error",
                "detail": "Internal error during deferred constraint application",
                "changes": applied,
                "pending_actions_user_id_not_null_enforced": pending_actions_user_id_not_null_enforced,
                **snapshot,
            }
        finally:
            s.close()

    def migrate_schema(self) -> dict[str, Any]:
        s = self._get_session()
        applied: list[str] = []
        pending_actions_null_rows: int | None = None
        pending_actions_user_id_not_null_enforced = False
        pending_actions_user_id_not_null_blocked = False
        auth_owner_orphans: int | None = None
        duplicate_profiles: int | None = None
        try:
            dialect = self._dialect_name(s)
            consent_table = Consent.__tablename__
            self._prepare_outbox_lease_schema(s, dialect=dialect, applied=applied)
            self._prepare_chat_stream_ledger_schema(s, dialect=dialect, applied=applied)
            self._prepare_chat_study_schema(s, dialect=dialect, applied=applied)
            self._prepare_chat_rest_idempotency_schema(
                s,
                dialect=dialect,
                applied=applied,
            )
            self._migrate_seeded_agent_configs_to_cloud(s, applied)
            if dialect in ("postgresql", "postgres"):
                # One additive transaction: a failed identity/ownership backfill leaves the
                # pre-existing schema usable and never deletes or selects duplicate records.
                try:
                    s.execute(
                        text(
                            """
                            CREATE TABLE IF NOT EXISTS external_identities (
                                id SERIAL PRIMARY KEY,
                                issuer VARCHAR(512) NOT NULL,
                                subject VARCHAR(255) NOT NULL,
                                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                email_at_link VARCHAR(255) NULL,
                                email_verified BOOLEAN NOT NULL DEFAULT FALSE,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT unique_external_identity UNIQUE (issuer, subject)
                            );
                            CREATE INDEX IF NOT EXISTS idx_external_identity_user
                                ON external_identities (user_id);
                            CREATE TABLE IF NOT EXISTS external_identity_events (
                                id SERIAL PRIMARY KEY,
                                identity_id INTEGER NOT NULL REFERENCES external_identities(id) ON DELETE CASCADE,
                                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                event_type VARCHAR(50) NOT NULL,
                                admin_group_authorized BOOLEAN NOT NULL DEFAULT FALSE,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            );
                            CREATE INDEX IF NOT EXISTS idx_external_identity_event_user
                                ON external_identity_events (user_id, created_at);
                            CREATE TABLE IF NOT EXISTS service_principals (
                                id SERIAL PRIMARY KEY,
                                issuer VARCHAR(512) NOT NULL,
                                subject VARCHAR(255) NOT NULL,
                                client_id VARCHAR(255) NOT NULL,
                                display_name VARCHAR(255) NULL,
                                status VARCHAR(20) NOT NULL DEFAULT 'active',
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT unique_service_principal_subject UNIQUE (issuer, subject),
                                CONSTRAINT unique_service_principal_client UNIQUE (issuer, client_id)
                            );
                            CREATE TABLE IF NOT EXISTS service_principal_scopes (
                                principal_id INTEGER NOT NULL REFERENCES service_principals(id) ON DELETE CASCADE,
                                scope VARCHAR(100) NOT NULL,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                PRIMARY KEY (principal_id, scope)
                            );
                            CREATE TABLE IF NOT EXISTS feedback_entries (
                                id VARCHAR(36) PRIMARY KEY,
                                owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                                conversation_id VARCHAR(100) NOT NULL,
                                message_id VARCHAR(100) NULL,
                                rating VARCHAR(20) NOT NULL,
                                feedback_type VARCHAR(20) NOT NULL,
                                comment TEXT NULL,
                                context_json JSONB NULL,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            );
                            CREATE INDEX IF NOT EXISTS idx_feedback_owner_created
                                ON feedback_entries (owner_user_id, created_at);
                            CREATE INDEX IF NOT EXISTS idx_feedback_owner_conversation
                                ON feedback_entries (owner_user_id, conversation_id, created_at);
                            CREATE TABLE IF NOT EXISTS admin_delegations (
                                id VARCHAR(36) PRIMARY KEY,
                                human_issuer VARCHAR(512) NOT NULL,
                                human_subject VARCHAR(255) NOT NULL,
                                service_client_id VARCHAR(255) NOT NULL,
                                operation_id VARCHAR(255) NOT NULL,
                                resource_id VARCHAR(255) NULL,
                                result_status INTEGER NULL,
                                trace_id VARCHAR(64) NOT NULL,
                                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            );
                            CREATE INDEX IF NOT EXISTS idx_admin_delegation_trace
                                ON admin_delegations (trace_id, created_at);
                            CREATE TABLE IF NOT EXISTS auth_migration_quarantine (
                                resource_type VARCHAR(64) NOT NULL,
                                resource_id VARCHAR(255) NOT NULL,
                                reason VARCHAR(255) NOT NULL,
                                detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                resolved_at TIMESTAMP NULL,
                                PRIMARY KEY (resource_type, resource_id)
                            )
                            """
                        )
                    )
                    applied.extend(
                        [
                            "external_identities.table",
                            "service_principals.tables",
                            "feedback_entries.table",
                            "admin_delegations.table",
                            "auth_migration_quarantine.table",
                        ]
                    )
                    if self._table_exists(s, "experiments") and not self._column_exists(
                        s, "experiments", "owner_user_id"
                    ):
                        s.execute(text("ALTER TABLE experiments ADD COLUMN owner_user_id INTEGER NULL"))
                        applied.append("experiments.owner_user_id")
                    if self._table_exists(s, "experiments"):
                        s.execute(
                            text(
                                """
                                UPDATE experiments e
                                SET owner_user_id = e.user_id::INTEGER
                                FROM users u
                                WHERE e.owner_user_id IS NULL
                                  AND e.user_id ~ '^[0-9]+$'
                                  AND u.id = e.user_id::INTEGER
                                """
                            )
                        )
                        owner_result = s.execute(
                            text("SELECT COUNT(*) FROM experiments WHERE owner_user_id IS NULL")
                        )
                        auth_owner_orphans = int(
                            getattr(owner_result, "scalar", lambda: 0)() or 0
                        )
                        s.execute(
                            text(
                                """
                                INSERT INTO auth_migration_quarantine(resource_type, resource_id, reason)
                                SELECT 'experiment', id::TEXT, 'owner_user_id could not be backfilled'
                                FROM experiments WHERE owner_user_id IS NULL
                                ON CONFLICT (resource_type, resource_id) DO UPDATE
                                SET reason = EXCLUDED.reason, detected_at = CURRENT_TIMESTAMP,
                                    resolved_at = NULL
                                """
                            )
                        )
                        s.execute(
                            text(
                                "CREATE INDEX IF NOT EXISTS idx_experiment_owner_status "
                                "ON experiments (owner_user_id, status)"
                            )
                        )
                        if auth_owner_orphans == 0:
                            s.execute(
                                text(
                                    "UPDATE auth_migration_quarantine SET resolved_at = CURRENT_TIMESTAMP "
                                    "WHERE resource_type = 'experiment' AND resolved_at IS NULL"
                                )
                            )
                            if not self._constraint_exists(
                                s, "experiments", "fk_experiments_owner_user"
                            ):
                                s.execute(
                                    text(
                                        "ALTER TABLE experiments ADD CONSTRAINT "
                                        "fk_experiments_owner_user FOREIGN KEY (owner_user_id) "
                                        "REFERENCES users(id) ON DELETE RESTRICT"
                                    )
                                )
                                applied.append("experiments.owner_user_fk")
                            s.execute(
                                text(
                                    "ALTER TABLE experiments ALTER COLUMN owner_user_id SET NOT NULL"
                                )
                            )
                            applied.append("experiments.owner_user_not_null")
                    if self._table_exists(s, "profiles"):
                        duplicate_result = s.execute(
                            text(
                                "SELECT COUNT(*) FROM (SELECT user_id FROM profiles "
                                "GROUP BY user_id HAVING COUNT(*) > 1) duplicates"
                            )
                        )
                        duplicate_profiles = int(
                            getattr(duplicate_result, "scalar", lambda: 0)() or 0
                        )
                        s.execute(
                            text(
                                """
                                INSERT INTO auth_migration_quarantine(resource_type, resource_id, reason)
                                SELECT 'profile', user_id::TEXT, 'multiple profiles for one user'
                                FROM profiles GROUP BY user_id HAVING COUNT(*) > 1
                                ON CONFLICT (resource_type, resource_id) DO UPDATE
                                SET reason = EXCLUDED.reason, detected_at = CURRENT_TIMESTAMP,
                                    resolved_at = NULL
                                """
                            )
                        )
                        if duplicate_profiles == 0:
                            s.execute(
                                text(
                                    "UPDATE auth_migration_quarantine SET resolved_at = CURRENT_TIMESTAMP "
                                    "WHERE resource_type = 'profile' AND resolved_at IS NULL"
                                )
                            )
                            s.execute(
                                text(
                                    "CREATE UNIQUE INDEX IF NOT EXISTS unique_profile_user "
                                    "ON profiles (user_id)"
                                )
                            )
                            applied.append("profiles.unique_user")
                    commit = getattr(s, "commit", None)
                    if callable(commit):
                        commit()
                except Exception:
                    rollback = getattr(s, "rollback", None)
                    if callable(rollback):
                        rollback()
                    raise
            if not self._index_exists(s, "users", "idx_user_lookup"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_user_lookup ON users (email)",
                    "users.idx_user_lookup",
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
            if not self._column_exists(s, "pending_actions", "simulation_summary_json"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE pending_actions ADD COLUMN simulation_summary_json TEXT NULL",
                    "pending_actions.simulation_summary_json",
                    applied,
                )
            if not self._column_exists(s, "pending_actions", "user_id"):
                self._execute_ddl(
                    s,
                    "ALTER TABLE pending_actions ADD COLUMN user_id VARCHAR(128) NULL",
                    "pending_actions.user_id",
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
            if not self._index_exists(s, "pending_actions", "idx_pending_actions_status_user"):
                self._execute_ddl(
                    s,
                    "CREATE INDEX idx_pending_actions_status_user ON pending_actions (status, user_id)",
                    "pending_actions.idx_pending_actions_status_user",
                    applied,
                )
            self._backfill_pending_action_user_ids(s, applied)
            pending_actions_null_rows = self._count_null_pending_action_user_ids(s)
            pending_actions_user_id_nullable = self._column_nullable(s, "pending_actions", "user_id")
            if pending_actions_user_id_nullable is False:
                pending_actions_user_id_not_null_enforced = True
            elif pending_actions_null_rows == 0:
                not_null_sql = self._pending_action_user_id_not_null_sql(dialect=dialect)
                if not_null_sql:
                    self._execute_ddl(
                        s,
                        not_null_sql,
                        "pending_actions.user_id_not_null",
                        applied,
                    )
                    pending_actions_user_id_not_null_enforced = True
                else:
                    logger.warning(
                        "pending_actions_user_id_not_null_sql_unsupported",
                        dialect=dialect,
                    )
            elif pending_actions_null_rows and pending_actions_null_rows > 0:
                pending_actions_user_id_not_null_blocked = True
                logger.warning(
                    "pending_actions_user_id_not_null_blocked",
                    remaining_without_owner=pending_actions_null_rows,
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
            # Audit ledger (append-only)
            if dialect in ("postgresql", "postgres"):
                if not self._table_exists(s, "audit_ledger_events"):
                    try:
                        s.execute(
                            text(
                                """
                                CREATE TABLE IF NOT EXISTS audit_ledger_events (
                                    id SERIAL PRIMARY KEY,
                                    actor_user_id INTEGER NULL,
                                    endpoint VARCHAR(200) NOT NULL,
                                    action VARCHAR(100) NOT NULL,
                                    tool VARCHAR(100) NULL,
                                    status VARCHAR(20) NOT NULL,
                                    trace_id VARCHAR(64) NULL,
                                    payload_json JSONB NULL,
                                    prev_hash VARCHAR(64) NULL,
                                    entry_hash VARCHAR(64) NOT NULL,
                                    signature VARCHAR(64) NOT NULL,
                                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                )
                                """
                            )
                        )
                        applied.append("audit_ledger_events.table")
                    except Exception:
                        pass
                for idx_sql, idx_id in (
                    (
                        "CREATE INDEX IF NOT EXISTS idx_audit_ledger_ts ON audit_ledger_events (created_at)",
                        "audit_ledger_events.idx_ts",
                    ),
                    (
                        "CREATE INDEX IF NOT EXISTS idx_audit_ledger_trace ON audit_ledger_events (trace_id)",
                        "audit_ledger_events.idx_trace",
                    ),
                    (
                        "CREATE INDEX IF NOT EXISTS idx_audit_ledger_actor ON audit_ledger_events (actor_user_id, created_at)",
                        "audit_ledger_events.idx_actor",
                    ),
                    (
                        "CREATE INDEX IF NOT EXISTS idx_audit_ledger_action ON audit_ledger_events (action, created_at)",
                        "audit_ledger_events.idx_action",
                    ),
                ):
                    try:
                        s.execute(text(idx_sql))
                        applied.append(idx_id)
                    except Exception:
                        pass
                try:
                    s.execute(
                        text(
                            """
                            CREATE OR REPLACE FUNCTION prevent_audit_ledger_mutation()
                            RETURNS TRIGGER AS $$
                            BEGIN
                                RAISE EXCEPTION 'audit_ledger_events is append-only';
                            END;
                            $$ LANGUAGE plpgsql
                            """
                        )
                    )
                    applied.append("audit_ledger_events.fn_immutable")
                except Exception:
                    pass
                try:
                    s.execute(
                        text(
                            """
                            DO $$
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_audit_ledger_no_update'
                                ) THEN
                                    CREATE TRIGGER trg_audit_ledger_no_update
                                    BEFORE UPDATE ON audit_ledger_events
                                    FOR EACH ROW EXECUTE FUNCTION prevent_audit_ledger_mutation();
                                END IF;
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_audit_ledger_no_delete'
                                ) THEN
                                    CREATE TRIGGER trg_audit_ledger_no_delete
                                    BEFORE DELETE ON audit_ledger_events
                                    FOR EACH ROW EXECUTE FUNCTION prevent_audit_ledger_mutation();
                                END IF;
                            END $$;
                            """
                        )
                    )
                    applied.append("audit_ledger_events.triggers_immutable")
                except Exception:
                    pass
                if not self._table_exists(s, "data_governance_records"):
                    try:
                        s.execute(
                            text(
                                """
                                CREATE TABLE IF NOT EXISTS data_governance_records (
                                    id SERIAL PRIMARY KEY,
                                    user_id INTEGER NULL,
                                    resource_type VARCHAR(64) NOT NULL,
                                    resource_id VARCHAR(255) NOT NULL,
                                    classification VARCHAR(16) NOT NULL,
                                    classification_source VARCHAR(16) NOT NULL,
                                    retention_policy VARCHAR(32) NOT NULL,
                                    retention_days INTEGER NULL,
                                    retention_until TIMESTAMP NULL,
                                    metadata_json JSONB NULL,
                                    purge_job_id VARCHAR(64) NULL,
                                    purged_at TIMESTAMP NULL,
                                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                )
                                """
                            )
                        )
                        applied.append("data_governance_records.table")
                    except Exception:
                        pass
                for idx_sql, idx_id in (
                    (
                        "CREATE INDEX IF NOT EXISTS idx_data_gov_resource ON data_governance_records (resource_type, resource_id)",
                        "data_governance_records.idx_resource",
                    ),
                    (
                        "CREATE INDEX IF NOT EXISTS idx_data_gov_user ON data_governance_records (user_id, resource_type)",
                        "data_governance_records.idx_user",
                    ),
                    (
                        "CREATE INDEX IF NOT EXISTS idx_data_gov_retention ON data_governance_records (retention_until, purged_at)",
                        "data_governance_records.idx_retention",
                    ),
                ):
                    try:
                        s.execute(text(idx_sql))
                        applied.append(idx_id)
                    except Exception:
                        pass
            try:
                s.commit()
            except Exception:
                pass
            return {
                "status": "applied",
                "changes": applied,
                "pending_actions_user_id_null_rows": pending_actions_null_rows,
                "pending_actions_user_id_not_null_enforced": pending_actions_user_id_not_null_enforced,
                "pending_actions_user_id_not_null_blocked": pending_actions_user_id_not_null_blocked,
                "auth_owner_orphans": auth_owner_orphans,
                "duplicate_profiles": duplicate_profiles,
            }
        except Exception as e:
            logger.error("DB migration failed", exc_info=e)
            return {
                "status": "error",
                "detail": "Internal error during migration",
                "changes": applied,
                "pending_actions_user_id_null_rows": pending_actions_null_rows,
                "pending_actions_user_id_not_null_enforced": pending_actions_user_id_not_null_enforced,
                "pending_actions_user_id_not_null_blocked": pending_actions_user_id_not_null_blocked,
                "auth_owner_orphans": auth_owner_orphans,
                "duplicate_profiles": duplicate_profiles,
            }
        finally:
            s.close()


db_migration_service = DBMigrationService()
