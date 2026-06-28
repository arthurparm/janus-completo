import pytest

from app.core.tools.action_module import ActionRegistry


class FakeTool:
    def __init__(self, name="test_tool"):
        self.name = name
        self.description = "A test tool"


@pytest.fixture
def registry():
    reg = ActionRegistry()
    yield reg
    for name in list(reg._tools.keys()):
        reg.unregister(name)


class TestNamespaceRegistration:
    def test_register_core_default(self, registry):
        tool = FakeTool("default_tool")
        registry.register_tool(tool)
        ns = registry.get_namespace("default_tool")
        assert ns == "core"

    def test_register_explicit_core(self, registry):
        tool = FakeTool("explicit_core")
        registry.register_tool(tool, namespace="core")
        ns = registry.get_namespace("explicit_core")
        assert ns == "core"

    def test_register_evolution(self, registry):
        tool = FakeTool("evolution_tool")
        registry.register_tool(tool, namespace="evolution")
        ns = registry.get_namespace("evolution_tool")
        assert ns == "evolution"

    def test_register_user(self, registry):
        tool = FakeTool("user_tool")
        registry.register_tool(tool, namespace="user")
        ns = registry.get_namespace("user_tool")
        assert ns == "user"

    def test_evolution_cannot_shadow_core(self, registry):
        core_tool = FakeTool("shadow_tool")
        registry.register_tool(core_tool, namespace="core")
        evo_tool = FakeTool("shadow_tool")
        with pytest.raises(ValueError, match="Cannot"):
            registry.register_tool(evo_tool, namespace="evolution")


class TestResolveTool:
    def test_resolve_tool_evolution_first(self, registry):
        core_tool = FakeTool("multi_tool")
        registry.register_tool(core_tool, namespace="core")
        evo_tool = FakeTool("multi_tool_evo")
        registry.register_tool(evo_tool, namespace="evolution")
        resolved = registry.resolve_tool("multi_tool_evo")
        assert resolved is not None

    def test_resolve_tool_falls_back_to_core(self, registry):
        core_tool = FakeTool("core_only")
        registry.register_tool(core_tool, namespace="core")
        resolved = registry.resolve_tool("core_only")
        assert resolved is not None

    def test_resolve_tool_not_found(self, registry):
        resolved = registry.resolve_tool("nonexistent")
        assert resolved is None


class TestListByNamespace:
    def test_list_by_namespace(self, registry):
        registry.register_tool(FakeTool("c1"), namespace="core")
        registry.register_tool(FakeTool("c2"), namespace="core")
        registry.register_tool(FakeTool("e1"), namespace="evolution")

        core_tools = registry.list_by_namespace("core")
        evo_tools = registry.list_by_namespace("evolution")
        assert len(core_tools) == 2
        assert len(evo_tools) == 1


class TestGetNamespace:
    def test_get_namespace(self, registry):
        registry.register_tool(FakeTool("evo_ns"), namespace="evolution")
        assert registry.get_namespace("evo_ns") == "evolution"

    def test_get_namespace_unknown(self, registry):
        assert registry.get_namespace("unknown") is None
