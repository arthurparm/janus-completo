from types import SimpleNamespace

import pytest

import app.main as main_module


@pytest.mark.asyncio
async def test_lifespan_validates_secrets_before_kernel_startup(monkeypatch):
    order: list[str] = []

    def _validate():
        order.append("validate")

    class _KernelStub:
        def __init__(self):
            self.graph_db = object()
            self.memory_db = object()
            self.broker = object()
            self.agent_manager = object()
            self.agent_service = object()
            self.memory_service = object()
            self.knowledge_service = object()
            self.task_service = object()
            self.context_service = object()
            self.sandbox_service = object()
            self.reflexion_service = object()
            self.tool_service = object()
            self.collaboration_service = object()
            self.document_service = object()
            self.observability_service = object()
            self.optimization_service = object()
            self.autonomy_service = object()
            self.llm_service = object()
            self.chat_service = object()
            self.assistant_service = object()
            self.outbox_service = object()
            self.goal_manager = object()
            self.workers = []

        async def startup(self):
            order.append("startup")

        async def shutdown(self):
            order.append("shutdown")

    async def _noop_async(*args, **kwargs):
        return None

    kernel = _KernelStub()

    monkeypatch.setattr(
        "app.core.security.secret_validator.validate_production_secrets", _validate
    )
    monkeypatch.setattr(main_module.Kernel, "get_instance", staticmethod(lambda: kernel))
    monkeypatch.setattr(main_module, "init_graph", _noop_async)
    monkeypatch.setattr(main_module, "close_graph", _noop_async)
    monkeypatch.setattr(main_module, "start_all_workers", _noop_async)
    monkeypatch.setattr(main_module, "get_orchestrator_worker_names", lambda: [])
    monkeypatch.setattr(main_module.settings, "START_ORCHESTRATOR_WORKERS_ON_STARTUP", False)
    monkeypatch.setattr(main_module.settings, "LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(main_module.settings, "LLM_RATE_LIMITS", {})

    async with main_module.lifespan(main_module.app):
        assert order[0] == "validate"
        assert "startup" in order

    assert order[-1] == "shutdown"
