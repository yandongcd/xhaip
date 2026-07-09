"""Tool Registry — 全局工具注册 + 发现."""

from __future__ import annotations

from typing import Any

from haip.tools import BaseTool, ToolResult

_tools: dict[str, BaseTool] = {}


def register(tool: BaseTool) -> None:
    _tools[tool.name] = tool


def get(name: str) -> BaseTool | None:
    return _tools.get(name)


def list_all() -> dict[str, BaseTool]:
    return dict(_tools)


def list_schemas() -> list[dict[str, Any]]:
    return [
        {"name": t.name, "description": t.description, "parameters": t.parameters()}
        for t in _tools.values()
    ]


def execute(name: str, **kwargs: Any) -> ToolResult:
    tool = _tools.get(name)
    if tool is None:
        return ToolResult(success=False, error=f"Unknown tool: {name}")
    try:
        return tool.execute(**kwargs)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
