"""
围术期止吐 BP Pipeline 编排 (pipeline)

8 个业务流程的编排函数，串联 scoring → drug → controls → anesthesia → nondrug
每个 BP handler 接受 A2A 调用，返回 JSON-serializable dict
"""

from .scoring_engine import (
    calculate_apfel_score,
    calculate_povoc_score,
    calculate_pdnv_score,
    classify_risk_level,
)
from .drug_recommend import (
    recommend_regimen_adult,
    recommend_regimen_pediatric,
    recommend_timing,
    recommend_rescue,
)
from .drug_controls import validate_contraindications, check_duplicate_medication
from .anesthesia_guide import (
    recommend_tiva,
    recommend_pnb,
    recommend_epidural,
    recommend_dexmedetomidine,
    recommend_opioid_sparing,
    recommend_fluid_therapy,
    recommend_muscle_relaxant,
)
from .nondrug_guide import (
    recommend_acupoint,
    recommend_auricular,
    recommend_preop_carbs,
    recommend_lifestyle,
    recommend_aromatherapy,
)


def bp_preop_risk_scoring(
    patient_id: str = "",
    patient: dict = None,
    surgery: dict = None,
    **kwargs,
) -> dict:
    """BP-PONV-01: 术前 PONV 风险评分"""
    if patient is None:
        patient = {}
    if surgery is None:
        surgery = {}

    age = patient.get("age", 35)

    if age < 18:
        score_result = calculate_povoc_score(
            age=age,
            surgery_duration_min=surgery.get("duration_min", 0),
            opioid_used="是" if surgery.get("opioid_used") else "否",
            ponv_history="是" if patient.get("ponv_history") else "否",
            motion_sickness="是" if patient.get("motion_sickness") else "否",
        )
    else:
        score_result = calculate_apfel_score(
            gender=patient.get("gender", ""),
            smoking="否" if not patient.get("smoking") else "是",
            ponv_history="是" if patient.get("ponv_history") else "否",
            motion_sickness="是" if patient.get("motion_sickness") else "否",
            opioid_planned="是" if surgery.get("opioid_planned") else "否",
        )

    return {
        "patient_id": patient_id,
        "risk_assessment": score_result,
        "status": "ok",
    }


def bp_anesthesia_optimization(
    patient_id: str = "",
    patient: dict = None,
    surgery: dict = None,
    risk_level: str = "",
    **kwargs,
) -> dict:
    """BP-PONV-02: 麻醉方案止吐优化"""
    if patient is None:
        patient = {}
    if surgery is None:
        surgery = {}

    return {
        "patient_id": patient_id,
        "tiva": recommend_tiva(
            risk_level=risk_level, surgery_type=surgery.get("type", "")
        ),
        "pnb": recommend_pnb(
            surgery_type=surgery.get("type", ""), patient=patient
        ),
        "epidural": recommend_epidural(
            surgery_category=surgery.get("category", ""), patient=patient
        ),
        "dexmedetomidine": recommend_dexmedetomidine(
            patient=patient, surgery_type=surgery.get("type", "")
        ),
        "opioid_sparing": recommend_opioid_sparing(
            pain_level=surgery.get("pain_level", "moderate"),
            opioid_used=surgery.get("opioid_planned", False),
            patient=patient,
        ),
        "fluid_therapy": recommend_fluid_therapy(
            surgery_duration_min=surgery.get("duration_min", 60),
            risk_level=risk_level,
        ),
        "muscle_relaxant": recommend_muscle_relaxant(
            reversal_needed=surgery.get("reversal_needed", False),
            risk_level=risk_level,
        ),
        "status": "ok",
    }


def bp_drug_prophylaxis(
    patient_id: str = "",
    patient: dict = None,
    risk_level: str = "",
    risk_score: int = 0,
    **kwargs,
) -> dict:
    """BP-PONV-03: 药物预防方案生成"""
    if patient is None:
        patient = {}

    age = patient.get("age", 35)

    if age < 18:
        regimen = recommend_regimen_pediatric(
            risk_level=risk_level, risk_score=risk_score, age=age
        )
    else:
        regimen = recommend_regimen_adult(
            risk_level=risk_level, risk_score=risk_score
        )

    validation = validate_contraindications(
        regimen=regimen, patient=patient
    )

    return {
        "patient_id": patient_id,
        "regimen": regimen,
        "validation": validation,
        "status": "ok",
    }


def bp_drug_timing(
    patient_id: str = "",
    regimen: dict = None,
    **kwargs,
) -> dict:
    """BP-PONV-04: 给药时机提醒"""
    if regimen is None:
        regimen = {}

    drugs = [d["name"] for d in regimen.get("drugs", [])]
    timing_result = recommend_timing(drugs=drugs)

    return {
        "patient_id": patient_id,
        "timing_plan": timing_result.get("timing_plan", []),
        "status": "ok",
    }


def bp_intraop_decision(
    patient_id: str = "",
    patient: dict = None,
    surgery: dict = None,
    risk_level: str = "",
    **kwargs,
) -> dict:
    """BP-PONV-05: 术中液体与辅助决策"""
    if patient is None:
        patient = {}
    if surgery is None:
        surgery = {}

    return {
        "patient_id": patient_id,
        "fluid": recommend_fluid_therapy(
            surgery_duration_min=surgery.get("duration_min", 60),
            risk_level=risk_level,
        ),
        "dexmedetomidine": recommend_dexmedetomidine(patient=patient),
        "muscle_relaxant": recommend_muscle_relaxant(
            reversal_needed=surgery.get("reversal_needed", False),
            risk_level=risk_level,
        ),
        "opioid_monitoring": recommend_opioid_sparing(
            pain_level=surgery.get("pain_level", ""),
            opioid_used=True,
            patient=patient,
        ),
        "status": "ok",
    }


def bp_postop_rescue(
    patient_id: str = "",
    prior_prophylaxis: bool = False,
    hours_since_prophylaxis: float = 0,
    triple_therapy_used: bool = False,
    **kwargs,
) -> dict:
    """BP-PONV-06: 术后 PONV 监测与补救"""
    rescue = recommend_rescue(
        prior_prophylaxis=prior_prophylaxis,
        hours_since_prophylaxis=hours_since_prophylaxis,
        triple_therapy_used=triple_therapy_used,
    )

    return {
        "patient_id": patient_id,
        "rescue_plan": rescue,
        "status": "ok",
    }


def bp_nondrug_intervention(
    patient_id: str = "",
    patient: dict = None,
    surgery: dict = None,
    risk_level: str = "",
    drug_contraindications: bool = False,
    **kwargs,
) -> dict:
    """BP-PONV-07: 非药物辅助干预"""
    if patient is None:
        patient = {}
    if surgery is None:
        surgery = {}

    return {
        "patient_id": patient_id,
        "preop_carbs": recommend_preop_carbs(
            patient=patient, surgery_type=surgery.get("type", "")
        ),
        "acupoint": recommend_acupoint(
            risk_level=risk_level, drug_contraindications=drug_contraindications
        ),
        "auricular": recommend_auricular(
            risk_level=risk_level, surgery_type=surgery.get("type", "")
        ),
        "lifestyle": recommend_lifestyle(patient=patient, postoperative=True),
        "aromatherapy": recommend_aromatherapy(),
        "status": "ok",
    }


def bp_discharge_followup(
    patient_id: str = "",
    patient: dict = None,
    pacu_opioid: bool = False,
    pacu_nausea: bool = False,
    **kwargs,
) -> dict:
    """BP-PONV-08: 出院后 PDNV 随访"""
    if patient is None:
        patient = {}

    pdnv = calculate_pdnv_score(
        gender=patient.get("gender", ""),
        age=patient.get("age", 35),
        ponv_history="是" if patient.get("ponv_history") else "否",
        pacu_opioid="是" if pacu_opioid else "否",
        pacu_nausea="是" if pacu_nausea else "否",
    )

    return {
        "patient_id": patient_id,
        "pdnv_assessment": pdnv,
        "discharge_advice": {
            "low_risk": "观察，如出现恶心可口服昂丹司琼ODT",
            "medium_high_risk": "开具口服止吐药（昂丹司琼8mg PO q8h prn）+ 非药物措施",
        }.get(
            "medium_high_risk" if pdnv.get("score", 0) >= 2 else "low_risk",
            "观察",
        ),
        "status": "ok",
    }
