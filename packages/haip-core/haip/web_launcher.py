"""Web Launcher — 统一启动所有 Agent Web 服务.

支持:
  - 单 Agent 启动
  - 多 Agent 并行启动
  - 端口冲突检测
  - 浏览器自动打开
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from typing import Any


DEFAULT_PORTS: dict[str, int] = {
    "pharmacy": 8770, "orthopedic-surgery": 8765, "cardio-surgery": 8768,
    "pediatrics": 8820, "pain-hub": 8840, "acute-pain": 8841,
    "cardio-risk": 8801, "medical-record": 8766, "metrics": 8767, "haip": 8769,
}


def _resolve_port(agent_name: str) -> int:
    """端口解析: agent YAML 的 port 字段优先, DEFAULT_PORTS 仅作回退。"""
    try:
        from haip.agent import get as get_agent
        plugin = get_agent(agent_name)
        if plugin and plugin.port:
            return plugin.port
    except Exception:
        pass
    return DEFAULT_PORTS.get(agent_name, 8700)


def launch_agent(agent_name: str, port: int | None = None, host: str = "127.0.0.1",
                 open_browser: bool = True) -> subprocess.Popen | None:
    """启动单个 Agent 的 Web 服务。"""
    if port is None:
        port = _resolve_port(agent_name)

    if _port_in_use(host, port):
        print(f"  ⚠ 端口 {port} 已被占用, Agent '{agent_name}' 可能已在运行")
        return None

    cmd = [sys.executable, "-m", "uvicorn", "haip.web_server:app",
           "--host", host, "--port", str(port)]
    env = os.environ.copy()
    env["XHAIP_AGENT"] = agent_name  # 单 Agent 模式

    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  ✓ {agent_name} 已启动: http://{host}:{port}")
    return proc


def launch_all(host: str = "127.0.0.1", open_portal: bool = True) -> dict[str, subprocess.Popen]:
    """启动所有 Agent 的 Web 服务。"""
    processes: dict[str, subprocess.Popen] = {}
    for name in DEFAULT_PORTS:
        if name in ("medical-record", "metrics", "cardio-risk"):
            pass  # 跳过 Master Data 和 Specialist Agent (A2A only)
        else:
            proc = launch_agent(name, None, host, open_browser=False)
            if proc:
                processes[name] = proc
    # 启动门户
    portal_proc = launch_agent("haip", 8769, host, open_browser=open_portal)
    if portal_proc:
        processes["haip"] = portal_proc

    if open_portal:
        time.sleep(1)
        webbrowser.open(f"http://{host}:8769")

    return processes


def stop_all(processes: dict[str, subprocess.Popen]) -> None:
    """停止所有 Agent 进程。"""
    for name, proc in processes.items():
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"  ✗ {name} 已停止")


def validate(host: str = "127.0.0.1") -> dict[str, Any]:
    """验证所有 Agent 端口配置。"""
    issues: list[str] = []
    used_ports: set[int] = set()
    agents_status: dict[str, Any] = {}

    from haip.agent import list_all
    agents = list_all()

    for name, plugin in agents.items():
        port = plugin.port or DEFAULT_PORTS.get(name, 0)
        if port == 0:
            agents_status[name] = {"port": 0, "status": "CLI-only"}
            continue
        if port in used_ports:
            issues.append(f"端口冲突: {name} 和 another agent 共用端口 {port}")
        used_ports.add(port)
        in_use = _port_in_use(host, port)
        agents_status[name] = {"port": port, "status": "running" if in_use else "stopped"}

    return {"valid": len(issues) == 0, "issues": issues, "agents": agents_status, "total": len(agents)}


def _port_in_use(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect((host, port))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
