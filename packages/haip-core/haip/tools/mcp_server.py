"""HAIP Generic MCP Server — exposes registered tools via MCP protocol.

Usage:
    python -m haip.tools.mcp_server serve --agent <agent_name> --port <port>
    python -m haip.tools.mcp_server serve --all --port 8700

The server auto-discovers tools from:
  1. The global tool registry (haip.tools.registry)
  2. DomainPlugin agent YAML definitions (haip.agent)

Each tool is exposed as an MCP tool callable via tools/list and tools/call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _list_registry_tools() -> list[dict[str, Any]]:
    """Return tools from the global tool registry."""
    try:
        from haip.tools.registry import list_schemas
        return list_schemas()
    except ImportError:
        return []


def _list_agent_tools(agent_name: str) -> list[dict[str, Any]]:
    """Return tools defined on a specific agent's YAML definition."""
    try:
        from haip.agent import get as get_agent, load_from_dir, list_all
    except ImportError:
        return []

    # Ensure agents are loaded
    if not list_all():
        candidates = [
            Path.cwd() / "agents" / "definitions",
            Path.cwd() / "packages" / "haip-hospital" / "agents" / "definitions",
        ]
        for d in candidates:
            if d.exists():
                load_from_dir(str(d))

    plugin = get_agent(agent_name)
    if plugin is None:
        return []

    tools = []
    for td in plugin.tools:
        tools.append({
            "name": td.name,
            "description": td.description,
            "parameters": td.input,
            "handler": td.handler,
            "agent": agent_name,
        })
    return tools


def _run_agent_tool(agent_name: str, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool on an agent via the A2A dispatcher."""
    try:
        from haip.a2a import call as a2a_call
        result = a2a_call(agent_name, tool_name, params)
        return result
    except ImportError:
        return {"error": "A2A dispatcher not available"}
    except Exception as e:
        return {"error": str(e)}


def _run_registry_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool from the global tool registry."""
    try:
        from haip.tools.registry import execute
        result = execute(tool_name, **params)
        return {
            "success": result.success,
            "output": result.output,
            "data": result.data,
            "error": result.error,
            "confidence": result.confidence,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# -- CLI entry points for `xhaip tools mcp-serve` --


def serve_agent(agent_name: str, port: int = 8700, host: str = "0.0.0.0") -> None:
    """Serve agent tools over MCP SSE transport."""
    tools = _list_agent_tools(agent_name)
    if not tools:
        print(f"No tools found for agent: {agent_name}")
        print("Tip: Run `xhaip load` first, or check `xhaip info {agent_name}`")
        sys.exit(1)

    print(f"[{agent_name}] {len(tools)} tool(s) discovered:")
    for t in tools:
        print(f"  - {t['name']}: {t.get('description', '')[:60]}")

    _serve_mcp(agent_name, tools, port, host, dispatch_fn=lambda tn, p: _run_agent_tool(agent_name, tn, p))


def serve_all(port: int = 8700, host: str = "0.0.0.0") -> None:
    """Serve all registered tools over MCP SSE transport."""
    reg_tools = _list_registry_tools()
    if not reg_tools:
        print("No tools in global registry.")
        print("Tip: Run `xhaip load` first or register tools via haip.tools.registry.register()")
        sys.exit(1)

    print(f"[ALL] {len(reg_tools)} tool(s) from global registry:")
    for t in reg_tools:
        print(f"  - {t['name']}: {t.get('description', '')[:60]}")

    _serve_mcp("all", reg_tools, port, host, dispatch_fn=lambda tn, p: _run_registry_tool(tn, p))


def _serve_mcp(
    name: str,
    tools: list[dict[str, Any]],
    port: int,
    host: str,
    dispatch_fn: callable,
) -> None:
    """Start MCP server using FastMCP (optional dependency)."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("fastmcp not installed. Install with: pip install mcp")
        print("Falling back to built-in HTTP JSON-RPC server...")
        _serve_builtin(name, tools, port, host, dispatch_fn)
        return

    mcp = FastMCP(name)
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.transport_security.enable_dns_rebinding_protection = False

    for tool_info in tools:
        tool_name = tool_info["name"]
        tool_desc = tool_info.get("description", "")

        def make_tool(tn, td):
            def tool_fn(**kwargs: Any) -> str:
                result = dispatch_fn(tn, kwargs)
                return json.dumps(result, ensure_ascii=False, default=str)

            tool_fn.__name__ = tn.replace(".", "_").replace("-", "_")
            tool_fn.__doc__ = td or f"MCP tool: {tn}"
            return tool_fn

        try:
            mcp.add_tool(make_tool(tool_name, tool_desc))
        except Exception as e:
            print(f"  [WARN] Could not register tool {tool_name}: {e}")

    print(f"\n[{name}] MCP server starting on {host}:{port} (SSE transport)")
    mcp.run(transport="sse")


def _serve_builtin(
    name: str,
    tools: list[dict[str, Any]],
    port: int,
    host: str,
    dispatch_fn: callable,
) -> None:
    """Built-in JSON-RPC server when fastmcp is not available."""
    import http.server

    tool_index: dict[str, dict[str, Any]] = {t["name"]: t for t in tools}

    class MCPHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                request = json.loads(body)
            except json.JSONDecodeError:
                self._respond(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}})
                return

            method = request.get("method", "")
            req_id = request.get("id")

            if method == "tools/list":
                result = [{
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "inputSchema": {"type": "object", "properties": t.get("parameters", {})},
                } for t in tools]
                self._respond(200, {"jsonrpc": "2.0", "id": req_id, "result": {"tools": result}})

            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                if tool_name not in tool_index:
                    self._respond(200, {"jsonrpc": "2.0", "id": req_id, "result": {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}})
                    return

                try:
                    result_data = dispatch_fn(tool_name, arguments)
                    self._respond(200, {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result_data, ensure_ascii=False, default=str)}]}})
                except Exception as e:
                    self._respond(200, {"jsonrpc": "2.0", "id": req_id, "result": {"isError": True, "content": [{"type": "text", "text": str(e)}]}})

            elif method == "initialize":
                self._respond(200, {"jsonrpc": "2.0", "id": req_id, "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": f"haip-mcp-{name}", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                }})

            elif method == "notifications/initialized":
                self._respond(200, {"jsonrpc": "2.0", "id": req_id, "result": {}})

            else:
                self._respond(404, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def _respond(self, code, data):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    server = http.server.HTTPServer((host, port), MCPHandler)
    print(f"\n[{name}] Built-in MCP server starting on {host}:{port} (JSON-RPC)")
    print("Endpoints: POST /  (tools/list, tools/call)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()


def main():
    """Standalone entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="HAIP MCP Server")
    sub = parser.add_subparsers(dest="cmd")

    serve_p = sub.add_parser("serve", help="Start MCP server")
    serve_p.add_argument("--agent", "-a", default="", help="Agent name (serve single agent's tools)")
    serve_p.add_argument("--all", action="store_true", help="Serve all registered tools")
    serve_p.add_argument("--port", "-p", type=int, default=8700, help="Port (default: 8700)")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")

    sub.add_parser("list-agents", help="List agents with available tools")

    args = parser.parse_args()

    if args.cmd == "serve":
        if args.all:
            serve_all(port=args.port, host=args.host)
        elif args.agent:
            serve_agent(args.agent, port=args.port, host=args.host)
        else:
            print("Specify --agent <name> or --all")
            sys.exit(1)
    elif args.cmd == "list-agents":
        from haip.agent import list_all, load_from_dir
        from pathlib import Path

        ags = list_all()
        if not ags:
            candidates = [
                Path.cwd() / "agents" / "definitions",
                Path.cwd() / "packages" / "haip-hospital" / "agents" / "definitions",
            ]
            for d in candidates:
                if d.exists():
                    load_from_dir(str(d))
            ags = list_all()

        for aname, ainfo in ags.items():
            tool_names = [t.name for t in ainfo.tools] if hasattr(ainfo, "tools") and ainfo.tools else []
            print(f"  {aname:30s} | tools: {len(tool_names)} ({', '.join(tool_names[:5])}{'...' if len(tool_names) > 5 else ''})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
