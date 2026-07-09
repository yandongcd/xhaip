"""测试 Agent Plugin 模型 + YAML loader."""

import tempfile
from pathlib import Path

from haip.agent import DomainPlugin, load_from_dir, register, get, list_all, build_a2a_routes


YAML_PHARMACY = """
name: pharmacy
cn_name: 药剂科智能体
type: business
port: 8770
department: 药剂科
aliases: [药剂科, 药房]
prompt:
  system: 你是南方医院药剂科AI助手
  temperature: 0.3
tools:
  - name: assess_nutrition
    description: 评估营养风险
    handler: pharmacy.assessment.nutrition_risk
    input: {patient_id: str}
  - name: calculate_tpn
    description: TPN 配比计算
    handler: pharmacy.tpn_calculator.compute
depends_on:
  - agent: medical-record
    version: '>=1.0'
guard:
  triggers: [药物交互]
  high_risk_scenarios: [抗凝药物相互作用]
ui:
  template: chat-with-role-switcher
  roles:
    - {id: pharmacist, label: 药师, default: true}
"""


class TestDomainPlugin:
    def test_from_yaml_basic(self):
        import yaml
        data = yaml.safe_load(YAML_PHARMACY)
        plugin = DomainPlugin.from_yaml(data)
        assert plugin.name == "pharmacy"
        assert plugin.cn_name == "药剂科智能体"
        assert plugin.type == "business"
        assert plugin.port == 8770
        assert "药剂科" in plugin.aliases

    def test_tools_parsed(self):
        import yaml
        data = yaml.safe_load(YAML_PHARMACY)
        plugin = DomainPlugin.from_yaml(data)
        assert len(plugin.tools) == 2
        assert plugin.tools[0].name == "assess_nutrition"
        assert plugin.tools[0].handler == "pharmacy.assessment.nutrition_risk"
        assert plugin.tools[0].input == {"patient_id": "str"}

    def test_prompt_parsed(self):
        import yaml
        data = yaml.safe_load(YAML_PHARMACY)
        plugin = DomainPlugin.from_yaml(data)
        assert "药剂科AI助手" in plugin.prompt.system
        assert plugin.prompt.temperature == 0.3

    def test_depends_on_parsed(self):
        import yaml
        data = yaml.safe_load(YAML_PHARMACY)
        plugin = DomainPlugin.from_yaml(data)
        assert len(plugin.depends_on) == 1
        assert plugin.depends_on[0]["agent"] == "medical-record"

    def test_guard_parsed(self):
        import yaml
        data = yaml.safe_load(YAML_PHARMACY)
        plugin = DomainPlugin.from_yaml(data)
        assert "药物交互" in plugin.guard.triggers
        assert "抗凝药物相互作用" in plugin.guard.high_risk_scenarios

    def test_ui_parsed(self):
        import yaml
        data = yaml.safe_load(YAML_PHARMACY)
        plugin = DomainPlugin.from_yaml(data)
        assert plugin.ui.template == "chat-with-role-switcher"
        assert len(plugin.ui.roles) == 1
        assert plugin.ui.roles[0]["id"] == "pharmacist"

    def test_defaults(self):
        plugin = DomainPlugin(name="test")
        assert plugin.version == "1.0.0"
        assert plugin.type == "business"
        assert plugin.port == 0
        assert plugin.tools == []
        assert plugin.depends_on == []


class TestAgentRegistry:
    def setup_method(self):
        list_all().clear()

    def test_register_and_get(self):
        plugin = DomainPlugin(name="test", type="business")
        register(plugin)
        assert get("test") is plugin

    def test_get_nonexistent(self):
        assert get("nonexistent") is None

    def test_load_from_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "test_agent.yaml"
            yaml_path.write_text(YAML_PHARMACY, encoding="utf-8")
            count = load_from_dir(tmp)
            assert count == 1
            assert get("pharmacy") is not None

    def test_load_from_dir_skips_underscore(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "_schema.yaml").write_text("{}", encoding="utf-8")
            count = load_from_dir(tmp)
            assert count == 0

    def test_build_a2a_routes(self):
        from haip.agent import ToolDef
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(
                name="test", description="", handler="pkg.fn",
            )],
        ))
        routes = build_a2a_routes()
        assert "pharmacy" in routes
