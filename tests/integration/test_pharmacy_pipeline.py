"""全链路集成测试 — YAML 定义 → 注册 → A2A 调用 → 业务计算.

验证药剂科 Agent 从 YAML 到业务函数执行的完整链路。
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.agent import load_from_dir, register, DomainPlugin, ToolDef, _registry  # noqa: E402
from haip.a2a import call, clear_history, get_history  # noqa: E402


YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


class TestPharmacyFullPipeline:
    def setup_method(self):
        """每个测试前清空注册表。"""
        from haip.agent import _registry
        _registry.clear()
        clear_history()

    def test_load_pharmacy_yaml_success(self):
        count = load_from_dir(str(YAML_DIR))
        assert count >= 1

    def test_registered_after_load(self):
        from haip.agent import get
        load_from_dir(str(YAML_DIR))
        plugin = get("pharmacy")
        assert plugin is not None
        assert plugin.name == "pharmacy"
        assert plugin.type == "business"
        assert plugin.port == 8770

    def test_tools_available_in_registry(self):
        from haip.agent import get
        load_from_dir(str(YAML_DIR))
        plugin = get("pharmacy")
        tool_names = [t.name for t in plugin.tools]
        assert "assess_nutrition" in tool_names
        assert "calculate_tpn" in tool_names
        assert "review_prescription" in tool_names

    def test_a2a_call_to_nonexistent_module(self):
        """调用不存在的模块应返回明确错误，不 crash。"""
        _registry.clear()
        register(DomainPlugin(
            name="test", type="business",
            tools=[ToolDef(name="probe", description="", handler="no.such.module.func")],
        ))
        result = call("test", "probe")
        assert result["status"] == "error"
        assert "ModuleNotFoundError" in result["error"] or "not found" in result["error"]

    def test_a2a_call_to_nonexistent_func(self):
        """调用不存在的函数应返回明确错误。"""
        _registry.clear()
        register(DomainPlugin(
            name="test", type="business",
            tools=[ToolDef(name="probe", description="",
                          handler="haip.llm.mock.nonexistent_func")],
        ))
        result = call("test", "probe")
        assert result["status"] == "error"

    def test_a2a_call_unknown_agent(self):
        result = call("nonexistent", "any_tool")
        assert result["status"] == "error"

    def test_a2a_call_unknown_tool(self):
        _registry.clear()
        register(DomainPlugin(name="test", type="business"))
        result = call("test", "unknown_tool")
        assert result["status"] == "error"

    def test_call_history_tracks_errors(self):
        _registry.clear()
        register(DomainPlugin(name="test", type="business"))
        call("test", "unknown_tool")
        history = get_history()
        assert len(history) >= 1
        assert history[0]["status"] == "error"

    def test_call_batch(self):
        """批量调用测试。"""
        from haip.a2a import call_batch
        _registry.clear()
        register(DomainPlugin(name="a1", type="business"))
        register(DomainPlugin(name="a2", type="specialist"))
        results = call_batch([
            {"agent": "a1", "tool": "no_tool"},
            {"agent": "a2", "tool": "no_tool"},
            {"agent": "ghost", "tool": "x"},
        ])
        assert len(results) == 3
        assert all(r["status"] == "error" for r in results)
