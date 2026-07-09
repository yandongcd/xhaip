"""测试 A2A Dispatcher."""

import sys
from pathlib import Path

from haip.a2a import call, get_history, clear_history
from haip.agent import register as reg_agent, list_all

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _setup_pharmacy_agent():
    from haip.agent import DomainPlugin, ToolDef
    list_all().clear()
    plugin = DomainPlugin(
        name="pharmacy", type="business", port=8770,
        tools=[ToolDef(
            name="calculate_tpn", description="TPN 配比计算",
            handler="pharmacy.handlers.calculate_tpn",
            input={"patient_id": "str", "energy_kcal": "float"},
        )],
    )
    reg_agent(plugin)


class TestA2ADispatcher:
    def setup_method(self):
        clear_history()
        list_all().clear()

    def test_call_unknown_agent(self):
        result = call("nonexistent", "test")
        assert result["status"] == "error"
        assert "Unknown agent" in result["error"]

    def test_call_unknown_tool(self):
        from haip.agent import DomainPlugin
        list_all().clear()
        reg_agent(DomainPlugin(name="test", type="specialist"))
        result = call("test", "nonexistent")
        assert result["status"] == "error"

    def test_call_history_recorded(self):
        from haip.agent import DomainPlugin, ToolDef
        list_all().clear()
        reg_agent(DomainPlugin(
            name="test", type="specialist",
            tools=[ToolDef(name="echo", description="", handler="pkg.mod.fn", input={})],
        ))
        _ = call("test", "echo", {"msg": "hi"})
        history = get_history()
        assert len(history) >= 1
        assert history[0]["agent"] == "test"
