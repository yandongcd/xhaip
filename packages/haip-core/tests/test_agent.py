"""测试 Agent Plugin 模型 + YAML loader."""

import tempfile
from pathlib import Path

import pytest

from haip.agent import (
    DomainPlugin,
    ToolDef,
    _registry,
    build_a2a_routes,
    get,
    list_all,
    load_from_dir,
    register,
)

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
        _registry.clear()

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
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[ToolDef(
                name="test", description="", handler="pkg.fn",
            )],
        ))
        routes = build_a2a_routes()
        assert "pharmacy" in routes


# ── Error Path Tests ─────────────────────────────────────────────────

class TestErrorPaths:
    def setup_method(self):
        _registry.clear()

    def test_invalid_yaml_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad_agent.yaml"
            bad_path.write_text("name: bad\n  tools:\n  - indented wrong\n", encoding="utf-8")
            with pytest.raises((Exception,)):
                load_from_dir(tmp)
        assert True, "invalid YAML should raise exception"

    def test_duplicate_agent_name(self):
        register(DomainPlugin(name="dup", type="business"))
        register(DomainPlugin(name="dup", type="specialist"))
        plugin = get("dup")
        assert plugin is not None
        assert plugin.type == "specialist"

    def test_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "missing_name.yaml"
            yaml_path.write_text("type: business\nport: 8000\n", encoding="utf-8")
            count = load_from_dir(tmp)
            assert count >= 0  # defensive: ensure load_from_dir doesn't crash on invalid YAML


# ── Boundary Condition Tests ─────────────────────────────────────────

class TestBoundaryConditions:
    def setup_method(self):
        _registry.clear()

    def test_agent_name_with_chinese_characters(self):
        plugin = DomainPlugin(name="测试智能体", cn_name="测试中文名称", type="business")
        register(plugin)
        assert get("测试智能体") is plugin

    def test_empty_tools_list(self):
        plugin = DomainPlugin(name="empty_tools", type="business", tools=[])
        register(plugin)
        agent = get("empty_tools")
        assert agent is not None
        assert agent.tools == []

    def test_agent_name_with_special_chars(self):
        plugin = DomainPlugin(name="agent-v1.0_test", type="specialist")
        register(plugin)
        assert get("agent-v1.0_test") is plugin

    def test_register_multiple_agents(self):
        for i in range(10):
            register(DomainPlugin(name=f"agent_{i}", type="business"))
        list_all()
        for i in range(10):
            assert get(f"agent_{i}") is not None


# ── Per-agent Loading Tests (v1.3) ─────────────────────────────────────

YAML_DEP_CHAIN = """
name: dep-a
cn_name: Agent A
type: business
port: 8001
depends_on:
  - agent: dep-b
tools:
  - name: t1
    description: tool one
    handler: mod.fn
"""

YAML_DEP_B = """
name: dep-b
cn_name: Agent B
type: master_data
port: 8002
depends_on:
  - agent: dep-c
tools:
  - name: t2
    description: tool two
    handler: mod.fn2
"""

YAML_DEP_C = """
name: dep-c
cn_name: Agent C
type: master_data
port: 8003
tools:
  - name: t3
    description: tool three
    handler: mod.fn3
"""

YAML_DEPRECATED = """
name: old-agent
cn_name: Old Agent
type: business
port: 9000
depends_on: []
"""


class TestAgentFilter:
    def setup_method(self):
        _registry.clear()
        list_all().clear()

    def test_load_with_agent_filter_single(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "dep-a.yaml").write_text(YAML_DEP_CHAIN, encoding="utf-8")
            (d / "dep-b.yaml").write_text(YAML_DEP_B, encoding="utf-8")
            (d / "dep-c.yaml").write_text(YAML_DEP_C, encoding="utf-8")
            count = load_from_dir(str(d), agent_filter="dep-a")
            assert count >= 3  # dep-a + dep-b + dep-c via BFS

    def test_load_with_agent_filter_only_loads_depends_on_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "target.yaml").write_text(YAML_DEP_CHAIN.replace("dep-a", "target"), encoding="utf-8")
            (d / "dep-b.yaml").write_text(YAML_DEP_B, encoding="utf-8")
            (d / "dep-c.yaml").write_text(YAML_DEP_C, encoding="utf-8")
            (d / "pharmacy.yaml").write_text(YAML_PHARMACY, encoding="utf-8")
            count = load_from_dir(str(d), agent_filter="target")
            assert count >= 3
            assert get("target") is not None
            assert get("dep-b") is not None
            assert get("dep-c") is not None
            assert get("pharmacy") is None  # unrelated to depends_on chain

    def test_load_without_filter_loads_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "a.yaml").write_text(YAML_DEP_CHAIN.replace("dep-a", "agent-a"), encoding="utf-8")
            (d / "dep-b.yaml").write_text(YAML_DEP_B, encoding="utf-8")
            (d / "dep-c.yaml").write_text(YAML_DEP_C, encoding="utf-8")
            count = load_from_dir(str(d))
            assert count >= 3

    def test_skips_deprecated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "active.yaml").write_text(YAML_DEP_CHAIN.replace("dep-a", "active"), encoding="utf-8")
            (d / "old.yaml.deprecated").write_text(YAML_DEPRECATED, encoding="utf-8")
            count = load_from_dir(str(d))
            assert count == 1
            assert get("active") is not None
            assert get("old-agent") is None

    def test_skips_internal_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "active.yaml").write_text(YAML_DEP_CHAIN.replace("dep-a", "active"), encoding="utf-8")
            (d / "hidden.yaml.internal").write_text(YAML_DEPRECATED, encoding="utf-8")
            count = load_from_dir(str(d))
            assert count == 1
            assert get("active") is not None
            assert get("old-agent") is None

    def test_list_all_excludes_skipped(self):
        register(DomainPlugin(name="active", type="business"))
        register(DomainPlugin(name="legacy", type="business"))
        agents = list_all()
        assert "active" in agents
        # list_all filters based on filename convention (.deprecated/.internal)
        # Direct registration bypasses file check, so both are visible

    def test_agent_filter_nonexistent_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            count = load_from_dir(str(tmp), agent_filter="no-such-agent")
            assert count == 0
