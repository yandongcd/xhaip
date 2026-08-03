"""A2A behavioural tests for 15 expanded/new agents — positive + negative + boundary.

Pattern: test internal engines directly (unit) or handler functions (A2A).
Each agent: ≥2 functions, ≥3 scenarios (positive / negative / boundary).
"""
from __future__ import annotations

import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# INF-Agent v2.0 (infection diagnosis + sepsis)
# ══════════════════════════════════════════════════════════════

class TestInfAgent:
    """INF-Agent: infection_type, sepsis_screening, test_recommend, antimicrobial_advice."""

    def test_infection_type_bacterial_septic(self):
        from modules.inf_agent import _calc_infection_prob
        r = _calc_infection_prob(pct=15, wbc=18, crp=150, neut_pct=90, lymph_pct=8,
                                 il6=200, lactate=5, g_test=False, gm_test=False,
                                 immunosuppressed=False, abx_history=True)
        assert r["probabilities"]["bacterial"] > 50

    def test_infection_type_healthy_noninfectious(self):
        from modules.inf_agent import _calc_infection_prob
        r = _calc_infection_prob(pct=0.1, wbc=7, crp=5, neut_pct=60, lymph_pct=30,
                                 il6=10, lactate=1, g_test=False, gm_test=False,
                                 immunosuppressed=False, abx_history=False)
        assert r["probabilities"]["non_infectious"] > r["probabilities"]["bacterial"]

    def test_infection_type_fungal_immunosuppressed(self):
        from modules.inf_agent import _calc_infection_prob
        r = _calc_infection_prob(pct=1.0, wbc=3, crp=30, neut_pct=40, lymph_pct=15,
                                 il6=40, lactate=1.5, g_test=True, gm_test=True,
                                 immunosuppressed=True, abx_history=True)
        assert r["probabilities"]["fungal"] > 20

    def test_sepsis_screening_sirs_positive(self):
        from modules.inf_agent import _sirs_criteria
        r = _sirs_criteria({"wbc": 15, "bands_pct": 12}, {"temperature": 39, "heart_rate": 100, "respiratory_rate": 24})
        assert r["positive"] is True

    def test_sepsis_screening_qsofa_negative(self):
        from modules.inf_agent import _qsofa
        r = _qsofa({"respiratory_rate": 16, "sbp": 120, "gcs": 15})
        assert r["positive"] is False

    def test_organ_flags_normal_umol_no_aki(self):
        """C4 回归: Cr=95.7μmol/L (≈1.08mg/dL) + TBil=9.2μmol/L 不得再误报 AKI/高胆红素."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"Cr": 95.7, "TBil": 9.2, "lactate": 1.5, "PLT": 200})
        assert all("急性肾损伤" not in f and "高胆红素血症" not in f for f in flags)

    def test_organ_flags_no_baseline_screening_note(self):
        """无基线时 Cr=250μmol/L (2.83mg/dL) 不得再报 AKI — 降级为肾功能异常筛查提示."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"Cr": 250, "TBil": 25, "lactate": 2.5, "PLT": 85})
        joined = " ".join(flags)
        assert "急性肾损伤" not in joined
        assert "肾功能异常" in joined
        assert "高胆红素血症" in joined
        assert "高乳酸血症" in joined
        assert "血小板减少" in joined

    def test_organ_flags_with_baseline_kdigo_aki(self):
        """有基线 (scr_baseline) 时按 KDIGO 相对标准: Cr/基线=250/150=1.67≥1.5 → AKI 1期."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"Cr": 250, "scr_baseline": 150})
        joined = " ".join(flags)
        assert "急性肾损伤" in joined
        assert "肾功能异常" not in joined

    def test_organ_flags_with_baseline_kdigo_boundary(self):
        """KDIGO 边界: Cr/基线=225/150=1.5 精确命中; 223.5/150=1.49 不命中."""
        from modules.inf_agent import _organ_dysfunction_flags
        assert "急性肾损伤" in " ".join(_organ_dysfunction_flags({"Cr": 225, "scr_baseline": 150}))
        assert "急性肾损伤" not in " ".join(_organ_dysfunction_flags({"Cr": 223.5, "scr_baseline": 150}))

    def test_organ_flags_with_baseline_no_aki_despite_absolute(self):
        """有基线但 Cr 仅轻度升高 (160/150=1.07<1.5): 即使 Cr>106μmol/L 也不报 AKI/肾功能异常 —
        慢性稳定升高 (如 CKD) 不再被绝对阈值误伤."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"creatinine": 160, "scr_baseline": 150})
        assert all("急性肾损伤" not in f and "肾功能异常" not in f for f in flags)

    def test_organ_flags_patients_v2_pc001(self):
        """patients_v2 PC001 实景: Cr=185/基线=150=1.23<1.5 → 无 AKI (旧绝对阈值会误报)."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"creatinine": 185, "scr_baseline": 150})
        assert all("急性肾损伤" not in f and "肾功能异常" not in f for f in flags)

    def test_organ_flags_lowercase_keys(self):
        """patients_v2 风格小写键同样生效."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"creatinine": 95, "bilirubin": 15})
        assert all("急性肾损伤" not in f and "高胆红素血症" not in f for f in flags)

    def test_organ_flags_missing_creatinine_no_aki(self):
        """肌酐缺失 → 不得误报 AKI."""
        from modules.inf_agent import _organ_dysfunction_flags
        flags = _organ_dysfunction_flags({"TBil": 20})
        assert all("急性肾损伤" not in f for f in flags)

    def test_sepsis_screening_real_patient_no_false_aki(self):
        """真实患者 P374 (Cr=95.7μmol/L, TBil=9.2μmol/L): 不再假阳性 AKI/高胆红素."""
        from modules.inf_agent import sepsis_screening
        r = sepsis_screening(patient_id="P374")
        assert r["status"] == "ok"
        joined = " ".join(str(f) for f in r.get("findings", []))
        assert "急性肾损伤" not in joined
        assert "高胆红素血症" not in joined

    def test_test_recommend_bacterial_respiratory(self):
        from modules.inf_agent import test_recommend
        r = test_recommend(patient_id="P001", suspected_type="bacterial", infection_site="respiratory")
        assert r["status"] == "ok"
        assert len(r.get("tier1_essential", [])) >= 2

    def test_antimicrobial_advice_uti_community(self):
        from modules.inf_agent import antimicrobial_advice
        r = antimicrobial_advice(patient_id="P001", infection_type_val="bacterial", site="urinary", mdro_risk="low")
        assert "头孢曲松" in r["empiric_regimen"] or "呋喃妥因" in r["empiric_regimen"]

    def test_antimicrobial_advice_non_bacterial(self):
        from modules.inf_agent import antimicrobial_advice
        r = antimicrobial_advice(patient_id="P001", infection_type_val="viral", site="respiratory")
        assert "抗生素非首选" in r.get("summary", "")


# ══════════════════════════════════════════════════════════════
# EndoInsight v2.0 (endoscopy + Paris/Forrest/JNET)
# ══════════════════════════════════════════════════════════════

class TestEndoInsight:
    """EndoInsight: report_parse, risk_assessment, post_procedure_plan, followup, patient_education."""

    def test_report_parse_gastric_ulcer_hp_positive(self):
        from modules.endo_insight import report_parse
        r = report_parse(patient_id="P001",
                         report_text="胃窦可见溃疡，Forrest IIa，活检 HP阳性")
        assert r["status"] == "ok"
        assert "溃疡" in str(r.get("findings", {}))
        assert r.get("hp_status") == "阳性"

    def test_report_parse_normal_clean(self):
        from modules.endo_insight import report_parse
        r = report_parse(patient_id="P001", report_text="食管、胃、十二指肠未见明显异常。HP阴性")
        assert r["status"] == "ok"
        assert r.get("hp_status") == "阴性"

    def test_risk_assessment_esd_high_bleed(self):
        from modules.endo_insight import risk_assessment
        r = risk_assessment(patient_id="P001", findings={"ESD": "内镜黏膜下剥离术后"}, procedure_type="esd_emr")
        assert r.get("bleeding_risk") == "高危"

    def test_risk_assessment_diagnostic_low(self):
        from modules.endo_insight import risk_assessment
        r = risk_assessment(patient_id="P001", findings={}, procedure_type="diagnostic")
        assert r.get("bleeding_risk") == "低危"

    def test_followup_adenoma_lgd(self):
        from modules.endo_insight import followup_reminder
        r = followup_reminder(patient_id="P001", pathology="管状腺瘤 低级别")
        assert "5-10年" in r.get("followup_interval", "")

    def test_followup_early_cancer_esd(self):
        from modules.endo_insight import followup_reminder
        r = followup_reminder(patient_id="P001", pathology="ESD 早癌")
        assert "3月" in r.get("followup_interval", "")

    def test_post_procedure_plan_diagnostic(self):
        from modules.endo_insight import post_procedure_plan
        r = post_procedure_plan(patient_id="P001", procedure_type="diagnostic")
        assert r["status"] == "ok"
        assert len(r.get("diet_progression", [])) >= 3

    def test_patient_education_polyp(self):
        from modules.endo_insight import patient_education
        r = patient_education(patient_id="P001", findings={"息肉": "息肉切除"})
        assert len(r.get("explanations", [])) >= 1
        assert len(r.get("when_to_worry", [])) >= 2


# ══════════════════════════════════════════════════════════════
# aHUS Detective v2.0 (TMA + complement + genetic risk)
# ══════════════════════════════════════════════════════════════

class TestAHUSDetective:
    """aHUS: tma_triad, differential_diagnosis, risk_stratify, monitoring_plan."""

    def test_tma_triad_possible(self):
        from modules.ahus_detective import tma_triad
        r = tma_triad(patient_id="P001")
        assert r["status"] == "ok"
        assert "tma_triad" in r

    def test_plasmic_high_ttp_risk(self):
        from modules.ahus_detective import _plasmic_score
        r = _plasmic_score(plt=25, cr=100, inr=1.2, mcv=85, has_cancer=False, has_transplant=False)
        assert r["score"] >= 5

    def test_plasmic_low_risk(self):
        from modules.ahus_detective import _plasmic_score
        r = _plasmic_score(plt=100, cr=200, inr=1.8, mcv=95, has_cancer=True, has_transplant=True)
        assert r["score"] <= 3

    def test_differential_aHUS_low_c3_normal_c4(self):
        from modules.ahus_detective import differential_diagnosis
        r = differential_diagnosis(patient_id="P001", adamts13=60, stec_test="negative",
                                   complement_panel={"C3": 0.5, "C4": 0.2, "sC5b9": 400})
        assert r["status"] == "ok"
        assert "aHUS" in r.get("summary", "")

    def test_differential_ttp_very_low_adamts13(self):
        from modules.ahus_detective import differential_diagnosis
        r = differential_diagnosis(patient_id="P001", adamts13=5, stec_test="negative",
                                   complement_panel={"C3": 1.0, "C4": 0.2, "sC5b9": 200})
        assert "TTP" in r.get("summary", "")

    def test_risk_stratify_cfh_mutation_high(self):
        from modules.ahus_detective import risk_stratify
        r = risk_stratify(patient_id="P001", genetic_results={"CFH_mutation": True}, sc5b9=400)
        assert r.get("overall_risk") is not None
        assert r.get("eculizumab_indicated") is True

    def test_risk_stratify_no_mutation(self):
        from modules.ahus_detective import risk_stratify
        r = risk_stratify(patient_id="P001", genetic_results={}, sc5b9=150)
        assert r["status"] == "ok"


# ══════════════════════════════════════════════════════════════
# PFT v2.0 (pulmonary function: 6 patterns + GOLD + preop)
# ══════════════════════════════════════════════════════════════

class TestPulmonaryFunction:
    """PFT: pft_interpret, gold_staging, bronchodilator_test, preop_assessment."""

    def test_pft_interpret_obstructive(self):
        from modules.pulmonary_function import _classify_ventilation
        r = _classify_ventilation(fev1=1.5, fvc=3.0, fev1_pred=3.0, fvc_pred=3.5,
                                  dlco=80, tlc=5.0, tlc_pred=5.5, age=60)
        assert "阻塞" in r["pattern"]

    def test_pft_interpret_normal(self):
        from modules.pulmonary_function import _classify_ventilation
        r = _classify_ventilation(fev1=3.5, fvc=4.2, fev1_pred=3.5, fvc_pred=4.2,
                                  dlco=90, tlc=5.5, tlc_pred=5.5, age=30)
        assert "正常" in r["pattern"]

    def test_gold_stage1_group_a(self):
        from modules.pulmonary_function import gold_staging
        r = gold_staging(patient_id="P001", fev1_percent=85, exacerbations=0, CAT_score=8, mMRC=1)
        assert r["gold_stage_num"] == 1
        assert r["abg_group"] == "A"

    def test_gold_stage4_group_e(self):
        from modules.pulmonary_function import gold_staging
        r = gold_staging(patient_id="P001", fev1_percent=25, exacerbations=3, CAT_score=25, mMRC=3)
        assert r["gold_stage_num"] == 4
        assert r["abg_group"] == "E"

    def test_bronchodilator_positive(self):
        from modules.pulmonary_function import bronchodilator_test
        r = bronchodilator_test(patient_id="P001", pre_FEV1=1.5, post_FEV1=2.0)
        assert r["bdr_positive"] is True

    def test_bronchodilator_negative(self):
        from modules.pulmonary_function import bronchodilator_test
        r = bronchodilator_test(patient_id="P001", pre_FEV1=2.5, post_FEV1=2.6)
        assert r["bdr_positive"] is False

    def test_lung_age_elderly_smoker(self):
        from modules.pulmonary_function import _lung_age
        age = _lung_age(1.5, 170, "M")
        assert age > 50


# ══════════════════════════════════════════════════════════════
# Autoantibody v2.0 (ANA patterns + EULAR/ACR classification)
# ══════════════════════════════════════════════════════════════

class TestAutoantibody:
    """Autoantibody: pattern_match, trend_track, disease_orientation."""

    def test_pattern_match_sle(self):
        from modules.autoantibody import pattern_match
        r = pattern_match(patient_id="P001", antibodies={"ANA": True, "dsDNA": True, "Sm": True})
        assert r["status"] == "ok"
        matches = r.get("disease_matches", [])
        assert any("SLE" in m.get("disease", "") for m in matches)

    def test_pattern_match_no_antibodies(self):
        from modules.autoantibody import pattern_match
        r = pattern_match(patient_id="P001", antibodies={"ANA": False, "dsDNA": False})
        assert r["status"] == "ok"
        assert len(r.get("positive_antibodies", [])) < 3

    def test_trend_track_significant_rise(self):
        from modules.autoantibody import trend_track
        r = trend_track(patient_id="P001", current_results={"dsDNA": 200},
                        historical_results=[{"dsDNA": 40}])
        assert r.get("clinically_significant") is True

    def test_trend_track_no_history(self):
        from modules.autoantibody import trend_track
        r = trend_track(patient_id="P001", current_results={"dsDNA": 100}, historical_results=[])
        assert len(r.get("changes", [])) == 0

    def test_disease_orientation_sle_primary(self):
        from modules.autoantibody import disease_orientation, pattern_match
        pm = pattern_match(patient_id="P001", antibodies={"ANA": True, "dsDNA": True, "Sm": True})
        r = disease_orientation(patient_id="P001", antibody_pattern=pm)
        assert r["status"] == "ok"
        assert r.get("confidence") in ("高", "中", "低")


# ══════════════════════════════════════════════════════════════
# Breast Imaging v2.0 (BI-RADS + risk + followup)
# ══════════════════════════════════════════════════════════════

class TestBreastImaging:
    """Breast Imaging: birads_classify, risk_predict, followup_recommend."""

    def test_birads_normal(self):
        from modules.breast_imaging import birads_classify
        r = birads_classify(patient_id="P001", findings={}, breast_density="b")
        assert r["birads"] <= 2

    def test_birads_suspicious_spiculated(self):
        from modules.breast_imaging import birads_classify
        r = birads_classify(patient_id="P001",
                            findings={"mass": {"shape": "irregular", "margin": "spiculated", "density": "high_density"}},
                            breast_density="c")
        assert r["birads"] >= 4

    def test_birads_suspicious_calcifications(self):
        from modules.breast_imaging import birads_classify
        r = birads_classify(patient_id="P001",
                            findings={"calcifications": {"morphology": "suspicious_fine_pleomorphic",
                                                         "distribution": "segmental"}},
                            breast_density="c")
        assert r["birads"] >= 4

    def test_risk_predict_brca_positive(self):
        from modules.breast_imaging import risk_predict
        r = risk_predict(patient_id="P001", birads=4, age=35, family_history="first_degree", brca="positive")
        assert r["risk_level"] in ("高危", "极高危")

    def test_risk_predict_low(self):
        from modules.breast_imaging import risk_predict
        r = risk_predict(patient_id="P001", birads=1, age=45)
        assert r["risk_level"] == "一般风险"

    def test_followup_birads3_short_term(self):
        from modules.breast_imaging import followup_recommend
        r = followup_recommend(patient_id="P001", birads=3, breast_density="c")
        assert "6月" in r["primary_recommendation"] or "6" in r.get("next_imaging_interval", "")

    def test_followup_birads5_biopsy(self):
        from modules.breast_imaging import followup_recommend
        r = followup_recommend(patient_id="P001", birads=5)
        assert "活检" in r["primary_recommendation"]


# ══════════════════════════════════════════════════════════════
# Hypertension Screening v2.0 (secondary HTN + ARR + referral)
# ══════════════════════════════════════════════════════════════

class TestHypertensionScreening:
    """HTN Screening: high_risk_pattern, screening_recommend, referral_decision."""

    def test_high_risk_young_low_k(self):
        from modules.hypertension_screening import high_risk_pattern
        r = high_risk_pattern(patient_id="P001")
        assert r["status"] == "ok"
        assert "risk_level" in r

    def test_arr_high_pa_suspected(self):
        from modules.hypertension_screening import _interpret_arr
        r = _interpret_arr(aldosterone=20, renin_pra=0.3, renin_drc=None,
                           post_captopril_ald=None, potassium=3.8)
        assert r["pa_suspected"] is True

    def test_arr_normal(self):
        from modules.hypertension_screening import _interpret_arr
        r = _interpret_arr(aldosterone=8, renin_pra=3.0, renin_drc=None,
                           post_captopril_ald=None, potassium=4.2)
        assert r["pa_suspected"] is False

    def test_referral_high_score(self):
        from modules.hypertension_screening import referral_decision
        r = referral_decision(patient_id="P001", screening_results={"total_score": 8})
        assert "内分泌" in r["referral_decision"] or "专科" in r["referral_decision"]

    def test_referral_low_score(self):
        from modules.hypertension_screening import referral_decision
        r = referral_decision(patient_id="P001", screening_results={"total_score": 1})
        assert "社区" in r["referral_decision"] or "基层" in r["referral_decision"]


# ══════════════════════════════════════════════════════════════
# Elderly CGM v2.0 (glucose monitoring + hypo prediction + insulin)
# ══════════════════════════════════════════════════════════════

class TestElderlyCGM:
    """Elderly CGM: cgm_analysis, hypo_predict, regimen_optimize."""

    def test_cgm_metrics_good_tir(self):
        from modules.elderly_cgm import _cgm_metrics
        r = _cgm_metrics([6.0, 6.5, 7.0, 7.5, 8.0, 6.8, 7.2, 6.5, 7.8, 8.5])
        assert r["tir"] > 50

    def test_cgm_metrics_poor_cv(self):
        from modules.elderly_cgm import _cgm_metrics
        r = _cgm_metrics([3.0, 12.0, 4.0, 15.0, 2.5, 18.0, 5.0, 14.0])
        assert r["cv"] > 30

    def test_hypo_predict_severe_low(self):
        from modules.elderly_cgm import hypo_predict
        r = hypo_predict(patient_id="P001", recent_glucose=[6.0, 5.0, 3.5, 2.8],
                         medications=[{"drug": "胰岛素"}], creatinine=1.0, age=75)
        assert "红" in r.get("risk_tier", "")

    def test_hypo_predict_safe(self):
        from modules.elderly_cgm import hypo_predict
        r = hypo_predict(patient_id="P001", recent_glucose=[7.0, 7.5, 7.8, 8.0],
                         medications=[], creatinine=0.8, age=75)
        assert "绿" in r.get("risk_tier", "")

    def test_elderly_targets_healthy(self):
        from modules.elderly_cgm import _elderly_targets
        r = _elderly_targets(70, "healthy", [])
        assert r["tier"] == "healthy"
        assert "70" in r["targets"]["tir_goal"]

    def test_elderly_targets_very_poor(self):
        from modules.elderly_cgm import _elderly_targets
        r = _elderly_targets(85, "very_poor", ["心衰", "CKD"])
        assert r["tier"] == "very_complex"
        assert "50" in r["targets"]["tir_goal"]

    def test_regimen_optimize_hypo_red(self):
        from modules.elderly_cgm import regimen_optimize
        r = regimen_optimize(patient_id="P001", tir_percent=45, hypo_risk="红 — 立即干预")
        assert "减少" in r.get("summary", "") or "调整" in r.get("summary", "")


# ══════════════════════════════════════════════════════════════
# PACER v2.0 (postop complications + Clavien-Dindo)
# ══════════════════════════════════════════════════════════════

class TestPacer:
    """PACER: complication_scan, risk_predict, escalation."""

    def test_risk_predict_low_baseline(self):
        from modules.pacer import risk_predict
        r = risk_predict(patient_id="P001", surgery_duration=120, blood_loss=200, asa_class=2, age=50)
        assert r["risk_level"] == "低危"

    def test_risk_predict_high_emergency(self):
        from modules.pacer import risk_predict
        r = risk_predict(patient_id="P001", surgery_duration=300, blood_loss=1200,
                         asa_class=4, age=80, emergency=True, contaminated="dirty",
                         albumin_preop=25, copd=True)
        assert r["risk_level"] in ("高危", "极高危")

    def test_escalation_grade_i_routine(self):
        from modules.pacer import escalation
        r = escalation(patient_id="P001", complication_grade="I")
        assert r["needs_emergency_surgery"] is False

    def test_escalation_grade_iiib_surgery(self):
        from modules.pacer import escalation
        r = escalation(patient_id="P001", complication_grade="IIIb")
        assert r["needs_emergency_surgery"] is True
        assert "急诊手术" in str(r.get("actions", []))


# ══════════════════════════════════════════════════════════════
# DrugAgent v2.0 (drug interactions + TDM + Beers + renal dose)
# ══════════════════════════════════════════════════════════════

class TestDrugAgent:
    """DrugAgent: order_audit, medication_reconciliation, adr_alert."""

    def test_order_audit_warfarin_metronidazole_high_severity(self):
        from modules.drug_agent import order_audit
        r = order_audit(patient_id="P001", orders=[{"drug": "华法林"}, {"drug": "甲硝唑"}])
        high = r.get("high_severity_count", 0)
        assert high >= 1

    def test_order_audit_no_interaction(self):
        from modules.drug_agent import order_audit
        r = order_audit(patient_id="P001", orders=[{"drug": "对乙酰氨基酚"}, {"drug": "奥美拉唑"}])
        assert r.get("passed") is True or r.get("high_severity_count", 0) == 0

    def test_order_audit_carbapenem_valproate_contraindicated(self):
        from modules.drug_agent import order_audit
        r = order_audit(patient_id="P001", orders=[{"drug": "碳青霉烯"}, {"drug": "丙戊酸"}])
        assert r.get("high_severity_count", 0) >= 1

    def test_medrec_admission_added_meds(self):
        from modules.drug_agent import medication_reconciliation
        r = medication_reconciliation(patient_id="P001",
                                       source_meds=[{"drug": "A药"}, {"drug": "B药"}],
                                       target_meds=[{"drug": "A药"}, {"drug": "C药"}],
                                       reconciliation_type="admission")
        assert "C药" in r.get("added_meds", [])
        assert "B药" in r.get("stopped_meds", [])

    def test_adr_allergy_check(self):
        from modules.drug_agent import _check_allergy
        r = _check_allergy("青霉素", ["penicillin"])
        assert len(r) >= 1

    def test_renal_dose_metformin_crcl_20(self):
        from modules.drug_agent import _renally_adjusted
        r = _renally_adjusted(20, "metformin")
        assert "禁忌" in r or "减量" in r

    def test_order_audit_crcl_cockcroft_gault_real_patient(self):
        """C4: 真实患者 P001 (62M/43.1kg/Cr=70.4μmol/L) → CrCl≈58.6, 左氧氟沙星按 CrCl 调整."""
        from modules.drug_agent import order_audit
        r = order_audit(patient_id="P001", orders=[{"drug": "左氧氟沙星"}])
        crcl = r.get("crcl")
        assert crcl is not None, "CrCl 应被真实计算"
        assert 50 <= crcl <= 70, f"CrCl={crcl} 超出 CG 预期范围"
        renal_issues = [i for i in r.get("issues", []) if i.get("type") == "肾功能调整"]
        assert len(renal_issues) == 1
        assert renal_issues[0]["crcl"] == crcl

    def test_order_audit_missing_creatinine_no_renal_adjustment(self):
        """C4 回归: 肌酐缺失 (P046 无 Cr) → 数据缺失标记, 绝不进入减量分支."""
        from modules.drug_agent import order_audit
        r = order_audit(patient_id="P046", orders=[{"drug": "左氧氟沙星"}])
        assert r.get("crcl") is None
        assert "缺失" in (r.get("renal_data_note") or "")
        assert all(i.get("type") != "肾功能调整" for i in r.get("issues", []))

    def test_order_audit_missing_patient_no_renal_adjustment(self):
        """患者不存在 → 同样不得以默认 CrCl=1.0 触发最强减量."""
        from modules.drug_agent import order_audit
        r = order_audit(patient_id="P-NOT-EXIST", orders=[{"drug": "二甲双胍"}])
        assert r.get("crcl") is None
        assert all(i.get("type") != "肾功能调整" for i in r.get("issues", []))


# ══════════════════════════════════════════════════════════════
# Bladder Cancer v2.0 (TMT/RC + NMIBC + neoadjuvant)
# ══════════════════════════════════════════════════════════════

class TestBladderCancer:
    """Bladder Cancer: eligibility_score, trimodal_comparison, guideline_reference."""

    def test_eligibility_t2_n0_eligible(self):
        from modules.bladder_cancer import eligibility_score
        r = eligibility_score(patient_id="P001", T_stage="T2", N_status="N0")
        assert r.get("tmt_eligible") is True

    def test_eligibility_t4b_n2_ineligible(self):
        from modules.bladder_cancer import eligibility_score
        r = eligibility_score(patient_id="P001", T_stage="T4b", N_status="N2",
                              hydronephrosis="bilateral", CIS_extensive="extensive")
        assert r.get("tmt_eligible") is False

    def test_guideline_nmibc_high(self):
        from modules.bladder_cancer import guideline_reference
        r = guideline_reference(clinical_scenario="nmibc_high")
        assert "BCG" in r.get("guidelines", {}).get("EAU 2024", "")

    def test_guideline_neoadjuvant(self):
        from modules.bladder_cancer import guideline_reference
        r = guideline_reference(clinical_scenario="neoadjuvant")
        assert "ddMVAC" in r.get("guidelines", {}).get("EAU 2024", "") or \
               "GC" in r.get("guidelines", {}).get("EAU 2024", "")

    def test_eligibility_neoadj_crcl_real_patient(self):
        """C4: P374 (82M/47.3kg/Cr=95.7μmol/L) → CG CrCl≈35 <60 → 顺铂不合格."""
        from modules.bladder_cancer import eligibility_score
        r = eligibility_score(patient_id="P374", T_stage="T2", N_status="N0")
        neoadj = r.get("neoadjuvant")
        assert neoadj is not None
        assert neoadj["cisplatin_eligible"] is False
        assert any("CrCl" in reason for reason in neoadj["reasons"])
        assert 30 <= neoadj["crcl"] <= 45, f"CG CrCl={neoadj['crcl']} 超出预期"

    def test_eligibility_neoadj_missing_creatinine(self):
        """C4 回归: 肌酐缺失 → 不因默认值误判, 以数据缺失标记提示."""
        from modules.bladder_cancer import eligibility_score
        r = eligibility_score(patient_id="P046", T_stage="T2", N_status="N0")
        neoadj = r.get("neoadjuvant")
        assert neoadj is not None
        assert neoadj["cisplatin_eligible"] is True
        assert any("数据缺失" in reason for reason in neoadj["reasons"])


# ══════════════════════════════════════════════════════════════
# Report QC v2.0 (imaging report quality control)
# ══════════════════════════════════════════════════════════════

class TestReportQC:
    """Report QC: hard_rule_check, semantic_check, qc_report."""

    def test_hard_rule_gender_contradiction_male_female_organ(self):
        from modules.report_qc import hard_rule_check
        r = hard_rule_check(patient_id="P001", report_text="子宫正常", patient_gender="M", patient_age=30,
                            body_part="盆腔", clinical_indication="腹痛", modality="CT")
        assert r.get("fatal_count", 0) >= 1

    def test_hard_rule_no_issues(self):
        from modules.report_qc import hard_rule_check
        r = hard_rule_check(patient_id="P001", report_text="胸部CT未见明显异常", patient_gender="M",
                            patient_age=50, body_part="胸部", clinical_indication="体检", modality="CT")
        assert r.get("passed") is True

    def test_semantic_conclusion_contradiction(self):
        from modules.report_qc import semantic_check
        r = semantic_check(patient_id="P001", findings="右下肺见占位", conclusion="未见明显异常")
        assert r.get("passed") is False

    def test_qc_report_grade_a(self):
        from modules.report_qc import qc_report
        r = qc_report(patient_id="P001", hard_issues=[], semantic_issues=[], structured_score=100)
        assert "A" in r["grade"]


# ══════════════════════════════════════════════════════════════
# Neuro Preconsult v2.0 (GCS + red flags + WFNS)
# ══════════════════════════════════════════════════════════════

class TestNeuroPreconsult:
    """Neuro Preconsult: history_collect, red_flag_screen, summary_generate."""

    def test_red_flag_subarachnoid(self):
        from modules.neuro_preconsult import red_flag_screen
        r = red_flag_screen(patient_id="P001", symptoms=["突发剧烈头痛", "恶心呕吐"])
        assert r.get("flag_count", 0) >= 1
        assert r["highest_urgency"] == "emergent"

    def test_red_flag_none(self):
        from modules.neuro_preconsult import red_flag_screen
        r = red_flag_screen(patient_id="P001", symptoms=["轻微头痛", "失眠"])
        assert r.get("flag_count", 0) == 0

    def test_gcs_normal(self):
        from modules.neuro_preconsult import _gcs_score
        r = _gcs_score(4, 5, 6)
        assert r["score"] == 15
        assert "清楚" in r["level"]

    def test_gcs_severe(self):
        from modules.neuro_preconsult import _gcs_score
        r = _gcs_score(1, 2, 2)
        assert r["score"] == 5
        assert "昏迷" in r["level"] or "重度" in r["level"]


# ══════════════════════════════════════════════════════════════
# VTE Management v1.0 (risk + anticoag + monitoring + bridging)
# ══════════════════════════════════════════════════════════════

class TestVTEManagement:
    """VTE: assess_risk, anticoagulation, monitor, followup, reminder, bridging."""

    def test_caprini_major_surgery_high_risk(self):
        from modules.vte_management import _caprini_risk
        r = _caprini_risk(surgery_type="major", age=70, bmi=30, has_cancer=True,
                          has_vte_history=True, bed_rest_days=3)
        assert r["risk_level"] == "高危"

    def test_caprini_minor_surgery_low_risk(self):
        from modules.vte_management import _caprini_risk
        r = _caprini_risk(surgery_type="minor", age=35, bmi=23)
        assert r["risk_level"] in ("极低危", "低危")

    def test_wells_dvt_high_probability(self):
        from modules.vte_management import _wells_score
        r = _wells_score(dvt_symptoms=["tenderness", "leg_swelling", "calf_swelling_3cm", "previous_dvt"],
                         scenario="dvt", alternative_diagnosis=False)
        assert "高临床" in r["probability"]

    def test_anticoag_warfarin_inr_supratherapeutic(self):
        from modules.vte_management import _anticoagulation_plan
        r = _anticoagulation_plan("warfarin", 4.5, 80, 50, 70)
        assert "高" in r.get("adjustment", "") or "暂停" in r.get("adjustment", "") or ">4.0" in r.get("adjustment", "")

    def test_anticoag_warfarin_inr_therapeutic(self):
        from modules.vte_management import _anticoagulation_plan
        r = _anticoagulation_plan("warfarin", 2.3, 80, 50, 70)
        assert "维持" in r.get("adjustment", "")

    def test_anticoag_rivaroxaban_crcl_10(self):
        from modules.vte_management import _anticoagulation_plan
        r = _anticoagulation_plan("rivaroxaban", 0, 10, 80, 70)
        assert "禁忌" in r.get("note", "")

    def test_monitor_pulmonary_embolism_suspected(self):
        from modules.vte_management import monitor
        r = monitor(patient_id="P001", chest_pain=True, dyspnea=True)
        assert "high" in r.get("summary", "").lower() or len(r.get("alerts", [])) > 0

    def test_followup_warfarin_generates_nodes(self):
        from modules.vte_management import followup
        r = followup(patient_id="P001", drug="warfarin")
        assert r["status"] == "ok"
        assert len(r.get("findings", [])) >= 4

    def test_bridging_warfarin_surgery(self):
        from modules.vte_management import bridging
        r = bridging(patient_id="P001", drug="warfarin", surgery_date="2026-08-01")
        assert "停用" in str(r.get("findings", [])) or "LMWH" in str(r.get("findings", []))


# ══════════════════════════════════════════════════════════════
# Oncology Cycle v1.0 (treatment cycle + risk + tri-endpoint)
# ══════════════════════════════════════════════════════════════

class TestOncologyCycle:
    """Oncology Cycle: patient_summary, cycle_plan, risk_screening, tri_endpoint."""

    def test_cycle_plan_generates_four_checks(self):
        from modules.oncology_cycle import cycle_plan
        r = cycle_plan(patient_id="P001", treatment_date="2026-08-01", regimen_type="chemotherapy")
        assert r["status"] == "ok"
        checks = r.get("cycle_plan", {}).get("checks", [])
        assert len(checks) >= 4

    def test_cycle_plan_cisplatin_note(self):
        from modules.oncology_cycle import cycle_plan
        r = cycle_plan(patient_id="P001", treatment_date="2026-08-01", regimen_type="顺铂+吉西他滨")
        notes = r.get("cycle_plan", {}).get("regimen_notes", [])
        assert any("水化" in n or "肾" in n for n in notes)

    def test_risk_screening_neutropenia_fever(self):
        from modules.oncology_cycle import risk_screening
        r = risk_screening(patient_id="P001", treatment_type="chemotherapy", temperature=38.5)
        risks = [risk["risk"] for risk in r.get("risks", [])]
        assert any("感染" in risk for risk in risks), f"Expected infection risk, got {risks}"

    def test_risk_screening_no_risks(self):
        from modules.oncology_cycle import risk_screening
        r = risk_screening(patient_id="P001", treatment_type="targeted", temperature=36.8)
        risks = r.get("risks", [])
        # Should have at least the "no risk" entry
        assert len(risks) >= 1

    def test_tri_endpoint_doctor(self):
        from modules.oncology_cycle import tri_endpoint
        r = tri_endpoint(patient_id="P001", endpoint="doctor")
        assert r["status"] == "ok"
        assert "医生" in r["output"]["title"]

    def test_tri_endpoint_patient(self):
        from modules.oncology_cycle import tri_endpoint
        r = tri_endpoint(patient_id="P001", endpoint="patient",
                         cycle_plan={"next_cycle_date": "2026-08-22", "cycle_interval_days": 21})
        assert r["status"] == "ok"
        assert len(r["output"].get("danger_signs", [])) >= 2
