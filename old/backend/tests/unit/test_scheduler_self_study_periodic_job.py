import sys
import types

import pytest
from app.services.scheduler_service import (
    SchedulerService,
    ScheduleType,
    initialize_default_jobs,
)


def _install_dependency_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stubs every module lazily imported by initialize_default_jobs so that
    registering the default jobs never touches real infra."""
    meta_agent_module = types.ModuleType("app.core.agents.meta_agent")
    meta_agent_module.get_meta_agent = lambda: types.SimpleNamespace(
        run_analysis_cycle=lambda trigger: trigger
    )
    monkeypatch.setitem(sys.modules, "app.core.agents.meta_agent", meta_agent_module)

    memory_core_module = types.ModuleType("app.core.memory.memory_core")

    async def _get_memory_db():
        return types.SimpleNamespace(health_check=lambda: {"ok": True})

    memory_core_module.get_memory_db = _get_memory_db
    monkeypatch.setitem(sys.modules, "app.core.memory.memory_core", memory_core_module)

    logging_config_module = types.ModuleType("app.core.infrastructure.logging_config")
    logging_config_module.cleanup_rotated_log_files = lambda *_a, **_k: {"removed": 0, "scanned": 0}
    monkeypatch.setitem(sys.modules, "app.core.infrastructure.logging_config", logging_config_module)

    audit_ledger_repo_module = types.ModuleType("app.repositories.audit_ledger_repository")
    audit_ledger_repo_module.audit_ledger_repository = types.SimpleNamespace(
        verify_integrity=lambda **_k: {"ok": True, "errors": []}
    )
    monkeypatch.setitem(sys.modules, "app.repositories.audit_ledger_repository", audit_ledger_repo_module)

    data_purge_service_module = types.ModuleType("app.services.data_purge_service")

    async def _run_expired_purge(**_k):
        return {"ok": True, "purged": 0}

    data_purge_service_module.data_purge_service = types.SimpleNamespace(
        run_expired_purge=_run_expired_purge
    )
    monkeypatch.setitem(sys.modules, "app.services.data_purge_service", data_purge_service_module)

    secret_key_rotation_service_module = types.ModuleType("app.services.secret_key_rotation_service")

    async def _reencrypt_batch(**_k):
        return {"ok": True}

    secret_key_rotation_service_module.secret_key_rotation_service = types.SimpleNamespace(
        reencrypt_batch=_reencrypt_batch
    )
    monkeypatch.setitem(
        sys.modules, "app.services.secret_key_rotation_service", secret_key_rotation_service_module
    )


@pytest.mark.asyncio
async def test_self_study_periodic_job_registered_with_settings_interval(monkeypatch):
    import app.services.scheduler_service as scheduler_module

    _install_dependency_stubs(monkeypatch)
    monkeypatch.setattr(scheduler_module.settings, "AUTONOMY_SELF_STUDY_PERIODIC_INTERVAL_SECONDS", 7200)
    monkeypatch.setattr(scheduler_module.settings, "AUTONOMY_SELF_STUDY_PERIODIC_ENABLED", True)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    job = scheduler.get_job("self_study_periodic")
    assert job is not None
    assert job.schedule_type == ScheduleType.INTERVAL
    assert job.interval_seconds == 7200
    assert job.enabled is True


@pytest.mark.asyncio
async def test_self_study_periodic_job_respects_disabled_flag(monkeypatch):
    import app.services.scheduler_service as scheduler_module

    _install_dependency_stubs(monkeypatch)
    monkeypatch.setattr(scheduler_module.settings, "AUTONOMY_SELF_STUDY_PERIODIC_ENABLED", False)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    job = scheduler.get_job("self_study_periodic")
    assert job is not None
    assert job.enabled is False


@pytest.mark.asyncio
async def test_self_study_periodic_job_delegates_to_autonomy_admin_service(monkeypatch):
    import app.services.scheduler_service as scheduler_module

    _install_dependency_stubs(monkeypatch)

    kernel_module = types.ModuleType("app.core.kernel")
    fake_kernel = types.SimpleNamespace(
        llm_service="llm", knowledge_service="knowledge", goal_manager="goals"
    )
    kernel_module.Kernel = types.SimpleNamespace(get_instance=lambda: fake_kernel)
    monkeypatch.setitem(sys.modules, "app.core.kernel", kernel_module)

    run_calls: list[dict] = []

    class _FakeAutonomyAdminService:
        def __init__(self, *, llm_service, knowledge_service, goal_manager):
            assert llm_service == "llm"
            assert knowledge_service == "knowledge"
            assert goal_manager == "goals"

        async def run_self_study(self, *, mode, reason, trigger_type):
            run_calls.append({"mode": mode, "reason": reason, "trigger_type": trigger_type})
            return {"status": "completed", "files_processed": 3, "errors": 0, "proposed_goal_id": None}

    autonomy_admin_service_module = types.ModuleType("app.services.autonomy_admin_service")
    autonomy_admin_service_module.AutonomyAdminService = _FakeAutonomyAdminService
    monkeypatch.setitem(sys.modules, "app.services.autonomy_admin_service", autonomy_admin_service_module)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    job = scheduler.get_job("self_study_periodic")
    await job.callback()

    assert run_calls == [
        {"mode": "incremental", "reason": "scheduled_periodic", "trigger_type": "scheduled"}
    ]


@pytest.mark.asyncio
async def test_self_study_periodic_job_swallows_failures(monkeypatch):
    import app.services.scheduler_service as scheduler_module

    _install_dependency_stubs(monkeypatch)

    kernel_module = types.ModuleType("app.core.kernel")
    kernel_module.Kernel = types.SimpleNamespace(
        get_instance=lambda: (_ for _ in ()).throw(RuntimeError("kernel unavailable"))
    )
    monkeypatch.setitem(sys.modules, "app.core.kernel", kernel_module)

    scheduler = SchedulerService()
    await initialize_default_jobs(scheduler)

    job = scheduler.get_job("self_study_periodic")
    # Must not raise: scheduler jobs run unattended and failures are logged, not propagated.
    await job.callback()
