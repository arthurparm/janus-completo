import os
import sys
from types import SimpleNamespace

sys.path.append(os.path.join(os.getcwd(), "backend"))

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


def test_migrate_schema_uses_postgres_sql_and_consent_table(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    _force_all_missing(monkeypatch, svc)

    result = svc.migrate_schema()

    assert result["status"] == "applied"
    assert any("ALTER TABLE users ADD CONSTRAINT unique_user_email UNIQUE (email)" in q for q in fake.executed_sql)
    assert any("ALTER TABLE users ADD CONSTRAINT unique_user_cpf_hash UNIQUE (cpf_hash)" in q for q in fake.executed_sql)
    assert all("UNIQUE KEY" not in q for q in fake.executed_sql)
    assert any("ALTER TABLE user_privacy_consents ADD CONSTRAINT unique_user_privacy_scope_consent UNIQUE (user_id, scope)" in q for q in fake.executed_sql)
    assert any("CREATE INDEX idx_privacy_consent_user_scope ON user_privacy_consents (user_id, scope)" in q for q in fake.executed_sql)
    assert any("CREATE TABLE IF NOT EXISTS audit_ledger_events" in q for q in fake.executed_sql)
    assert any("CREATE TABLE IF NOT EXISTS data_governance_records" in q for q in fake.executed_sql)
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


def test_migrate_schema_promotes_pending_actions_user_id_not_null_when_residue_zero(monkeypatch):
    svc = DBMigrationService()
    fake = _FakeSession("postgresql")
    monkeypatch.setattr(svc, "_get_session", lambda: fake)
    monkeypatch.setattr(svc, "_index_exists", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(svc, "_constraint_exists", lambda *_args, **_kwargs: True)
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
