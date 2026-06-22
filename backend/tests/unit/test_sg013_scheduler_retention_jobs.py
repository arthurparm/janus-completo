import os
import sys
import types

import pytest
from app.services.scheduler_service import (
    SchedulerService,
    ScheduleType,
    initialize_default_jobs,
)


def _install_dependency_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cleanup_calls: list[tuple[str, int]],
    integrity_calls: list[int],
    audit_record_calls: list[dict[str, object]],
    purge_limits: list[int],
) -> None:
    meta_agent_module = types.ModuleType("app.core.agents.meta_agent")

    class _FakeMetaAgent:
        async def run_analysis_cycle(self, trigger):  # pragma: no cover - defensive only
            return trigger

    def _get_meta_agent():
        return _FakeMetaAgent()

    meta_agent_module.get_meta_agent = _get_meta_agent
    monkeypatch.setitem(sys.modules, "app.core.agents.meta_agent", meta_agent_module)

    memory_core_module = types.ModuleType("app.core.memory.memory_core")

    async def _get_memory_db():
        class _FakeMemory:
            def health_check(self):
                return {"ok": True}

        return _FakeMemory()

    memory_core_module.get_memory_db = _get_memory_db
    monkeypatch.setitem(sys.modules, "app.core.memory.memory_core", memory_core_module)

    monitoring_module = types.ModuleType("app.core.monitoring")
    monitoring_module.get_health_monitor = lambda: object()
    monkeypatch.setitem(sys.modules, "app.core.monitoring", monitoring_module)

    poison_module = types.ModuleType("app.core.monitoring.poison_pill_handler")
    poison_module.get_poison_pill_handler = lambda: object()
    monkeypatch.setitem(sys.modules, "app.core.monitoring.poison_pill_handler", poison_module)

    observability_repo_module = types.ModuleType("app.repositories.observability_repository")

    class _FakeObservabilityRepository:
        def __init__(self, *_args, **_kwargs):
            pass

    def _record_audit_event_direct(**kwargs):
        audit_record_calls.append(dict(kwargs))

    observability_repo_module.ObservabilityRepository = _FakeObservabilityRepository
    observability_repo_module.record_audit_event_direct = _record_audit_event_direct
    monkeypatch.setitem(sys.modules, "app.repositories.observability_repository", observability_repo_module)

    observability_service_module = types.ModuleType("app.services.observability_service")

    class _FakeObservabilityService:
        def __init__(self, _repo):
            self._repo = _repo

    observability_service_module.ObservabilityService = _FakeObservabilityService
    monkeypatch.setitem(sys.modules, "app.services.observability_service", observability_service_module)

    logging_config_module = types.ModuleType("app.core.infrastructure.logging_config")

    def _cleanup_rotated_log_files(log_file: str, retention_days: int):
        cleanup_calls.append((log_file, retention_days))
        return {"removed": 1, "scanned": 2}

    logging_config_module.cleanup_rotated_log_files = _cleanup_rotated_log_files
    monkeypatch.setitem(sys.modules, "app.core.infrastructure.logging_config", logging_config_module)

    audit_ledger_repo_module = types.ModuleType("app.repositories.audit_ledger_repository")

    class _FakeAuditLedgerRepository:
        def verify_integrity(self, *, max_errors: int = 25):
            integrity_calls.append(max_errors)
            return {"ok": True, "errors": []}

    audit_ledger_repo_module.audit_ledger_repository = _FakeAuditLedgerRepository()
    monkeypatch.setitem(sys.modules, "app.repositories.audit_ledger_repository", audit_ledger_repo_module)

    data_purge_service_module = types.ModuleType("app.services.data_purge_service")

    class _FakeDataPurgeService:
        async def run_expired_purge(self, *, limit: int = 250):
            purge_limits.append(limit)
            return {"ok": True, "purged": 0}

    data_purge_service_module.data_purge_service = _FakeDataPurgeService()
    monkeypatch.setitem(sys.modules, "app.services.data_purge_service", data_purge_service_module)

    secret_key_rotation_service_module = types.ModuleType("app.services.secret_key_rotation_service")

    class _FakeSecretKeyRotationService:
        async def reencrypt_batch(self, *, limit: int = 100, active_only: bool = True):
            return {"ok": True, "processed": 0, "active_only": active_only, "limit": limit}

    secret_key_rotation_service_module.secret_key_rotation_service = _FakeSecretKeyRotationService()
    monkeypatch.setitem(
        sys.modules,
        "app.services.secret_key_rotation_service",
        secret_key_rotation_service_module,
    )


@pytest.mark.asyncio
async def test_initialize_default_jobs_registers_sg013_jobs(monkeypatch: pytest.MonkeyPatch):
    import app.services.scheduler_service as scheduler_module

    cleanup_calls: list[tuple[str, int]] = []
    integrity_calls: list[int] = []
    audit_record_calls: list[dict[str, object]] = []
    purge_limits: list[int] = []
    _install_dependency_stubs(
        monkeypatch,
        cleanup_calls=cleanup_calls,
        integrity_calls=integrity_calls,
        audit_record_calls=audit_record_calls,
        purge_limits=purge_limits,
    )

    monkeypatch.setattr(scheduler_module.settings, "AUDIT_LEDGER_INTEGRITY_CHECK_INTERVAL_SECONDS", 30)
    monkeypatch.setattr(scheduler_module.settings, "DATA_PURGE_INTERVAL_SECONDS", 10)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    daily_job = scheduler.get_job("daily_cleanup")
    assert daily_job is not None
    assert daily_job.schedule_type == ScheduleType.DAILY
    assert daily_job.hour == 3
    assert daily_job.minute == 0

    integrity_job = scheduler.get_job("audit_ledger_integrity_check")
    assert integrity_job is not None
    assert integrity_job.schedule_type == ScheduleType.INTERVAL
    assert integrity_job.interval_seconds == 60

    purge_job = scheduler.get_job("data_purge_job")
    assert purge_job is not None
    assert purge_job.schedule_type == ScheduleType.INTERVAL
    assert purge_job.interval_seconds == 300


@pytest.mark.asyncio
async def test_sg013_jobs_apply_retention_settings(monkeypatch: pytest.MonkeyPatch):
    import app.services.scheduler_service as scheduler_module

    cleanup_calls: list[tuple[str, int]] = []
    integrity_calls: list[int] = []
    audit_record_calls: list[dict[str, object]] = []
    purge_limits: list[int] = []
    _install_dependency_stubs(
        monkeypatch,
        cleanup_calls=cleanup_calls,
        integrity_calls=integrity_calls,
        audit_record_calls=audit_record_calls,
        purge_limits=purge_limits,
    )

    monkeypatch.setattr(scheduler_module.settings, "LOG_FILE_RETENTION_DAYS", 9)
    monkeypatch.setattr(scheduler_module.settings, "AUDIT_LEDGER_INTEGRITY_CHECK_INTERVAL_SECONDS", 65)
    monkeypatch.setattr(scheduler_module.settings, "DATA_PURGE_INTERVAL_SECONDS", 400)
    monkeypatch.setattr(scheduler_module.settings, "DATA_PURGE_BATCH_LIMIT", 42)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    await scheduler.get_job("daily_cleanup").callback()  # type: ignore[union-attr]
    await scheduler.get_job("audit_ledger_integrity_check").callback()  # type: ignore[union-attr]
    await scheduler.get_job("data_purge_job").callback()  # type: ignore[union-attr]

    assert len(cleanup_calls) == 2
    assert all(retention == 9 for _, retention in cleanup_calls)
    assert sorted(os.path.basename(path) for path, _ in cleanup_calls) == [
        "janus-errors.log",
        "janus.log",
    ]
    assert integrity_calls == [25]
    assert audit_record_calls == []
    assert purge_limits == [42]

    integrity_job = scheduler.get_job("audit_ledger_integrity_check")
    assert integrity_job is not None
    assert integrity_job.interval_seconds == 65

    purge_job = scheduler.get_job("data_purge_job")
    assert purge_job is not None
    assert purge_job.interval_seconds == 400
