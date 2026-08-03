"""Tests for clinical modules — nutrition + drug compatibility."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from haip.clinical.drug_compat import CompatibilityResult, check_cation_limits, check_compatibility
from haip.clinical.nutrition import NRS2002Result
from haip.clinical.nutrition import assess as nrs2002


class TestNRS2002:
    def test_low_risk(self):
        r = nrs2002(age=45, bmi=24.0, nutrition_status="正常", disease_severity="无")
        assert r.total_score == 0
        assert r.risk_level == "低风险"

    def test_moderate_risk_with_disease(self):
        r = nrs2002(age=45, bmi=22.0, nutrition_status="正常", disease_severity="中度应激")
        assert r.total_score == 2
        assert r.risk_level == "低风险"

    def test_moderate_risk(self):
        r = nrs2002(age=45, bmi=19.0, nutrition_status="中度", disease_severity="无")
        assert r.total_score == 2
        assert r.risk_level == "低风险"

    def test_high_risk_total_3(self):
        r = nrs2002(age=45, bmi=19.0, nutrition_status="中度", disease_severity="轻度应激")
        assert r.total_score == 3
        assert r.risk_level == "中度风险"

    def test_high_risk_total_5(self):
        r = nrs2002(age=70, bmi=17.5, nutrition_status="重度", disease_severity="重度应激")
        assert r.total_score >= 5
        assert r.risk_level == "高风险"
        assert r.age_bonus == 1

    def test_age_bonus_under_70(self):
        r = nrs2002(age=65, bmi=22.0, nutrition_status="正常", disease_severity="无")
        assert r.age_bonus == 0

    def test_age_bonus_over_70(self):
        r = nrs2002(age=75, bmi=22.0, nutrition_status="正常", disease_severity="无")
        assert r.age_bonus == 1

    def test_auto_disease_from_diagnosis(self):
        r = nrs2002(age=65, bmi=22.0, diagnosis="髋部骨折")
        assert r.disease_score >= 1

    def test_auto_disease_critical(self):
        r = nrs2002(age=65, bmi=22.0, diagnosis="严重烧伤")
        assert r.disease_score >= 3

    def test_bmi_low_override(self):
        r = nrs2002(age=50, bmi=17.0, nutrition_status="正常", disease_severity="无")
        assert r.nutrition_score >= 3

    def test_intake_reduction(self):
        r = nrs2002(age=50, bmi=22.0, nutrition_status="正常", disease_severity="无", intake_reduction="75-100%")
        assert r.nutrition_score >= 3

    def test_weight_loss_auto_detect(self):
        r = nrs2002(age=50, bmi=22.0, disease_severity="无", weight_loss_1m_pct=6.0)
        assert r.nutrition_score >= 2

    def test_recommendation_contains_action(self):
        r = nrs2002(age=70, bmi=17.0, nutrition_status="重度", disease_severity="重度应激")
        assert "营养支持" in r.recommendation
        assert r.risk_level == "高风险"


class TestDrugCompatibility:
    def test_no_conflict(self):
        r = check_compatibility(["头孢曲松", "氯化钠"])
        assert r.safe

    def test_calcium_phosphate(self):
        r = check_compatibility(["葡萄糖酸钙", "甘油磷酸钠"])
        assert not r.safe
        assert any("DI001" in v for v in r.violations)

    def test_insulin_fat_emulsion(self):
        r = check_compatibility(["胰岛素", "脂肪乳"])
        assert not r.safe
        assert any("DI007" in v for v in r.violations)

    def test_fat_emulsion_warning(self):
        r = check_compatibility(["脂肪乳", "维生素C"])
        assert r.safe  # No direct conflict
        assert any("一价阳离子" in w for w in r.warnings)

    def test_multiple_drugs(self):
        r = check_compatibility(["葡萄糖酸钙", "甘油磷酸钠", "胰岛素", "脂肪乳"])
        assert not r.safe
        assert len(r.violations) >= 1

    def test_vitamin_k_warfarin(self):
        r = check_compatibility(["维生素K", "华法林"])
        assert not r.safe
        assert any("DI003" in v for v in r.violations)

    def test_cation_limits_safe(self):
        r = check_cation_limits(sodium_mmol=100, potassium_mmol=30, calcium_mmol=5, magnesium_mmol=3)
        assert r["safe"]
        assert r["monovalent_total"] == 130
        assert r["divalent_total"] == 8

    def test_cation_limits_exceeded(self):
        r = check_cation_limits(sodium_mmol=140, potassium_mmol=20, calcium_mmol=8, magnesium_mmol=5)
        assert not r["safe"]
        assert len(r["warnings"]) >= 1

    def test_cation_limits_divalent(self):
        r = check_cation_limits(sodium_mmol=50, potassium_mmol=30, calcium_mmol=10, magnesium_mmol=5)
        assert not r["safe"]
        assert r["divalent_total"] > 10

    def test_recommendations_include_sequence(self):
        r = check_compatibility(["葡萄糖酸钙", "甘油磷酸钠"])
        assert any("配制顺序" in rec or "磷酸盐" in rec for rec in r.recommendations)
