"""
围术期止吐药智能体 — 单元测试

覆盖：
  - scoring_engine: Apfel/POVOC/PDNV 评分
  - drug_recommend: 用药方案推荐 + 补救
  - drug_controls: 7 类禁忌证筛查
  - anesthesia_guide: 麻醉管理
  - nondrug_guide: 非药物干预
  - drug_db: 药品数据库
  - pipeline: BP 编排
"""

import pytest
from pharmacy.antiemetic import (
    anesthesia_guide,
    drug_controls,
    drug_db,
    drug_recommend,
    nondrug_guide,
    pipeline,
    scoring_engine,
)


# ════════════════════════════════════════════
# scoring_engine 测试
# ════════════════════════════════════════════
class TestApfelScore:
    def test_apfel_score_0(self):
        """低风险：0个危险因素"""
        r = scoring_engine.calculate_apfel_score(
            gender="M", smoking="是", ponv_history="无",
            motion_sickness="无", opioid_planned="否",
        )
        assert r["score"] == 0
        assert r["risk_level"] == "low"
        assert r["probability_pct"] == 10

    def test_apfel_score_2(self):
        """中风险：2个危险因素"""
        r = scoring_engine.calculate_apfel_score(
            gender="F", smoking="是", ponv_history="无",
            motion_sickness="无", opioid_planned="是",
        )
        assert r["score"] == 2
        assert r["risk_level"] == "medium"
        assert r["probability_pct"] == 39

    def test_apfel_score_4(self):
        """高风险：4个危险因素 — 全中"""
        r = scoring_engine.calculate_apfel_score(
            gender="F", smoking="否", ponv_history="有",
            motion_sickness="有", opioid_planned="是",
        )
        assert r["score"] == 4
        assert r["risk_level"] == "high"
        assert r["probability_pct"] == 79
        assert len(r["factors"]) == 4

    def test_apfel_score_female_variants(self):
        """女性/女/F 都应识别"""
        r1 = scoring_engine.calculate_apfel_score(gender="女")
        r2 = scoring_engine.calculate_apfel_score(gender="F")
        r3 = scoring_engine.calculate_apfel_score(gender="女性")
        assert r1["score"] >= 1
        assert r2["score"] >= 1
        assert r3["score"] >= 1


class TestPOVOCScore:
    def test_povoc_score_0(self):
        """低风险：0个危险因素"""
        r = scoring_engine.calculate_povoc_score(
            age=1, surgery_duration_min=20,
            opioid_used="否", ponv_history="无",
        )
        assert r["score"] == 0
        assert r["risk_level"] == "low"

    def test_povoc_score_2(self):
        """中风险：2个危险因素"""
        r = scoring_engine.calculate_povoc_score(
            age=4, surgery_duration_min=35,
            opioid_used="否", ponv_history="无",
        )
        assert r["score"] == 2
        assert r["risk_level"] == "medium"

    def test_povoc_score_4(self):
        """高风险：4个危险因素"""
        r = scoring_engine.calculate_povoc_score(
            age=7, surgery_duration_min=60,
            opioid_used="是", ponv_history="有",
        )
        assert r["score"] == 4
        assert r["risk_level"] == "high"
        assert r["probability_pct"] == 70


class TestPDNVScore:
    def test_pdnv_score_high(self):
        r = scoring_engine.calculate_pdnv_score(
            gender="F", age=30, ponv_history="有",
            pacu_opioid="是", pacu_nausea="是",
        )
        assert r["score"] >= 3
        assert r["probability_pct"] >= 50


# ════════════════════════════════════════════
# drug_recommend 测试
# ════════════════════════════════════════════
class TestDrugRecommend:
    def test_adult_low_risk(self):
        r = drug_recommend.recommend_regimen_adult(risk_level="low")
        assert r["tier"] == "单药预防"
        assert len(r["drugs"]) == 1

    def test_adult_high_risk(self):
        r = drug_recommend.recommend_regimen_adult(risk_level="high")
        assert r["tier"] == "三联用药预防"
        assert len(r["drugs"]) == 3
        # 第一联应为帕洛诺司琼（长效）
        assert r["drugs"][0]["name"] == "帕洛诺司琼"

    def test_rescue_no_prophylaxis(self):
        r = drug_recommend.recommend_rescue(prior_prophylaxis=False)
        assert "未接受预防" in r["scenario"]
        assert "昂丹司琼" in str(r["recommendation"])
        assert r["recommendation"]["first_line"]["options"][0]["dose"] == "1mg"

    def test_rescue_triple_6h(self):
        r = drug_recommend.recommend_rescue(
            prior_prophylaxis=True,
            hours_since_prophylaxis=3,
            triple_therapy_used=True,
        )
        assert "6h内不重复" in r["recommendation"]

    def test_rescue_after_6h(self):
        r = drug_recommend.recommend_rescue(
            prior_prophylaxis=True,
            hours_since_prophylaxis=8,
        )
        assert "可重复" in r["recommendation"]


# ════════════════════════════════════════════
# drug_controls 测试
# ════════════════════════════════════════════
class TestDrugControls:
    def test_clean_patient_passes(self):
        r = drug_controls.validate_contraindications(
            regimen={"drugs": [{"name": "昂丹司琼", "class": "5-HT3受体拮抗剂"}]},
            patient={"age": 35, "allergies": [], "comorbidities": [], "labs": {}},
        )
        assert r["passed"] is True

    def test_q_qt_prolongation_droperidol(self):
        r = drug_controls.validate_contraindications(
            regimen={"drugs": [{"name": "氟哌利多", "class": "多巴胺受体拮抗剂"}]},
            patient={
                "age": 55, "gender": "F",
                "allergies": [], "comorbidities": [],
                "labs": {"qtc": 500},
            },
        )
        assert r["passed"] is False
        assert r["high_severity_count"] >= 1

    def test_parkinson_dopamine_block(self):
        r = drug_controls.validate_contraindications(
            regimen={"drugs": [{"name": "甲氧氯普胺", "class": "多巴胺受体拮抗剂"}]},
            patient={
                "age": 65, "allergies": [],
                "comorbidities": ["帕金森"],
                "labs": {},
            },
        )
        assert r["passed"] is False

    def test_elderly_anticholinergic_block(self):
        r = drug_controls.validate_contraindications(
            regimen={"drugs": [{"name": "戊乙奎醚", "class": "抗胆碱能药"}]},
            patient={
                "age": 70, "allergies": [],
                "comorbidities": [], "labs": {},
            },
        )
        assert r["passed"] is False
        assert r["high_severity_count"] >= 1

    def test_pregnancy_dopamine_block(self):
        r = drug_controls.validate_contraindications(
            regimen={"drugs": [{"name": "氟哌利多", "class": "多巴胺受体拮抗剂"}]},
            patient={
                "age": 30, "gender": "F",
                "allergies": [], "comorbidities": [],
                "labs": {}, "pregnancy": True,
            },
        )
        assert r["passed"] is False


# ════════════════════════════════════════════
# anesthesia_guide 测试
# ════════════════════════════════════════════
class TestAnesthesiaGuide:
    def test_tiva_high_risk(self):
        r = anesthesia_guide.recommend_tiva(risk_level="high")
        assert r["tiva_recommended"] is True
        assert r["recommendation_level"] == "strong"

    def test_tiva_low_risk(self):
        r = anesthesia_guide.recommend_tiva(risk_level="low")
        assert r["recommendation_level"] == "consider"

    def test_pnb_breast_surgery(self):
        r = anesthesia_guide.recommend_pnb(surgery_type="breast_surgery")
        assert "SAPB" in r["pnb_type"]
        assert r["pnb_recommended"] is True

    def test_fluid_long_surgery(self):
        r = anesthesia_guide.recommend_fluid_therapy(surgery_duration_min=200)
        assert r["fluid_type"] == "胶体液优先"

    def test_dexmedetomidine_bradycardia(self):
        r = anesthesia_guide.recommend_dexmedetomidine(
            patient={"hr": 45}
        )
        assert r["dexmedetomidine_recommended"] is False


# ════════════════════════════════════════════
# nondrug_guide 测试
# ════════════════════════════════════════════
class TestNonDrugGuide:
    def test_acupoint_high_risk(self):
        r = nondrug_guide.recommend_acupoint(risk_level="high")
        assert r["acupoint_recommended"] is True
        assert any("合谷" in a for a in r["acupoints"])

    def test_carbs_diabetic(self):
        r = nondrug_guide.recommend_preop_carbs(
            patient={"diabetic": True}
        )
        assert r["carbs_recommended"] is False

    def test_carbs_obese(self):
        r = nondrug_guide.recommend_preop_carbs(
            patient={"bmi": 32}
        )
        assert r["carbs_recommended"] is False

    def test_lifestyle_postop(self):
        r = nondrug_guide.recommend_lifestyle(postoperative=True)
        assert r["total"] >= 3
        has_gum = any(i["type"] == "咀嚼口香糖" for i in r["interventions"])
        assert has_gum is True


# ════════════════════════════════════════════
# drug_db 测试
# ════════════════════════════════════════════
class TestDrugDB:
    def test_search_by_class(self):
        r = drug_db.search_drug(drug_class="5-HT3受体拮抗剂")
        assert r["total"] >= 6

    def test_search_ondansetron(self):
        r = drug_db.search_drug(keyword="昂丹司琼")
        assert r["total"] == 1

    def test_list_classes(self):
        r = drug_db.list_drug_classes()
        assert "5-HT3受体拮抗剂" in r["classes"]
        assert "NK-1受体拮抗剂" in r["classes"]

    def test_get_profile(self):
        r = drug_db.get_drug_profile(drug_name="帕洛诺司琼")
        assert r["status"] == "ok"
        assert r["drug"]["half_life_h"] == 40


# ════════════════════════════════════════════
# pipeline 集成测试
# ════════════════════════════════════════════
class TestPipeline:
    def test_bp_risk_scoring_adult(self):
        r = pipeline.bp_preop_risk_scoring(
            patient={"age": 45, "gender": "F", "smoking": False, "ponv_history": True},
            surgery={"opioid_planned": True},
        )
        assert r["risk_assessment"]["risk_level"] == "high"
        assert r["status"] == "ok"

    def test_bp_drug_prophylaxis(self):
        r = pipeline.bp_drug_prophylaxis(
            patient={"age": 35, "allergies": [], "comorbidities": [], "labs": {}},
            risk_level="medium",
            risk_score=2,
        )
        assert r["regimen"]["tier"] == "二联用药预防"
        assert r["validation"]["passed"] is True

    def test_bp_anesthesia_optimization(self):
        r = pipeline.bp_anesthesia_optimization(
            patient={"hr": 72},
            surgery={"type": "breast_surgery", "duration_min": 120},
            risk_level="high",
        )
        assert r["tiva"]["tiva_recommended"] is True
        assert r["pnb"]["pnb_recommended"] is True

    def test_bp_nondrug_intervention(self):
        r = pipeline.bp_nondrug_intervention(
            patient={"age": 35},
            risk_level="high",
            drug_contraindications=True,
        )
        assert r["acupoint"]["acupoint_recommended"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
