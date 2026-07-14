"""A2A Transport abstraction — supports InProcess, MCP/HTTP, and Mock transports.

Usage:
    from haip.a2a.transport import InProcessTransport, MCPTransport, set_transport
    transport = MCPTransport(base_url="http://localhost:8765")
    set_transport("orthopedic-surgery", transport)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentTransport(ABC):
    """Agent 调用传输层抽象。"""

    @abstractmethod
    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        ...


class InProcessTransport(AgentTransport):
    """进程内 A2A 调用 — 直接 importlib 加载。"""

    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        from haip.a2a import call as a2a_call
        return a2a_call(agent, tool, params)


class MockTransport(AgentTransport):
    """测试用 Mock Transport。"""

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None):
        self.responses = responses or {}
        self.call_log: list[dict[str, Any]] = []

    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        self.call_log.append({"agent": agent, "tool": tool, "params": params})
        key = f"{agent}/{tool}"
        if key in self.responses:
            return dict(self.responses[key])
        return {"status": "ok", "result": f"mock:{agent}/{tool}", "agent": agent}


class MCPTransport(AgentTransport):
    """MCP/HTTP 远程 Agent 调用 — 通过 FastAPI 端点调用远程 Agent。

    使用 httpx 作为 HTTP 客户端，连接运行在其他进程/容器中的 Agent。
    """

    def __init__(self, base_url: str = "", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call(self, agent: str, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        import httpx
        url = f"{self.base_url}/api/agent/{agent}/call"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json={
                    "tool": tool,
                    "params": params,
                })
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "error": f"HTTP {e.response.status_code}",
                    "detail": str(e)}
        except httpx.RequestError as e:
            return {"status": "error", "error": f"Connection failed: {e}",
                    "detail": str(e)}


# ── Transport Registry ──

_transports: dict[str, AgentTransport] = {}


def set_transport(agent_name: str, transport: AgentTransport) -> None:
    """为指定 Agent 设置传输方式。"""
    _transports[agent_name] = transport


def get_transport(agent_name: str) -> AgentTransport | None:
    """获取 Agent 的传输方式，未设置返回 None (默认 InProcess)。"""
    return _transports.get(agent_name)


def remove_transport(agent_name: str) -> None:
    """移除 Agent 的自定义传输（回退到 InProcess）。"""
    _transports.pop(agent_name, None)
