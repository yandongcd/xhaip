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


class TestBuiltinTokenAuth:
    """Optional X-MCP-Token auth on the built-in JSON-RPC transport."""

    def _start_server(self, token=""):
        import http.server
        import threading
        import time

        from haip.tools.mcp_server import _serve_builtin

        class RecordingHTTPServer(http.server.HTTPServer):
            instances = []

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                RecordingHTTPServer.instances.append(self)

        RecordingHTTPServer.instances.clear()
        tools = [{"name": "echo_tool", "description": "Echo", "parameters": {"x": {"type": "string"}}}]

        def dispatch(tn, p):
            return {"success": True, "output": p.get("x", ""), "data": {}, "error": None, "confidence": None}

        thread = threading.Thread(
            target=_serve_builtin,
            kwargs={"name": "tokentest", "tools": tools, "port": 0, "host": "127.0.0.1",
                    "dispatch_fn": dispatch, "token": token},
            daemon=True,
        )
        with patch.object(http.server, "HTTPServer", RecordingHTTPServer):
            thread.start()
            deadline = time.time() + 5
            while not RecordingHTTPServer.instances and time.time() < deadline:
                time.sleep(0.01)
            assert RecordingHTTPServer.instances, "server did not start"
            return RecordingHTTPServer.instances[-1], thread

    def _post(self, server, token_header=None):
        import json
        import urllib.error
        import urllib.request

        url = f"http://127.0.0.1:{server.server_address[1]}/"
        body = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        if token_header is not None:
            req.add_header("X-MCP-Token", token_header)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_no_token_set_accepts_requests(self):
        server, thread = self._start_server(token="")
        try:
            code, data = self._post(server)
            assert code == 200
            assert "tools" in data["result"]
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_token_set_rejects_request_without_token(self):
        server, thread = self._start_server(token="s3cret")
        try:
            code, data = self._post(server)
            assert code == 401
            assert data["error"]["message"].startswith("Unauthorized")
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_token_set_rejects_wrong_token(self):
        server, thread = self._start_server(token="s3cret")
        try:
            code, _ = self._post(server, token_header="wrong")
            assert code == 401
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_token_set_accepts_request_with_matching_token(self):
        server, thread = self._start_server(token="s3cret")
        try:
            code, data = self._post(server, token_header="s3cret")
            assert code == 200
            assert "tools" in data["result"]
        finally:
            server.shutdown()
            thread.join(timeout=5)
