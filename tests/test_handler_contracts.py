"""Agent YAML handler 契约测试 — 每个 tool 的 handler 必须可导入且函数存在.

源自 2026-07-17 interventional_pain.imaging_gate 漂移 bug:
YAML 声明的 handler 与模块实际函数名不一致, 集成测试自建 ToolDef 绕过 YAML 未能拦截。
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS_DIR = ROOT / "packages" / "haip-hospital" / "agents" / "definitions"


def _all_handlers() -> list[tuple[str, str, str]]:
    """(agent_name, tool_name, handler) 全量清单."""
    out = []
    for f in sorted(DEFINITIONS_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        for t in data.get("tools", []):
            handler = t.get("handler", "")
            if handler:
                out.append((data["name"], t["name"], handler))
    return out


HANDLERS = _all_handlers()


def test_definitions_found():
    assert len(HANDLERS) > 50, f"handler 清单异常: {len(HANDLERS)}"


@pytest.mark.parametrize("agent,tool,handler", HANDLERS,
                         ids=[f"{a}.{t}" for a, t, _ in HANDLERS])
def test_handler_resolves(agent, tool, handler):
    """handler 模块可导入且函数存在."""
    module_name, func_name = handler.rsplit(".", 1)
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        pytest.fail(f"{agent}.{tool}: 模块不可导入 {module_name} ({e})")
    fn = getattr(mod, func_name, None)
    assert callable(fn), (
        f"{agent}.{tool}: 函数 {func_name} 不存在于 {module_name} — YAML 与模块漂移"
    )
