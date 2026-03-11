import sys
import types

import pytest

from app.services.scheduler_service import ScheduleType, SchedulerService, initialize_default_jobs


def _install_dependency_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    cleanup_calls: list[tuple[str, int]],
    purge_calls: list[int],
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

    observability_repo_module.ObservabilityRepository = _FakeObservabilityRepository
    monkeypatch.setitem(sys.modules, "app.repositories.observability_repository", observability_repo_module)

    observability_service_module = types.ModuleType("app.services.observability_service")

    class _FakeObservabilityService:
        def __init__(self, _repo):
            self._repo = _repo

        def purge_old_audit_events(self, retention_days: int):
            purge_calls.append(retention_days)
            return {"removed": 7, "retention_days": retention_days}

    observability_service_module.ObservabilityService = _FakeObservabilityService
    monkeypatch.setitem(sys.modules, "app.services.observability_service", observability_service_module)

    logging_config_module = types.ModuleType("app.core.infrastructure.logging_config")

    def _cleanup_rotated_log_files(log_file: str, retention_days: int):
        cleanup_calls.append((log_file, retention_days))
        return {"removed": 1, "scanned": 2}

    logging_config_module.cleanup_rotated_log_files = _cleanup_rotated_log_files
    monkeypatch.setitem(sys.modules, "app.core.infrastructure.logging_config", logging_config_module)


@pytest.mark.asyncio
async def test_initialize_default_jobs_registers_sg013_jobs(monkeypatch: pytest.MonkeyPatch):
    import app.services.scheduler_service as scheduler_module

    cleanup_calls: list[tuple[str, int]] = []
    purge_calls: list[int] = []
    _install_dependency_stubs(monkeypatch, cleanup_calls=cleanup_calls, purge_calls=purge_calls)

    monkeypatch.setattr(scheduler_module.settings, "AUDIT_PURGE_INTERVAL_SECONDS", 1800)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    daily_job = scheduler.get_job("daily_cleanup")
    assert daily_job is not None
    assert daily_job.schedule_type == ScheduleType.DAILY
    assert daily_job.hour == 3
    assert daily_job.minute == 0

    audit_job = scheduler.get_job("audit_retention_cleanup")
    assert audit_job is not None
    assert audit_job.schedule_type == ScheduleType.INTERVAL
    assert audit_job.interval_seconds == 1800


@pytest.mark.asyncio
async def test_sg013_jobs_apply_retention_settings(monkeypatch: pytest.MonkeyPatch):
    import app.services.scheduler_service as scheduler_module

    cleanup_calls: list[tuple[str, int]] = []
    purge_calls: list[int] = []
    _install_dependency_stubs(monkeypatch, cleanup_calls=cleanup_calls, purge_calls=purge_calls)

    monkeypatch.setattr(scheduler_module.settings, "LOG_FILE_RETENTION_DAYS", 9)
    monkeypatch.setattr(scheduler_module.settings, "AUDIT_RETENTION_DAYS", 45)
    monkeypatch.setattr(scheduler_module.settings, "AUDIT_PURGE_INTERVAL_SECONDS", 30)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    await scheduler.get_job("daily_cleanup").callback()  # type: ignore[union-attr]
    await scheduler.get_job("audit_retention_cleanup").callback()  # type: ignore[union-attr]

    assert len(cleanup_calls) == 2
    assert all(retention == 9 for _, retention in cleanup_calls)
    assert sorted(path.split("/")[-1] for path, _ in cleanup_calls) == ["janus-errors.log", "janus.log"]
    assert purge_calls == [45]

    audit_job = scheduler.get_job("audit_retention_cleanup")
    assert audit_job is not None
    assert audit_job.interval_seconds == 60
