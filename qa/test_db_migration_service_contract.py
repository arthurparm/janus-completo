from types import SimpleNamespace

import app.services.db_migration_service as migration_module
from app.services.db_migration_service import DBMigrationService


class _FakeSession:
    def __init__(self, dialect_name: str):
        self._dialect_name = dialect_name
        self.executed_sql: list[str] = []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self._dialect_name))

    def execute(self, stmt):
        self.executed_sql.append(str(stmt))

    def close(self):
        return None


def _force_all_missing(monkeypatch, svc: DBMigrationService) -> None:
    monkeypatch.setattr(svc, "_index_exists", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(svc, "_constraint_exists", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args, **_kwargs: False)


def test_constraint_exists_detects_named_foreign_key(monkeypatch):
    inspector = SimpleNamespace(
        get_unique_constraints=lambda _table: [],
        get_foreign_keys=lambda _table: [{"name": "fk_experiments_owner_user"}],
    )
    monkeypatch.setattr(migration_module, "inspect", lambda _bind: inspector)

    service = DBMigrationService()
    session = _FakeSession("postgresql")

    assert service._constraint_exists(
        session, "experiments", "fk_experiments_owner_user"
    )


def test_migrate_schema_uses_postgres_sql_and_consent_table(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    _force_all_missing(monkeypatch, svc)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert any("ALTER TABLE users ADD CONSTRAINT unique_user_email UNIQUE (email)" in q for q in fake.executed_sql)
    assert all("UNIQUE KEY" not in q for q in fake.executed_sql)
    assert any("ALTER TABLE user_privacy_consents ADD CONSTRAINT unique_user_privacy_scope_consent UNIQUE (user_id, scope)" in q for q in fake.executed_sql)
    assert any("CREATE INDEX idx_privacy_consent_user_scope ON user_privacy_consents (user_id, scope)" in q for q in fake.executed_sql)
    assert any("CREATE TABLE IF NOT EXISTS audit_ledger_events" in q for q in fake.executed_sql)
    assert any("CREATE TABLE IF NOT EXISTS data_governance_records" in q for q in fake.executed_sql)
    assert any("CREATE TABLE chat_stream_runs" in q for q in fake.executed_sql)
    assert any("CREATE TABLE chat_stream_events" in q for q in fake.executed_sql)
    assert any("CREATE TABLE chat_study_runs" in q for q in fake.executed_sql)
    assert any("CREATE TABLE chat_rest_runs" in q for q in fake.executed_sql)
    assert all("audit_events" not in q for q in fake.executed_sql)


def test_migrate_schema_uses_mysql_specific_unique_key_and_text_json(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("mysql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    _force_all_missing(monkeypatch, svc)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert any("UNIQUE KEY" in q for q in fake.executed_sql)
    assert all("audit_events" not in q for q in fake.executed_sql)


def test_validate_schema_checks_consent_table_with_model_names(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)

    constraint_calls: list[tuple[str, str]] = []
    index_calls: list[tuple[str, str]] = []

    def _constraint(_s, table: str, name: str) -> bool:
        constraint_calls.append((table, name))
        return True

    def _index(_s, table: str, name: str) -> bool:
        index_calls.append((table, name))
        return True

    monkeypatch.setattr(svc, "_constraint_exists", _constraint)
    monkeypatch.setattr(svc, "_index_exists", _index)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_column_nullable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(svc, "_count_null_pending_action_user_ids", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(svc, "_table_exists", lambda *_args, **_kwargs: True)

    result = svc.validate_schema()

    assert result["status"] == "ok"
    assert ("user_privacy_consents", "unique_user_privacy_scope_consent") in constraint_calls
    assert ("user_privacy_consents", "idx_privacy_consent_user_scope") in index_calls
    assert (
        "chat_stream_runs",
        "uq_chat_stream_owner_session_request",
    ) in constraint_calls
    assert ("chat_stream_events", "idx_chat_stream_event_cursor") in index_calls


def test_migrate_schema_promotes_pending_actions_user_id_not_null_when_residue_zero(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        svc,
        "_constraint_exists",
        lambda _s, _table, name: name != "fk_experiments_owner_user",
    )
    monkeypatch.setattr(svc, "_column_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_table_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_backfill_pending_action_user_ids", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_count_null_pending_action_user_ids", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(svc, "_column_nullable", lambda *_args, **_kwargs: True)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert result["pending_actions_user_id_null_rows"] == 0
    assert result["pending_actions_user_id_not_null_enforced"] is True
    assert result["pending_actions_user_id_not_null_blocked"] is False
    assert any(
        "ALTER TABLE pending_actions ALTER COLUMN user_id SET NOT NULL" in q
        for q in fake.executed_sql
    )
    assert any(
        "fk_experiments_owner_user FOREIGN KEY (owner_user_id)" in q
        for q in fake.executed_sql
    )
    assert any(
        "ALTER TABLE experiments ALTER COLUMN owner_user_id SET NOT NULL" in q
        for q in fake.executed_sql
    )


def test_migrate_schema_reports_blocker_when_ownerless_rows_remain(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_constraint_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_table_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_backfill_pending_action_user_ids", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(svc, "_count_null_pending_action_user_ids", lambda *_args, **_kwargs: 3)
    monkeypatch.setattr(svc, "_column_nullable", lambda *_args, **_kwargs: True)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert result["pending_actions_user_id_null_rows"] == 3
    assert result["pending_actions_user_id_not_null_enforced"] is False
    assert result["pending_actions_user_id_not_null_blocked"] is True
    assert all(
        "ALTER TABLE pending_actions ALTER COLUMN user_id SET NOT NULL" not in q
        for q in fake.executed_sql
    )


def test_outbox_lease_migration_is_additive_and_reclaims_legacy_processing(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    applied: list[str] = []
    monkeypatch.setattr(svc, "_table_exists", lambda *_args: True)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args: False)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args: False)
    monkeypatch.setattr(svc, "_column_nullable", lambda *_args: True)

    svc._prepare_outbox_lease_schema(fake, dialect="postgresql", applied=applied)

    sql = "\n".join(fake.executed_sql)
    for column in ("message_id", "claimed_by", "claim_token", "claimed_at", "lease_until"):
        assert f"ALTER TABLE outbox_events ADD COLUMN {column}" in sql
    assert "WHERE status = 'processing' AND lease_until IS NULL" in sql
    assert "CREATE UNIQUE INDEX uq_outbox_message_id" in sql
    assert "CREATE INDEX idx_outbox_status_lease" in sql
    assert "ALTER TABLE outbox_events ALTER COLUMN message_id SET NOT NULL" in sql


def test_chat_stream_ledger_migration_is_owner_scoped_and_cursor_indexed(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    applied: list[str] = []
    monkeypatch.setattr(svc, "_table_exists", lambda *_args: False)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args: False)
    monkeypatch.setattr(svc, "_column_exists", lambda *_args: False)

    svc._prepare_chat_stream_ledger_schema(
        fake,
        dialect="postgresql",
        applied=applied,
    )

    sql = "\n".join(fake.executed_sql)
    assert "owner_user_id INTEGER NOT NULL REFERENCES users(id)" in sql
    assert "session_id INTEGER NOT NULL REFERENCES sessions(id)" in sql
    assert "UNIQUE (owner_user_id, session_id, request_id)" in sql
    assert "UNIQUE (run_id, sequence)" in sql
    assert "CREATE INDEX idx_chat_stream_event_cursor" in sql


def test_chat_study_migration_is_owner_scoped_versioned_and_indexed(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    applied: list[str] = []
    monkeypatch.setattr(svc, "_table_exists", lambda *_args: False)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args: False)

    svc._prepare_chat_study_schema(fake, dialect="postgresql", applied=applied)

    sql = "\n".join(fake.executed_sql)
    assert "owner_user_id VARCHAR(128) NOT NULL" in sql
    assert "version INTEGER NOT NULL DEFAULT 1" in sql
    assert "worker_token VARCHAR(64)" in sql
    assert "lease_until TIMESTAMP" in sql
    assert "UNIQUE (owner_user_id, conversation_id, message_id)" in sql
    assert "CREATE INDEX idx_chat_study_status_lease" in sql


def test_chat_rest_migration_is_scoped_leased_and_retained(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    applied: list[str] = []
    monkeypatch.setattr(svc, "_table_exists", lambda *_args: False)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args: False)

    svc._prepare_chat_rest_idempotency_schema(
        fake,
        dialect="postgresql",
        applied=applied,
    )

    sql = "\n".join(fake.executed_sql)
    assert "UNIQUE (owner_user_id, conversation_id, request_id)" in sql
    assert "producer_token VARCHAR(64)" in sql
    assert "lease_until TIMESTAMP" in sql
    assert "expires_at TIMESTAMP NOT NULL" in sql
    assert "CREATE INDEX idx_chat_rest_status_lease" in sql
