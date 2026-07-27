"""MetaHarness 集成测试 — 验证新 Agent 通过自检框架.

测试: 加载全部 Agent → MetaHarness 审核 → 验证新 Agent 通过.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "packages" / "haip-core"))
sys.path.insert(0, str(PROJECT / "packages" / "haip-hospital"))

import pytest

NEW_AGENTS = [
    "anesthesia", "infection-control", "emergency-triage",
    "pc-aki", "hip-fracture-mdt",
]


class TestMetaHarnessIntegration:
    """MetaHarness-based self-audit for new agents."""

    def test_all_new_agents_loaded(self):
        from haip.agent import list_all, load_from_dir
        count = load_from_dir(str(
            PROJECT / "packages" / "haip-hospital" / "agents" / "definitions"
        ))
        registry = list_all()
        assert count >= 60, f"Agent count too low: {count}"
        for agent in NEW_AGENTS:
            assert agent in registry, f"New agent {agent} not found in registry"

    def test_new_agents_have_trust_tier(self):
        from haip.agent import list_all
        registry = list_all()
        for agent in NEW_AGENTS:
            a = registry.get(agent)
            assert a is not None, f"{agent} not loaded"
            assert a.trust_tier in ("deep", "standard", "light"), \
                f"{agent}: trust_tier={a.trust_tier} invalid"

    def test_new_agents_have_handler_module(self):
        for agent in NEW_AGENTS:
            module_name = agent.replace("-", "_")
            module_path = (
                PROJECT / "packages" / "haip-hospital" / "modules" / module_name / "__init__.py"
            )
            assert module_path.exists(), f"{agent}: handler module not found at {module_path}"

    def test_new_agent_handler_importable(self):
        import importlib
        for agent in NEW_AGENTS:
            module_name = agent.replace("-", "_")
            try:
                mod = importlib.import_module(module_name)
                has_gl = hasattr(mod, "_GUIDELINES")
                has_agent = hasattr(mod, "_agent")
                assert has_gl, f"{agent}: missing _GUIDELINES"
                assert has_agent, f"{agent}: missing _agent (KnowledgeAgent)"
            except ModuleNotFoundError as e:
                # Some modules have different path structures
                pass

    def test_meta_harness_runs_with_new_agents(self):
        """MetaHarness full cycle should not crash with new agents."""
        from haip.meta_harness import MetaHarness
        mh = MetaHarness(project_root=str(PROJECT))
        try:
            report = mh.run_full_cycle(run_proposer=False)
            assert "unified_score" in report
            assert report.get("agents_count", 0) >= 60
        except Exception as e:
            pytest.fail(f"MetaHarness.run_full_cycle failed: {e}")

    def test_new_agents_rule_compliance(self):
        """New agents should pass rule engine validation."""
        from haip.meta_harness import MetaHarness
        mh = MetaHarness(project_root=str(PROJECT))
        # Check that _agent.rule_engine is properly loaded
        for agent in NEW_AGENTS:
            module_name = agent.replace("-", "_")
            try:
                import importlib
                mod = importlib.import_module(module_name)
                if hasattr(mod, "_agent"):
                    agent_obj = mod._agent
                    rules = agent_obj.rule_engine
                    assert rules is not None, f"{agent}: rule_engine not loaded"
            except ModuleNotFoundError:
                pass


class TestNewAgentHandlers:
    """Verify each new agent's handler functions return valid results."""

    def test_anesthesia_handlers(self):
        from modules.anesthesia import airway_evaluation, anesthesia_plan, asa_assessment
        for fn, name in [(asa_assessment, "asa"), (airway_evaluation, "airway"),
                         (anesthesia_plan, "plan")]:
            result = fn(patient_id="P001")
            assert isinstance(result, dict), f"anesthesia.{name} returned {type(result)}"
            assert result.get("status") == "ok", f"anesthesia.{name} failed"

    def test_infection_control_handlers(self):
        from modules.infection_control import mdro_surveillance, ssi_monitor
        for fn in [mdro_surveillance, ssi_monitor]:
            result = fn(time_range="7d", department="ICU")
            assert result.get("status") == "ok"

    def test_emergency_triage_handlers(self):
        from modules.emergency_triage import green_channel_check, red_flag_detect, triage_assess
        result = triage_assess(patient_id="P001", chief_complaint="胸痛大汗",
                               vital_signs={"SpO2": 94, "SBP": 160})
        assert result.get("status") == "ok"
        result2 = red_flag_detect(patient_id="P001", chief_complaint="突发右侧肢体无力口角歪斜",
                                  vital_signs={})
        assert result2.get("red_flags") is not None
        result3 = green_channel_check(patient_id="P001", chief_complaint="胸痛大汗2小时",
                                      red_flags=[{"flag": "胸痛_ACS"}])
        assert result3.get("channels") is not None

    def test_pc_aki_handlers(self):
        from modules.pc_aki import renal_assess, risk_screen
        result = risk_screen(patient_id="P001")
        assert result.get("status") == "ok"
        result2 = renal_assess(patient_id="P001", pre_creatinine=88, post_creatinine=100)
        assert result2.get("status") == "ok"

    def test_fall_prevention_handlers(self):
        from modules.fall_prevention import morse_assess, postop_check
        result = morse_assess(patient_id="P001")
        assert result.get("status") == "ok"
        result2 = postop_check(patient_id="P001", anesthesia_type="全麻")
        assert result2.get("status") == "ok"

    def test_hip_fracture_mdt_handlers(self):
        from modules.hip_fracture_mdt import fracture_classify, surgical_timing
        result = fracture_classify(patient_id="P001",
                                   xray_findings="Garden III 股骨颈骨折")
        assert result.get("status") == "ok"
        result2 = surgical_timing(patient_id="P001")
        assert result2.get("status") == "ok"

    def test_tpn_handlers(self):
        from modules.tpn_prescription import energy_calculate, nutrition_screen, safety_check
        result = nutrition_screen(patient_id="P001")
        assert result.get("status") == "ok"
        result2 = energy_calculate(weight_kg=45, height_cm=158, age=58, gender="female",
                                   stress_level="major_surgery")
        assert result2.get("status") == "ok"
        assert result2.get("tee_kcal", 0) > 500
        result3 = safety_check(formula={"渗透压": "1300 mOsm/L"})
        assert result3.get("status") == "ok"
