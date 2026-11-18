import sys
from types import ModuleType

import pytest

from app.core.workers import orchestrator
from app.core.workers.orchestrator import DisabledWorkerHandle


class _FakeMemoryWorker:
    def __init__(self):
        self.task = "memory_maintenance_task"

    async def start(self):
        self.task = "memory_maintenance_task"


def _async_starter(value: str):
    async def _starter():
        return value

    return _starter


def _install_worker_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_modules: dict[str, ModuleType] = {}

    monitoring = ModuleType("app.core.monitoring")
    monitoring.start_auto_healer = _async_starter("auto_healer_task")
    fake_modules["app.core.monitoring"] = monitoring

    module_specs = {
        "app.core.workers.agent_tasks_worker": {"start_agent_tasks_worker": "agent_tasks_task"},
        "app.core.workers.async_consolidation_worker": {
            "start_consolidation_worker": "knowledge_consolidation_task"
        },
        "app.core.workers.auto_scaler": {"start_auto_scaler": "auto_scaler_task"},
        "app.core.workers.code_agent_worker": {"start_code_agent_worker": "code_agent_task"},
        "app.core.workers.codex_worker": {"start_codex_worker": "codex_worker_task"},
        "app.core.workers.document_ingestion_worker": {
            "start_document_ingestion_worker": "document_ingestion_task"
        },
        "app.core.workers.distillation_worker": {
            "start_distillation_worker": "distillation_task"
        },
        "app.core.workers.debate_proponent_worker": {
            "start_debate_proponent_worker": "debate_proponent_task"
        },
        "app.core.workers.debate_critic_worker": {
            "start_debate_critic_worker": "debate_critic_task"
        },
        "app.core.workers.neural_training_worker": {
            "start_neural_training_worker": "neural_training_task"
        },
        "app.core.workers.professor_agent_worker": {
            "start_professor_agent_worker": "professor_agent_task"
        },
        "app.core.workers.red_team_agent_worker": {
            "start_red_team_agent_worker": "red_team_agent_task"
        },
        "app.core.workers.reflexion_worker": {"start_reflexion_worker": "reflexion_task"},
        "app.core.workers.router_worker": {"start_router_worker": "router_task"},
        "app.core.workers.sandbox_agent_worker": {
            "start_sandbox_agent_worker": "sandbox_agent_task"
        },
        "app.core.workers.thinker_agent_worker": {
            "start_thinker_agent_worker": "thinker_agent_task"
        },
        "app.core.workers.google_productivity_worker": {
            "start_google_productivity_consumer": "google_productivity_task"
        },
    }

    meta_agent_module = ModuleType("app.core.workers.meta_agent_worker")
    meta_agent_module.start_meta_agent_worker = _async_starter("meta_agent_task")
    meta_agent_module.start_failure_event_consumer = _async_starter("failure_consumer_task")
    fake_modules["app.core.workers.meta_agent_worker"] = meta_agent_module

    memory_module = ModuleType("app.core.workers.memory_maintenance_worker")
    memory_module.memory_maintenance_worker = _FakeMemoryWorker()
    fake_modules["app.core.workers.memory_maintenance_worker"] = memory_module

    for module_name, attrs in module_specs.items():
        module = ModuleType(module_name)
        for attr_name, task_name in attrs.items():
            setattr(module, attr_name, _async_starter(task_name))
        fake_modules[module_name] = module

    for module_name, module in fake_modules.items():
        monkeypatch.setitem(sys.modules, module_name, module)


@pytest.mark.asyncio
async def test_start_all_workers_aplica_perfil_core_infra(monkeypatch: pytest.MonkeyPatch):
    _install_worker_stubs(monkeypatch)
    monkeypatch.setattr(orchestrator, "_get_active_node_profile", lambda: "CORE_INFRA")
    monkeypatch.setattr(
        orchestrator.settings, "ENABLE_GOOGLE_PRODUCTIVITY_WORKER", False, raising=False
    )

    workers = await orchestrator.start_all_workers()
    worker_map = dict(zip(orchestrator.WORKER_NAMES, workers, strict=False))

    assert len(workers) == len(orchestrator.WORKER_NAMES)
    assert worker_map["memory_maintenance"] == "memory_maintenance_task"
    assert worker_map["auto_scaler"] == "auto_scaler_task"
    assert worker_map["auto_healer"] == "auto_healer_task"
    assert worker_map["router"] == "router_task"

    skipped = worker_map["neural_training"]
    assert isinstance(skipped, DisabledWorkerHandle)
    assert skipped.reason == "disabled_by_profile"
    assert skipped.detail == "JANUS_NODE_PROFILE=CORE_INFRA"

    google_worker = worker_map["google_productivity"]
    assert isinstance(google_worker, DisabledWorkerHandle)
    assert google_worker.reason == "disabled_by_profile"


def test_worker_profile_helper_retorna_true_sem_perfil():
    assert orchestrator._is_worker_enabled_for_profile("meta_agent", None) is True
    assert orchestrator._is_worker_enabled_for_profile("router", "CORE_INFRA") is True
    assert orchestrator._is_worker_enabled_for_profile("meta_agent", "CORE_INFRA") is False
