from types import SimpleNamespace

import pytest
from app.core.bootstrap import KERNEL_STATE_BINDINGS, bootstrap_dependencies
from app.core.kernel import Kernel
from fastapi import FastAPI


def test_kernel_reset_instance_creates_new_instance():
    Kernel.reset_instance()
    k1 = Kernel.get_instance()
    Kernel.reset_instance()
    k2 = Kernel.get_instance()
    Kernel.reset_instance()
    assert k1 is not k2


@pytest.mark.asyncio
async def test_bootstrap_dependencies_maps_all_bindings(monkeypatch):
    kernel = SimpleNamespace(**{attr: object() for attr in KERNEL_STATE_BINDINGS.values()})

    monkeypatch.setattr(Kernel, "get_instance", staticmethod(lambda *args, **kwargs: kernel))

    app = FastAPI()
    await bootstrap_dependencies(app)

    for state_key, kernel_attr in KERNEL_STATE_BINDINGS.items():
        assert getattr(app.state, state_key) is getattr(kernel, kernel_attr)


@pytest.mark.asyncio
async def test_bootstrap_dependencies_raises_when_kernel_attr_is_missing(monkeypatch):
    attrs = {attr: object() for attr in KERNEL_STATE_BINDINGS.values()}
    missing_attr = "graph_db"
    del attrs[missing_attr]
    kernel = SimpleNamespace(**attrs)

    monkeypatch.setattr(Kernel, "get_instance", staticmethod(lambda *args, **kwargs: kernel))

    app = FastAPI()
    with pytest.raises(RuntimeError) as exc_info:
        await bootstrap_dependencies(app)

    assert missing_attr in str(exc_info.value)


@pytest.mark.asyncio
async def test_kernel_startup_flags_control_phases(monkeypatch):
    kernel = Kernel()
    calls: list[object] = []

    async def _infra():
        calls.append("infra")

    async def _actors():
        calls.append("actors")

    def _build_dependency_graph(*, set_global_facades: bool = True):
        calls.append(("build_dependency_graph", set_global_facades))

    async def _bg():
        calls.append("bg")

    async def _auto():
        calls.append("auto")

    async def _warm():
        calls.append("warm")

    async def _senses():
        calls.append("senses")

    monkeypatch.setattr(kernel, "_init_infrastructure", _infra)
    monkeypatch.setattr(kernel, "_init_mas_actors", _actors)
    monkeypatch.setattr(kernel, "_build_dependency_graph", _build_dependency_graph)
    monkeypatch.setattr(kernel, "_start_background_processes", _bg)
    monkeypatch.setattr(kernel, "_run_auto_index", _auto)
    monkeypatch.setattr(kernel, "_warm_up_llms_async", _warm)
    monkeypatch.setattr(kernel, "_init_senses", _senses)
    monkeypatch.setattr("app.core.kernel.setup_logging", lambda *args, **kwargs: None)

    await kernel.startup(
        init_infrastructure=False,
        init_mas_actors=False,
        build_dependency_graph=False,
        register_tools=False,
        start_background_processes=False,
        auto_index=False,
        warmup_llms=False,
        init_senses=False,
    )
    assert calls == []

    await kernel.startup(
        init_infrastructure=False,
        init_mas_actors=False,
        build_dependency_graph=True,
        set_global_facades=False,
        register_tools=False,
        start_background_processes=False,
        auto_index=False,
        warmup_llms=False,
        init_senses=False,
    )
    assert calls == [("build_dependency_graph", False)]
