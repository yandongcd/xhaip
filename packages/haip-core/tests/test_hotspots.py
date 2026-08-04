"""无测试热点补测 — 高连接度函数 (图谱 degree≥49) 覆盖.

evaluate_htn (49) / high_risk_pattern (50) / complication_scan (62)
/ risk_screening (55) / _get_nested (79)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital" / "modules"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))


class TestEvaluateHtn:
    """cardio_risk.evaluate_htn — 高血压分级边界 (中国高血压指南 2024)."""

    def _bp(self, sbp, dbp):
        from cardio_risk import evaluate_htn
        r = evaluate_htn(sbp=sbp, dbp=dbp)
        assert r["status"] == "ok"
        return r["bp_classification"]

    def test_ish_140_89(self):
        c = self._bp(145, 80)
        assert c["grade"] == "ISH"
        assert c["level"] == 1

    def test_grade1_boundary(self):
        c = self._bp(140, 95)
        assert c["level"] == 1

    def test_grade2_160(self):
        c = self._bp(160, 90)
        assert c["level"] == 2
        assert "2 级" in c["grade_cn"]

    def test_grade3_180(self):
        c = self._bp(180, 95)
        assert c["level"] == 3
        assert "3 级" in c["grade_cn"]

    def test_normal_high_value(self):
        c = self._bp(135, 85)
        assert c["grade"] == "正常高值"

    def test_normal(self):
        c = self._bp(110, 70)
        assert c["grade"] == "正常"


class TestHighRiskPattern:
    """hypertension_screening.high_risk_pattern — 13 种继发高危模式."""

    def test_p001_returns_ok(self):
        from hypertension_screening import high_risk_pattern
        r = high_risk_pattern(patient_id="P001")
        assert r["status"] == "ok"
        assert "matched_patterns" in r
        assert isinstance(r["matched_patterns"], list)

    def test_returns_structured_fields(self):
        from hypertension_screening import high_risk_pattern
        r = high_risk_pattern(patient_id="P001")
        for key in ("risk_level", "total_score", "urgency"):
            assert key in r, f"缺字段 {key}: {r.keys()}"

    def test_missing_patient_errors(self):
        from hypertension_screening import high_risk_pattern
        r = high_risk_pattern(patient_id="NO_SUCH_PATIENT")
        assert r["status"] == "error"


class TestComplicationScan:
    """pacer.complication_scan — 术后 10 系统并发症扫描 (vital_signs 键: heart_rate/temperature/sbp/spo2)."""

    def test_ok_with_normal_vitals(self):
        from pacer import complication_scan
        r = complication_scan(
            patient_id="P001", postop_day=1,
            vital_signs={"heart_rate": 75, "sbp": 120, "dbp": 80, "spo2": 97, "temperature": 36.8},
        )
        assert r["status"] == "ok"
        assert isinstance(r["alerts"], list)

    def test_shock_combination_triggers(self):
        """SBP<90 + HR>110 血流动力学不稳定 → 术后出血 MTP 告警 (独立于 Hb)."""
        from pacer import complication_scan
        r = complication_scan(
            patient_id="P001", postop_day=1,
            vital_signs={"heart_rate": 115, "sbp": 80, "dbp": 50, "spo2": 96, "temperature": 37.0},
        )
        assert r["status"] == "ok"
        assert any("MTP" in a or "血流动力学" in a for a in r["alerts"]), f"休克组合未触发: {r['alerts']}"
        assert r["total_complications"] >= 1

    def test_drainage_high_triggers(self):
        from pacer import complication_scan
        r = complication_scan(
            patient_id="P001", postop_day=1,
            vital_signs={"heart_rate": 75, "sbp": 120, "dbp": 80, "spo2": 97, "temperature": 36.8},
            drainage_ml=260.0, drainage_color="鲜红",
        )
        assert len(r["alerts"]) >= 1 or r["total_complications"] >= 1


class TestRiskScreening:
    """oncology_cycle.risk_screening — 化疗相关风险初筛."""

    def test_ok(self):
        from oncology_cycle import risk_screening
        r = risk_screening(patient_id="P001", treatment_type="chemotherapy")
        assert r["status"] == "ok"

    def test_returns_risk_dimensions(self):
        from oncology_cycle import risk_screening
        r = risk_screening(patient_id="P001")
        assert any(k in r for k in ("risks", "dimensions", "bone_marrow", "assessment")), r.keys()


class TestGetNested:
    """respiratory._get_nested — 扁平键遍历 + 别名兜底 (degree 79 工具函数)."""

    def test_flat_lookup(self):
        from respiratory import _get_nested
        p = {"lab_results": {"k": 3.5}, "age": 78}
        assert _get_nested(p, "k") == 3.5
        assert _get_nested(p, "age") == 78

    def test_alias_fallback(self):
        from respiratory import _get_nested
        p = {"lab_results": {"potassium": 3.2}}
        assert _get_nested(p, "k", "potassium") == 3.2

    def test_default_when_missing(self):
        from respiratory import _get_nested
        p = {"lab_results": {"x": 1}}
        assert _get_nested(p, "missing", default=0) == 0

    def test_vitals_and_top_level(self):
        from respiratory import _get_nested
        p = {"vitals": {"hr": 90}, "bmi": 24.5}
        assert _get_nested(p, "hr") == 90
        assert _get_nested(p, "bmi") == 24.5
