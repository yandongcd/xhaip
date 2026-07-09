"""药剂科 — 完整处方审核规则库 (17 条药物交互规则).

业务流来源:
  - 中国药典 2020
  - 国家处方集
  - ESPEN / CSPEN 肠外营养指南
"""

from __future__ import annotations

from typing import Any

# ═══════════════════════════════════════════
# 药物交互规则库
# ═══════════════════════════════════════════

DRUG_INTERACTION_RULES = [
    # 抗凝相关 (4条)
    {"id": "D01", "drugs": ["华法林", "warfarin"], "interact": ["肝素", "heparin", "低分子肝素", "LMWH", "enoxaparin"],
     "risk": "出血风险×3", "severity": "high", "action": "每日监测 INR, 目标 2.0-3.0"},
    {"id": "D02", "drugs": ["华法林", "warfarin"], "interact": ["阿司匹林", "aspirin", "氯吡格雷", "clopidogrel"],
     "risk": "消化道出血", "severity": "high", "action": "加用 PPI, 评估获益风险比"},
    {"id": "D03", "drugs": ["华法林", "warfarin"], "interact": ["胺碘酮", "amiodarone"],
     "risk": "INR升高", "severity": "high", "action": "华法林减量 30-50%, 频繁监测 INR"},
    {"id": "D04", "drugs": ["NOAC", "利伐沙班", "rivaroxaban", "阿哌沙班", "apixaban"],
     "interact": ["酮康唑", "伊曲康唑", "ritonavir"],
     "risk": "NOAC 血药浓度升高", "severity": "high", "action": "避免联用, 换用其他抗真菌药"},

    # 抗生素相关 (3条)
    {"id": "D05", "drugs": ["氨基糖苷类", "庆大霉素", "gentamicin", "阿米卡星", "amikacin"],
     "interact": ["呋塞米", "furosemide", "依他尼酸"],
     "risk": "肾毒性×2", "severity": "high", "action": "避免联用, 监测肾功能 qd"},
    {"id": "D06", "drugs": ["头孢曲松", "ceftriaxone"],
     "interact": ["钙剂", "calcium", "葡萄糖酸钙"],
     "risk": "肺肾钙-头孢曲松沉淀", "severity": "critical",
     "action": "新生儿禁忌, 成人间隔 48h, 不可同管输注"},
    {"id": "D07", "drugs": ["甲硝唑", "metronidazole"],
     "interact": ["华法林", "warfarin"],
     "risk": "INR升高", "severity": "moderate", "action": "监测 INR, 必要时减量"},

    # 电解质/TPN 相关 (3条)
    {"id": "D08", "drugs": ["钙", "calcium", "葡萄糖酸钙"],
     "interact": ["磷", "phosphate", "磷酸盐"],
     "risk": "磷酸钙沉淀", "severity": "critical", "action": "不可同管输注, TPN 中钙/磷摩尔比<45"},
    {"id": "D09", "drugs": ["脂肪乳", "lipid"],
     "interact": ["钠", "sodium", "氯化钠"],
     "risk": "脂肪乳破乳", "severity": "high", "action": "Na+ > 100mmol/L 时慎用, 一价阳离子<150mmol/L"},
    {"id": "D10", "drugs": ["钾", "potassium", "KCl"],
     "interact": ["ACEI", "ARB", "螺内酯", "spironolactone"],
     "risk": "高钾血症", "severity": "high", "action": "监测血钾 qd, K < 5.5 mmol/L"},

    # 镇痛/镇静 (3条)
    {"id": "D11", "drugs": ["阿片类", "吗啡", "morphine", "芬太尼", "fentanyl", "羟考酮", "oxycodone"],
     "interact": ["苯二氮䓬类", "地西泮", "diazepam", "咪达唑仑", "midazolam"],
     "risk": "呼吸抑制×2", "severity": "critical", "action": "避免联用, 如必需则监测 SpO2 持续 + 纳洛酮备用"},
    {"id": "D12", "drugs": ["NSAIDs", "布洛芬", "ibuprofen", "双氯芬酸", "diclofenac"],
     "interact": ["华法林", "warfarin", "阿司匹林", "aspirin"],
     "risk": "消化道出血", "severity": "high", "action": "加用 PPI, 短期使用 (<5天)"},
    {"id": "D13", "drugs": ["对乙酰氨基酚", "paracetamol", "acetaminophen"],
     "interact": ["酒精", "alcohol", "乙醇"],
     "risk": "肝毒性×2", "severity": "high", "action": "日剂量<2g, 避免饮酒"},

    # 心血管/代谢 (4条)
    {"id": "D14", "drugs": ["ACEI", "ARB", "卡托普利", "captopril", "依那普利", "enalapril"],
     "interact": ["钾补充剂", "KCl", "螺内酯", "spironolactone"],
     "risk": "高钾血症", "severity": "high", "action": "监测血钾, 避免同时补钾"},
    {"id": "D15", "drugs": ["他汀类", "atorvastatin", "simvastatin", "rosuvastatin", "阿托伐他汀"],
     "interact": ["克拉霉素", "clarithromycin", "红霉素", "erythromycin"],
     "risk": "横纹肌溶解", "severity": "high", "action": "暂停他汀至抗生素疗程结束, 或换用阿奇霉素"},
    {"id": "D16", "drugs": ["胰岛素", "insulin"],
     "interact": ["β-阻滞剂", "美托洛尔", "metoprolol", "普萘洛尔", "propranolol"],
     "risk": "迟发型低血糖", "severity": "moderate", "action": "密切监测血糖, 调整胰岛素剂量"},
    {"id": "D17", "drugs": ["地高辛", "digoxin"],
     "interact": ["胺碘酮", "amiodarone", "维拉帕米", "verapamil"],
     "risk": "地高辛中毒 (心律失常)", "severity": "high", "action": "地高辛减量 50%, 监测血药浓度+ECG"},
]


def full_review(
    patient_id: str = "",
    prescription_items: list[dict] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """完整处方审核: 17 条药物交互规则。

    prescription_items: [{"name": "华法林", "dose": "2.5mg qd"}, ...]
    """
    items = prescription_items or []
    drug_names = [item.get("name", "").lower() for item in items]
    all_text = " ".join(drug_names)

    warnings: list[dict] = []
    critical_count = 0
    high_count = 0

    for rule in DRUG_INTERACTION_RULES:
        has_drug = any(d in all_text for d in rule["drugs"])
        has_interact = any(i in all_text for i in rule["interact"])
        if has_drug and has_interact:
            warnings.append({
                "rule_id": rule["id"], "risk": rule["risk"],
                "severity": rule["severity"], "action": rule["action"],
            })
            if rule["severity"] == "critical":
                critical_count += 1
            elif rule["severity"] == "high":
                high_count += 1

    passed = critical_count == 0 and high_count == 0
    risk = "critical" if critical_count > 0 else "high" if high_count > 0 else "low"

    return {
        "patient_id": patient_id, "items_count": len(items),
        "warnings_count": len(warnings), "critical": critical_count, "high": high_count,
        "risk_level": risk, "passed": passed, "warnings": warnings,
        "evidence": ["中国药典2020", "国家处方集", "Drugs.com Interaction Checker"],
    }
