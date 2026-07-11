"""MCP server coverage tests."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.tools.mcp_server import _list_registry_tools, _list_agent_tools
from haip.tools.registry import register, list_all
from haip.tools import ToolResult, BaseTool


class TestMCPServerTools:
    def setup_method(self):
        # Cannot clear registry directly, use list_all check
        pass

    def test_list_registry_tools_returns_list(self):
        tools = _list_registry_tools()
        assert isinstance(tools, list)

    def test_list_agent_tools_unknown_agent(self):
        tools = _list_agent_tools("nonexistent_agent_xyz")
        assert tools == []

    def test_list_registry_tools_has_schema(self):
        tools = _list_registry_tools()
        if tools:
            for t in tools:
                assert "name" in t

    def test_multiple_calls_consistent(self):
        t1 = _list_registry_tools()
        t2 = _list_registry_tools()
        assert len(t1) == len(t2)

    def test_list_agent_tools_with_registered_agent(self):
        from haip.agent import register as agent_register, DomainPlugin, ToolDef, _registry
        _registry.clear()
        agent_register(DomainPlugin(name="test-mcp-agent", type="specialist",
            tools=[ToolDef(name="tool_a", description="Tool A", handler="test.fn")]))
        tools = _list_agent_tools("test-mcp-agent")
        assert len(tools) == 1
        assert tools[0]["name"] == "tool_a"
        _registry.clear()
