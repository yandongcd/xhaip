"""药剂科 处方审核 — 17 规则药物交互检查 + PN 成分范围验证 + 适应症/配伍/用量审查.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any

# ── Guideline ranges for PN components ──
PN_COMPONENT_RANGES: dict[str, dict[str, Any]] = {
    "energy": {"min": 15, "max": 35, "unit": "kcal/kg/d", "ref": "ESPEN/中国指南 2023"},
    "protein": {"min": 0.8, "max": 2.0, "unit": "g/kg/d", "ref": "ESPEN/中国指南 2023"},
    "glucose": {"min": 100, "max": 300, "unit": "g/d", "ref": "中国成人患者肠外肠内营养指南 2023"},
    "fat": {"min": 0.5, "max": 2.5, "unit": "g/kg/d", "ref": "成人肠外营养脂肪乳指南 2023"},
    "sodium": {"min": 60, "max": 160, "unit": "mmol/d", "ref": "肠外营养中电解质补充共识 2024"},
    "potassium": {"min": 40, "max": 100, "unit": "mmol/d", "ref": "肠外营养中电解质补充共识 2024"},
    "phosphorus": {"min": 10, "max": 30, "unit": "mmol/d", "ref": "肠外营养中电解质补充共识 2024"},
    "magnesium": {"min": 4, "max": 16, "unit": "mmol/d", "ref": "肠外营养中电解质补充共识 2024"},
    "calcium": {"min": 2.5, "max": 10, "unit": "mmol/d", "ref": "肠外营养中电解质补充共识 2024"},
}

# ── Drug-drug interaction rules (17 rules) ──
DRUG_INTERACTION_RULES: list[dict[str, Any]] = [
    {"drugs": ["华法林", "肝素"], "risk": "出血风险显著增加", "severity": "severe",
     "action": "联合使用期间每日监测 INR，肝素使用期间 INR 可能不可靠，改用抗 Xa 监测"},
    {"drugs": ["华法林", "阿司匹林"], "risk": "消化道出血风险显著增加", "severity": "severe",
     "action": "避免联合使用，必要时加用 PPI 保护胃黏膜"},
    {"drugs": ["华法林", "NSAIDs"], "risk": "消化道出血", "severity": "severe",
     "action": "尽可能避免，必须使用时加用 PPI"},
    {"drugs": ["庆大霉素", "呋塞米"], "risk": "耳毒性及肾毒性增强", "severity": "severe",
     "action": "避免联合使用或严密监测听力+肾功能"},
    {"drugs": ["氨基糖苷", "利尿剂"], "risk": "肾毒性风险增加", "severity": "high",
     "action": "密切监测肾功能，每日测尿量/肌酐"},
    {"drugs": ["ACEI", "钾补充剂"], "risk": "高钾血症", "severity": "high",
     "action": "严密监测血钾，限制补钾量"},
    {"drugs": ["头孢", "酒精"], "risk": "双硫仑样反应", "severity": "high",
     "action": "用药期间及停药后7天内禁酒"},
    {"drugs": ["甲硝唑", "酒精"], "risk": "双硫仑样反应", "severity": "high",
     "action": "用药期间及停药后72小时内禁酒"},
    {"drugs": ["阿片类", "苯二氮卓"], "risk": "呼吸抑制风险增加", "severity": "critical",
     "action": "禁忌联合使用，强直性呼吸抑制可致死"},
    {"drugs": ["吗啡", "地西泮"], "risk": "呼吸抑制", "severity": "critical",
     "action": "绝对禁忌联合使用"},
    {"drugs": ["曲马多", "SSRI"], "risk": "5-HT 综合征", "severity": "severe",
     "action": "避免联合，如发生则停药+赛庚啶治疗"},
    {"drugs": ["碳酸钙", "左甲状腺素"], "risk": "左甲状腺素吸收减少", "severity": "moderate",
     "action": "间隔4小时以上服用"},
    {"drugs": ["钙剂", "铁剂"], "risk": "铁吸收减少", "severity": "moderate",
     "action": "间隔2小时以上服用"},
    {"drugs": ["NSAIDs", "ACEI"], "risk": "肾功能损伤+降压效果减弱", "severity": "high",
     "action": "监测肾功能和血压，限制 NSAIDs 使用时间"},
    {"drugs": ["华法林", "甲硝唑"], "risk": "INR 显著升高", "severity": "severe",
     "action": "联用期间密切监测 INR，可能需减少华法林剂量30-50%"},
    {"drugs": ["锂", "NSAIDs"], "risk": "锂血药浓度升高，锂中毒风险", "severity": "severe",
     "action": "监测血锂浓度，必要时减少锂剂量"},
    {"drugs": ["地高辛", "胺碘酮"], "risk": "地高辛中毒风险(血药浓度可升高2倍)", "severity": "severe",
     "action": "地高辛减量50%，监测血药浓度+心电图"},
]

# ── PN indication keywords ──
PN_INDICATIONS = [
    ("肠瘘/短肠综合征", ["短肠", "短肠综合征", "肠瘘", "肠功能障碍"]),
    ("肠梗阻", ["肠梗阻", "肠痹"]),
    ("重症胰腺炎", ["重症胰腺炎", "急性胰腺炎", "坏死性胰腺炎"]),
    ("高流量肠瘘", ["肠瘘", "肠穿孔"]),
    ("严重腹腔感染", ["腹腔感染", "腹膜炎", "腹腔脓肿"]),
    ("放射性肠炎急性期", ["放射性肠炎"]),
    ("严重炎症性肠病", ["克罗恩", "溃疡性结肠炎", "炎症性肠病"]),
    ("严重烧伤/创伤", ["烧伤", "多发伤", "严重创伤", "复合伤"]),
    ("重度营养不良/恶病质", ["恶病质", "重度营养不良", "严重营养不良", "进食困难"]),
    ("胃肠手术后早期", ["胃癌术后", "食管癌术后", "胃肠道术后", "胃肠术后"]),
]

EN_CONTRAINDICATIONS = [
    "肠梗阻", "肠功能障碍", "严重腹腔感染", "高流量肠瘘",
    "严重消化道出血", "严重呕吐/腹泻", "难治性腹泻", "严重腹泻",
]


# ── A2A handler: simple check ──
def check(
    patient_id: str = "", prescription_items: list | None = None,
    weight_kg: float = 60.0, diagnosis: str = "",
    tpn_prescription: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """处方审核 — 全面评估药物交互 + 用量 + 适应症.

    Backward compatible with v1.0 API; now additionally accepts tpn_prescription
    and diagnosis for PN-specific reviews.
    """
    items = prescription_items or []
    warnings: list[dict] = []
    items_count = len(items)

    # Drug-drug interaction check
    drug_names = []
    for item in items:
        name = item.get("name", "")
        drug_names.append(name)
    drug_names_lower = [n.lower() for n in drug_names]

    for rule in DRUG_INTERACTION_RULES:
        rule_drugs_lower = [d.lower() for d in rule["drugs"]]
        hits = sum(1 for d in rule_drugs_lower if any(d in name for name in drug_names_lower))
        if hits >= 2:
            warnings.append({
                "category": "药物相互作用",
                "drugs": " + ".join(rule["drugs"]),
                "risk": rule["risk"],
                "severity": rule["severity"],
                "action": rule["action"],
                "status": "不合理" if rule["severity"] in ("critical", "severe") else "需关注",
            })

    # Indication check (if diagnosis provided)
    if diagnosis:
        diagnosis_lower = diagnosis.lower()
        found_indication = False
        for indication_name, keywords in PN_INDICATIONS:
            if any(k in diagnosis_lower for k in keywords):
                found_indication = True
                break
        if not found_indication:
            en_contra_hit = any(k in diagnosis_lower for k in EN_CONTRAINDICATIONS)
            if not en_contra_hit and "营养" in diagnosis_lower:
                found_indication = True
        if not found_indication:
            warnings.append({
                "category": "适应症",
                "drugs": "PN 处方",
                "risk": "未明确识别 PN 适应证",
                "severity": "moderate",
                "action": "建议优先考虑肠内营养，如确有 PN 需要请在病程中明确记录",
                "status": "需关注",
            })

    # Dosage review (if TPN prescription data provided)
    if tpn_prescription:
        total_energy = tpn_prescription.get("total_energy_kcal", 0)
        amino_acid_g = tpn_prescription.get("amino_acid_grams", 0)
        glucose_g = tpn_prescription.get("glucose_grams", 0)
        fat_g = tpn_prescription.get("fat_grams", 0)

        if total_energy:
            per_kg = total_energy / weight_kg if weight_kg > 0 else 0
            r = PN_COMPONENT_RANGES["energy"]
            if per_kg < r["min"] or per_kg > r["max"]:
                warnings.append({
                    "category": "用法用量",
                    "drugs": "总能量",
                    "risk": f"{total_energy}kcal({per_kg:.1f} kcal/kg/d) 超出推荐范围({r['min']}-{r['max']}{r['unit']})",
                    "severity": "high",
                    "action": f"调整至 {r['min']}-{r['max']}{r['unit']}",
                    "status": "不合理",
                })

        if amino_acid_g:
            per_kg = amino_acid_g / weight_kg if weight_kg > 0 else 0
            r = PN_COMPONENT_RANGES["protein"]
            if per_kg < r["min"] or per_kg > r["max"]:
                warnings.append({
                    "category": "用法用量",
                    "drugs": "氨基酸",
                    "risk": f"{amino_acid_g}g({per_kg:.2f} g/kg/d) 超出推荐范围",
                    "severity": "moderate",
                    "action": f"调整至 {r['min']}-{r['max']}{r['unit']}",
                    "status": "需关注",
                })

        # Osmolarity check
        osm = tpn_prescription.get("osmolarity_est", 0)
        if osm and osm > 900:
            warnings.append({
                "category": "配伍禁忌",
                "drugs": "渗透压",
                "risk": f"估算渗透压 {osm}mOsm/L > 900，存在静脉炎风险",
                "severity": "moderate",
                "action": "渗透压 > 900 mOsm/L 需使用中心静脉通路",
                "status": "需关注",
            })

    severe_count = sum(1 for w in warnings if w.get("severity") in ("critical", "severe"))
    high_count = sum(1 for w in warnings if w.get("severity") == "high")
    overall = "高" if severe_count >= 2 or high_count >= 3 else ("中" if warnings else "低")

    return {
        "patient_id": patient_id, "items_count": items_count,
        "risk_level": overall, "warnings": warnings, "passed": len(warnings) == 0,
        "severe_count": severe_count, "total_warnings": len(warnings),
    }
