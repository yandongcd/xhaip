"""Tests for haip.tools.mcp_server."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import DomainPlugin
from haip.agent import _registry as agent_registry
from haip.agent import register as register_agent
from haip.tools import BaseTool, ToolResult
from haip.tools import registry as tool_registry
from haip.tools.mcp_server import (
    _list_agent_tools,
    _list_registry_tools,
    serve_agent,
    serve_all,
)


class _DummyTool(BaseTool):
    name = "dummy_test_tool"
    description = "A dummy tool for testing"

    def execute(self, **kwargs):
        return ToolResult(success=True, output="ok")


class TestListRegistryTools:
    def setup_method(self):
        tool_registry._tools.clear()

    def teardown_method(self):
        tool_registry._tools.clear()

    def test_empty_registry_returns_empty_list(self):
        result = _list_registry_tools()
        assert result == []

    def test_returns_schemas_for_registered_tools(self):
        tool_registry.register(_DummyTool())
        result = _list_registry_tools()
        assert len(result) == 1
        assert result[0]["name"] == "dummy_test_tool"
        assert result[0]["description"] == "A dummy tool for testing"

    def test_returns_multiple_tool_schemas(self):
        tool_registry.register(_DummyTool())

        class SecondTool(BaseTool):
            name = "second_tool"
            description = "Second tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool_registry.register(SecondTool())
        result = _list_registry_tools()
        assert len(result) == 2
        names = [t["name"] for t in result]
        assert "dummy_test_tool" in names
        assert "second_tool" in names


class TestListAgentTools:
    def setup_method(self):
        agent_registry.clear()

    def teardown_method(self):
        agent_registry.clear()

    def test_unknown_agent_returns_empty_list(self):
        result = _list_agent_tools("nonexistent-agent")
        assert result == []

    def test_empty_registry_returns_empty_list(self):
        result = _list_agent_tools("any-agent")
        assert result == []

    def test_returns_tools_for_registered_agent(self):
        from haip.agent import ToolDef

        plugin = DomainPlugin(
            name="test-agent",
            cn_name="测试",
            type="business",
            port=9999,
            tools=[
                ToolDef(name="tool_a", description="Tool A", handler="mod.func_a"),
                ToolDef(name="tool_b", description="Tool B", handler="mod.func_b"),
            ],
        )
        register_agent(plugin)
        result = _list_agent_tools("test-agent")
        assert len(result) == 2
        assert result[0]["name"] == "tool_a"
        assert result[0]["agent"] == "test-agent"
        assert result[1]["name"] == "tool_b"

    def test_agent_with_no_tools_returns_empty_list(self):
        plugin = DomainPlugin(
            name="no-tools-agent",
            cn_name="无工具",
            type="business",
            port=9999,
            tools=[],
        )
        register_agent(plugin)
        result = _list_agent_tools("no-tools-agent")
        assert result == []


class TestServeAgentErrors:
    def setup_method(self):
        agent_registry.clear()

    def teardown_method(self):
        agent_registry.clear()

    def test_no_agent_found_exits_with_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            serve_agent("nonexistent-agent", port=9999)
        assert exc_info.value.code == 1

    def test_agent_with_no_tools_exits_with_error(self):
        plugin = DomainPlugin(
            name="empty-agent",
            cn_name="空Agent",
            type="business",
            port=9999,
            tools=[],
        )
        register_agent(plugin)
        with pytest.raises(SystemExit) as exc_info:
            serve_agent("empty-agent", port=9999)
        assert exc_info.value.code == 1


class TestServeAllErrors:
    def setup_method(self):
        tool_registry._tools.clear()

    def teardown_method(self):
        tool_registry._tools.clear()

    def test_empty_registry_exits_with_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            serve_all(port=9999)
        assert exc_info.value.code == 1


class TestMainFunction:
    def test_main_help(self, capsys):
        from haip.tools.mcp_server import main as mcp_main

        with patch.object(sys, "argv", ["mcp_server", "--help"]):
            with pytest.raises(SystemExit) as exc:
                mcp_main()
            assert exc.value.code == 0
