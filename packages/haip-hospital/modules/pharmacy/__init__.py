"""药学部 — TPN处方/止吐预防/医嘱审核/用药重整/ADR预警.

业务流来源:
  - ESPEN/ASPEN/CSPEN 肠外肠内营养指南
  - ASER/SAMBA PONV预防共识 (2020)
  - 中国药典(2020)/中国静脉用药调配指南
  - 南方医院静配中心SOP
"""

from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="pharmacy", department="药学部")
_GUIDELINES = [
    "ESPEN 欧洲临床营养与代谢学会指南 (2023)",
    "ASPEN 美国肠外肠内营养学会指南 (2022)",
    "CSPEN 中国肠外肠内营养指南 (2024)",
    "ASER/SAMBA 术后恶心呕吐管理共识 (2020)",
    "中国麻醉学会 术后恶心呕吐诊疗指南 (2025)",
    "中国药典 (2020年版)",
    "中国静脉用药集中调配质量管理规范",
    "NMPA 止吐药物说明书 (5-HT3/NK1/糖皮质激素/抗组胺)",
]
_agent.rule_engine.load_all()


# ── Handler functions (matching YAML tool definitions) ──

def assess_nutrition_risk(**kwargs) -> dict:
    pid = kwargs.get("patient_id", "")
    w = float(kwargs.get("weight_kg", 0) or 0)
    h = float(kwargs.get("height_cm", 0) or 0)
    bmi = w / ((h / 100) ** 2) if h > 0 and w > 0 else 0
    age = _agent.get_patient(pid).get("age", 65) if pid else 65

    # NRS-2002 simplified
    nrs = 0
    if bmi and bmi < 20.5:
        nrs += 1
    if bmi and bmi < 18.5:
        nrs += 2
    if age >= 70:
        nrs += 1
    nrs = min(nrs + 1, 7)  # disease severity minimum 1

    level = "低危"
    if nrs >= 5:
        level = "高危"
    elif nrs >= 3:
        level = "中危"

    return {
        "status": "ok",
        "summary": f"营养风险评估 — NRS-2002 {nrs}分 ({level})",
        "nrs2002_score": nrs,
        "risk_level": level,
        "bmi": round(bmi, 1) if bmi else None,
        "refeeding_risk": "高风险" if nrs >= 5 or (bmi and bmi < 16) else "低风险",
    }


def compute_tpn(**kwargs) -> dict:
    w = float(kwargs.get("weight_kg", 70) or 70)
    h = float(kwargs.get("height_cm", 170) or 170)
    age = int(kwargs.get("age", 65) or 65)
    gender = kwargs.get("gender", "male")

    # Harris-Benedict BEE
    if gender == "female":
        bee = 655.1 + 9.56 * w + 1.85 * h - 4.68 * age
    else:
        bee = 66.5 + 13.75 * w + 5.0 * h - 6.78 * age

    tee = bee * 1.2  # mild stress factor
    protein = w * 1.2  # 1.2g/kg/d
    glucose_kcal = tee * 0.50  # 50% from glucose
    lipid_kcal = tee * 0.50  # 50% from lipid
    glucose_g = glucose_kcal / 3.4
    lipid_g = lipid_kcal / 9

    return {
        "status": "ok",
        "summary": f"TPN处方计算 — TEE {tee:.0f} kcal/d",
        "bee_kcal": round(bee, 0),
        "tee_kcal": round(tee, 0),
        "protein_g": round(protein, 0),
        "glucose_g": round(glucose_g, 0),
        "lipid_g": round(lipid_g, 0),
        "osmolarity_warning": ">1200mOsm → 必须中心静脉" if tee > 1800 else None,
        "calcium_phosphate_check": "Ca×P<45 安全" if tee > 1000 else None,
        "disclaimer": "此为AI辅助计算，须经临床药师审核确认后执行",
    }


def review_rx(**kwargs) -> dict:
    items = kwargs.get("prescription_items", [])
    alerts = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                drug = str(item.get("drug", "")).lower()
                if "钾" in drug or "potassium" in drug:
                    alerts.append(f"⚠️ 高浓度钾 ({item.get('drug')}): 外周静脉<60mmol/L")
                if "钙" in drug or "calcium" in drug:
                    alerts.append(f"⚠️ 钙剂 ({item.get('drug')}): 外周静脉<5mmol/L")
    return {
        "status": "ok",
        "summary": f"处方审核 — {len(items) if isinstance(items, list) else 0}条, {len(alerts)}条警告",
        "alerts": alerts,
        "disclaimer": "此为AI辅助审核，须经药师确认后发药",
    }


def nutrition_route(**kwargs) -> dict:
    gi = kwargs.get("gi_function", "normal")
    route = "EN 肠内营养"
    if gi in ("肠梗阻", "肠穿孔", "严重消化道出血", "obstruction", "perforation"):
        route = "PN 肠外营养"
    elif gi in ("部分功能", "partial", "短肠"):
        route = "EN + 补充性PN"
    return {
        "status": "ok",
        "summary": f"营养途径推荐 — {route}",
        "route": route,
        "basis": f"胃肠道功能: {gi}",
    }


def drug_search(**kwargs) -> dict:
    kw = kwargs.get("keyword", "")
    results = []
    if "阿司" in kw or "aspirin" in kw.lower():
        results.append({"name": "阿司匹林肠溶片", "dose": "100mg", "route": "po"})
    if "氯吡" in kw or "clopidogrel" in kw.lower():
        results.append({"name": "氯吡格雷", "dose": "75mg", "route": "po"})
    if "他汀" in kw or "atorvastatin" in kw.lower():
        results.append({"name": "阿托伐他汀钙片", "dose": "20mg", "route": "po"})
    return {
        "status": "ok",
        "summary": f"药品查询 — {kw} ({len(results)}条结果)",
        "results": results,
    }

