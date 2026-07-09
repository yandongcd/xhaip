"""测试 A2A 调用药剂科业务函数 (端到端)."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
# handler 路径 pharmacy.assessment 需要 modules/pharmacy/assessment 可被导入
sys.path.insert(0, str(project_root / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))
sys.path.insert(0, str(project_root / "packages" / "haip-core"))

from haip.a2a import call, clear_history, get_history  # noqa: E402
from haip.agent import register, DomainPlugin, ToolDef, _registry  # noqa: E402

YAML_DIR = project_root / "packages" / "haip-hospital" / "agents" / "definitions"


# 药剂科 handler 路径 -> 实际模块路径映射
# YAML: pharmacy.assessment.nutrition_risk -> 实际: pharmacy.assessment.assess_nutrition_risk
# 测试中直接注册 handler 路径到实际函数
PHARMACY_HANDLERS = {
    "assess_nutrition": "pharmacy.assessment.assess_nutrition_risk",
    "calculate_tpn": "pharmacy.handlers.calculate_tpn",  # 暂未实现
    "review_prescription": "pharmacy.handlers.review_prescription",
    "recommend_nutrition_route": "pharmacy.handlers.recommend_nutrition_route",
    "list_medications": "pharmacy.handlers.list_medications",
}


class TestPharmacyA2ACalls:
    def setup_method(self):
        _registry.clear()
        clear_history()

    def test_assess_nutrition_via_a2a(self):
        """通过 A2A dispatcher 调用营养风险评估。"""
        register(DomainPlugin(
            name="pharmacy", type="business", port=8770,
            tools=[
                ToolDef(name="assess_nutrition", description="营养风险",
                        handler="pharmacy.assessment.assess_nutrition_risk",
                        input={"patient_id": "str", "weight_kg": "float", "height_cm": "float"}),
            ],
        ))
        result = call("pharmacy", "assess_nutrition", {
            "patient_id": "P001", "weight_kg": 55.0, "height_cm": 170.0,
            "lab_results": {"albumin": 28.0, "crp": 60.0}, "age": 75,
        })
        assert result["status"] == "ok"
        assert result["risk_level"] == "高"
        assert result["nrs_score"] >= 5
        assert len(result["recommendations"]) >= 2
        assert "立即启动营养支持" in str(result["recommendations"])

    def test_assess_nutrition_normal(self):
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[
                ToolDef(name="assess_nutrition", description="",
                        handler="pharmacy.assessment.assess_nutrition_risk"),
            ],
        ))
        result = call("pharmacy", "assess_nutrition", {
            "patient_id": "P002", "weight_kg": 75.0, "height_cm": 175.0,
            "lab_results": {"albumin": 42.0, "crp": 3.0}, "age": 40,
        })
        assert result["status"] == "ok"
        assert result["risk_level"] == "低"
        assert result["nrs_score"] <= 2

    def test_assess_nutrition_electrolyte_abnormal(self):
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[
                ToolDef(name="assess_nutrition", description="",
                        handler="pharmacy.assessment.assess_nutrition_risk"),
            ],
        ))
        result = call("pharmacy", "assess_nutrition", {
            "patient_id": "P003", "weight_kg": 65.0, "height_cm": 168.0,
            "lab_results": {"albumin": 38.0, "crp": 10.0, "k": 3.0, "na": 130.0},
            "age": 55,
        })
        assert result["status"] == "ok"
        assert not result["electrolytes_ok"]
        assert any("钠" in r or "钾" in r for r in result["recommendations"])

    def test_call_history_tracks_success(self):
        register(DomainPlugin(
            name="pharmacy", type="business",
            tools=[
                ToolDef(name="assess_nutrition", description="",
                        handler="pharmacy.assessment.assess_nutrition_risk"),
            ],
        ))
        call("pharmacy", "assess_nutrition", {
            "patient_id": "P001", "weight_kg": 70.0, "height_cm": 165.0,
        })
        history = get_history()
        assert len(history) == 1
        assert history[0]["status"] == "ok"
        assert history[0]["agent"] == "pharmacy"
        assert history[0]["tool"] == "assess_nutrition"
        assert history[0]["elapsed_ms"] >= 0
