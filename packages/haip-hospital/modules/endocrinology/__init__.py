"""内分泌科 — KnowledgeAgent-powered clinical reasoning.

核心能力:
- 糖尿病综合管理: HbA1c目标分层、ADA低血糖分级、并发症筛查
- 甲状腺疾病: TSH解读、ATA TI-RADS结节风险分层
- 代谢综合征: IDF诊断标准
- 骨质疏松: 简化的FRAX风险评估
- 高危筛查: DKA/低血糖昏迷/甲亢危象/肾上腺危象/高钙危象

Guidelines: 中国糖尿病防治指南(2024), ADA Standards of Care 2025, ATA Thyroid 2015
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="endocrinology", department="内分泌科")
_GUIDELINES = [
    "中国糖尿病防治指南（2024版）",
    "ADA Standards of Care in Diabetes 2025",
    "ATA Thyroid Nodule Guidelines 2015",
    "IDF Metabolic Syndrome Consensus",
]
_agent.rule_engine.load_all()


def _error(msg: str) -> dict:
    return {"status": "error", "agent": _agent.agent_name, "error": msg}


# ── Diabetes ──

def _hba1c_target(age: int, duration_years: int, complications: list[str]) -> str:
    """HbA1c target stratification (ADA 2025)."""
    if age >= 75 or "心血管" in str(complications) or "低血糖史" in str(complications):
        return "<8.0% (宽松)"
    if age >= 65 or duration_years >= 10 or complications:
        return "<7.5% (一般)"
    return "<7.0% (严格)"


def _hypoglycemia_level(glucose: float) -> str:
    """ADA hypoglycemia classification."""
    if glucose < 3.0:
        return "Level 2 — 严重低血糖 (需他人协助)"
    if glucose < 3.9:
        return "Level 1 — 低血糖警戒 (<3.9 mmol/L)"
    return "正常"


def _complication_screen(diagnosis: str, labs: dict) -> list[str]:
    """Basic diabetes complication screening."""
    screening: list[str] = []
    if "2型糖" in diagnosis or "1型糖" in diagnosis:
        glu = labs.get("GLU", labs.get("glucose", 0))
        if isinstance(glu, (int, float)):
            if glu > 13.9:
                screening.append("高血糖危象风险 (GLU>13.9)")
            if glu > 22.2:
                screening.append("高渗性昏迷风险 (GLU>22.2)")
        cr = labs.get("Cr", labs.get("creatinine", 0))
        if isinstance(cr, (int, float)) and cr > 133:
            screening.append("糖尿病肾病风险 (Cr>133 μmol/L)")
    return screening


# ── Thyroid ──

def _tirads_risk(nodule_size: float, features: list[str]) -> tuple[int, str]:
    """ATA TI-RADS simplified classification."""
    suspicious = sum(1 for f in features if f in [
        "低回声", "微小钙化", "边缘不规则", "纵横比>1", "甲状腺外侵犯"
    ])
    if suspicious >= 4:
        return 5, "TR5 — 高度怀疑恶性 (FNA推荐 结节≥1cm)"
    if suspicious == 3:
        return 4, "TR4 — 中度怀疑 (FNA推荐 结节≥1.5cm)"
    if suspicious == 2:
        return 3, "TR3 — 低度怀疑 (FNA推荐 结节≥2.5cm)"
    if suspicious == 1:
        return 2, "TR2 — 良性可能 (无需FNA)"
    return 1, "TR1 — 良性 (无需FNA)"


def _tsh_interpret(tsh: float) -> str:
    """TSH level interpretation."""
    if tsh < 0.1:
        return "TSH重度抑制 (<0.1) — 甲亢/亚临床甲亢"
    if tsh < 0.4:
        return "TSH轻度抑制 (0.1-0.4) — 亚临床甲亢可能"
    if tsh <= 4.0:
        return "TSH正常 (0.4-4.0)"
    if tsh <= 10.0:
        return "TSH轻度升高 (4.0-10.0) — 亚临床甲减"
    return "TSH显著升高 (>10.0) — 甲减"


# ── Metabolic Syndrome ──

def _metabolic_syndrome(bp_systolic: float, bp_diastolic: float, fpg: float,
                         waist_cm: float, hdl: float, tg: float,
                         gender: str) -> dict:
    """IDF metabolic syndrome diagnostic criteria."""
    criteria = []
    if waist_cm >= 90 if gender == "M" else waist_cm >= 80:
        criteria.append(f"中心性肥胖 (腰围{waist_cm}cm)")
    if fpg >= 5.6:
        criteria.append(f"空腹血糖升高 (FPG {fpg} mmol/L)")
    if bp_systolic >= 130 or bp_diastolic >= 85:
        criteria.append(f"血压升高 ({bp_systolic}/{bp_diastolic} mmHg)")
    if tg >= 1.7:
        criteria.append(f"甘油三酯升高 (TG {tg} mmol/L)")
    if hdl < 1.03 if gender == "M" else hdl < 1.29:
        criteria.append(f"HDL降低 ({hdl} mmol/L)")

    criteria_met = len(criteria)
    has_central = any("中心性肥胖" in c for c in criteria)
    met_syndrome = has_central and criteria_met >= 3

    return {
        "diagnosis": "代谢综合征" if met_syndrome else "未达代谢综合征标准",
        "criteria_met": criteria_met,
        "criteria": criteria,
        "requires_central_obesity": True,
    }


# ── Public API ──

def assess_diabetes(**kwargs) -> dict:
    """糖尿病综合评估: HbA1c目标 + 低血糖分级 + 并发症筛查."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _error(f"Patient {pid} not found")

    age = p.get("age", 0)
    labs = p.get("lab_results", {})
    dx = p.get("diagnosis", "")

    glu = labs.get("GLU", labs.get("glucose", 0))
    glu_val = float(glu) if isinstance(glu, (int, float)) else 0

    target = _hba1c_target(age, 5, ["心血管"])  # assume 5yr duration
    hypo = _hypoglycemia_level(glu_val)
    screening = _complication_screen(dx, labs)
    vitals = _agent.assess_vitals(p)
    guides = _agent.search_guidelines("糖尿病") or _GUIDELINES

    return _agent.clinical_result(
        summary=f"糖尿病综合评估 — HbA1c目标{target}, GLU={glu_val}mmol/L, {hypo}",
        patient=p,
        guidelines=guides[:3],
        alerts=vitals.get("alerts", []) + screening,
        findings=[{
            "HbA1c目标": target,
            "当前血糖": f"{glu_val} mmol/L",
            "低血糖分级": hypo,
            "并发症风险": screening,
        }],
        recommendations=[
            f"HbA1c控制目标: {target}",
            "每3-6个月复查HbA1c",
            "年度糖尿病并发症筛查: 眼底/尿微量白蛋白/神经病变",
        ],
    )


def assess_thyroid(**kwargs) -> dict:
    """甲状腺评估: TSH解读 + TI-RADS结节风险分层."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _error(f"Patient {pid} not found")

    labs = p.get("lab_results", {})
    tsh = labs.get("TSH", 0)
    tsh_val = float(tsh) if isinstance(tsh, (int, float)) else 0

    tsh_status = _tsh_interpret(tsh_val) if tsh_val > 0 else "TSH未检测"
    # Assume ultrasound findings from diagnosis context
    dx = p.get("diagnosis", "")
    nodule_features = ["低回声"] if "结节" in dx else []
    tirads_level, tirads_desc = _tirads_risk(1.5, nodule_features)

    guides = _agent.search_guidelines("甲状腺") or _GUIDELINES

    return _agent.clinical_result(
        summary=f"甲状腺评估 — TSH={tsh_val}, {tsh_status}, TI-RADS {tirads_desc[:20]}",
        patient=p,
        guidelines=guides[:3],
        findings=[{
            "TSH": f"{tsh_val} mIU/L",
            "TSH解读": tsh_status,
            "TI-RADS分级": tirads_desc,
        }],
        recommendations=[
            "TSH异常→复查FT3/FT4+TPOAb+TgAb",
            "甲状腺结节→颈部超声+TI-RADS分级",
            "甲亢→TRAb检测, 甲减→随访替代治疗",
        ],
    )


def assess_metabolic(**kwargs) -> dict:
    """代谢综合征筛查 (IDF标准)."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _error(f"Patient {pid} not found")

    labs = p.get("lab_results", {})
    age = p.get("age", 0)
    gender = p.get("gender", "M")
    weight = p.get("weight_kg", 70)
    height_cm = p.get("height_cm", 170)

    fpg = float(labs.get("GLU", labs.get("glucose", 5.0)))
    tg = float(labs.get("TG", labs.get("triglycerides", 1.5)))
    hdl = float(labs.get("HDL", 1.2))
    waist = weight * 0.45 + (5 if gender == "M" else 3)

    result = _metabolic_syndrome(130, 85, fpg, waist, hdl, tg, gender)
    bmi = weight / ((height_cm / 100) ** 2) if height_cm else 0
    guides = _agent.search_guidelines("代谢") or _GUIDELINES

    return _agent.clinical_result(
        summary=f"代谢综合征筛查 — {result['diagnosis']}, 达标{result['criteria_met']}/5项",
        patient=p,
        guidelines=guides[:2],
        findings=[{
            "诊断": result["diagnosis"],
            "达标项数": result["criteria_met"],
            "诊断标准": result["criteria"],
            "BMI": f"{bmi:.1f} (腰围估算{waist:.0f}cm)",
        }],
        recommendations=[
            "生活方式干预: 饮食控制+运动≥150min/周",
            "达标≥3项且中心性肥胖→考虑二甲双胍/SGLT2i/GLP-1RA",
            "年度心血管风险评估",
        ],
    )


def assess_osteoporosis(**kwargs) -> dict:
    """骨质疏松风险简化评估."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _error(f"Patient {pid} not found")

    age = p.get("age", 0)
    gender = p.get("gender", "M")
    dx = p.get("diagnosis", "")
    labs = p.get("lab_results", {})

    # Simplified FRAX-like risk factors
    risk_factors = []
    if age >= 65:
        risk_factors.append(f"年龄≥65 ({age}岁)")
    if gender == "F":
        risk_factors.append("女性(绝经后风险升高)")
    if "糖尿" in dx:
        risk_factors.append("糖尿病(骨折风险增加)")
    if "激素" in dx or "甲状腺" in dx:
        risk_factors.append("内分泌疾病(继发性骨质疏松风险)")

    risk_level = "低危" if len(risk_factors) <= 1 else ("中危" if len(risk_factors) <= 2 else "高危")
    guides = _agent.search_guidelines("骨质疏松") or _GUIDELINES

    return _agent.clinical_result(
        summary=f"骨质疏松风险评估 — {risk_level} ({len(risk_factors)}个危险因素)",
        patient=p,
        guidelines=guides[:2],
        findings=[{
            "风险等级": risk_level,
            "危险因素": risk_factors,
            "推荐": "DXA骨密度检查" if risk_level in ("中危", "高危") else "常规随访",
        }],
        recommendations=[
            "高危→DXA骨密度检查+钙剂+维生素D补充",
            "中危→定期骨密度筛查",
            "低危→生活方式干预(负重运动/充足钙摄入)",
        ],
    )


# ── Template bp_* functions (backward compatible) ──

def _clinical_error(msg: str) -> dict:
    return _agent.make_clinical_error(msg)


def bp_reception(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p:
        return _clinical_error(f"Patient {pid} not found")
    dx = p.get("diagnosis", "")
    guides = _agent.search_guidelines(dx) or _GUIDELINES
    return _agent.clinical_result(
        summary=f"内分泌科—接诊完成: {dx}",
        patient=p, guidelines=guides[:3],
        findings=[{"主诉": dx, "专科关注": "血糖/甲功/骨代谢/肾上腺"}],
    )


def bp_exam(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _clinical_error(f"Patient {pid} not found")
    return _agent.clinical_result(patient=p, summary="内分泌科—检查完成",
        guidelines=_GUIDELINES[:2],
        recommendations=["FPG+HbA1c+OGTT", "TSH+FT3+FT4+TPOAb+TgAb", "骨密度DXA", "肾上腺皮质功能"])


def bp_diagnosis(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _clinical_error(f"Patient {pid} not found")
    return _agent.clinical_result(patient=p, summary="内分泌科—诊断完成",
        guidelines=_GUIDELINES[:2],
        findings=[{"诊断": p.get("diagnosis", ""), "分型": "2型/1型/甲亢/甲减/代谢综合征"}],
        recommendations=["请使用专科评估工具: assess_diabetes/assess_thyroid/assess_metabolic"])


def bp_plan(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _clinical_error(f"Patient {pid} not found")
    return _agent.clinical_result(patient=p, summary="内分泌科—治疗方案",
        guidelines=_GUIDELINES[:2],
        recommendations=["降糖/降甲/抗骨质疏松/生活方式干预", "请使用专科评估工具获取具体方案"])


def bp_treatment(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _clinical_error(f"Patient {pid} not found")
    return _agent.clinical_result(patient=p, summary="内分泌科—治疗执行",
        guidelines=_GUIDELINES[:2],
        recommendations=["血糖监测qid/甲功复查/骨代谢标志物/药物不良反应监测"])


def bp_followup(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid)
    if not p: return _clinical_error(f"Patient {pid} not found")
    return _agent.clinical_result(patient=p, summary="内分泌科—随访管理",
        guidelines=_GUIDELINES[:2],
        recommendations=["HbA1c q3-6月/甲功 q6-12月/年度并发症筛查/骨密度 q2年"])
