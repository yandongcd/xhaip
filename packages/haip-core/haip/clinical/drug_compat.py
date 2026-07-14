"""Drug Compatibility — parenteral nutrition drug interaction rules.

Ported from haip-0710 skill: .openharness/skills/skill-drug-compatibility/SKILL.md
Trust: T1 (中华临床营养杂志 2018 + 中国药典)

10 core rules (DI001-DI010) for TPN compounding safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompatibilityResult:
    """Drug compatibility check result."""

    safe: bool
    warnings: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# Core incompatibility rules
INCOMPATIBILITY_RULES: list[dict[str, Any]] = [
    {
        "id": "DI001",
        "drug_a": "钙剂",
        "drug_b": "磷制剂",
        "risk": "磷酸钙沉淀",
        "action": "分管稀释后加入；钙磷乘积 < 50",
    },
    {
        "id": "DI002",
        "drug_a": "钙剂",
        "drug_b": "脂肪乳",
        "risk": "影响乳剂稳定性",
        "action": "钙先与氨基酸混合后再加入",
    },
    {
        "id": "DI003",
        "drug_a": "维生素K",
        "drug_b": "华法林",
        "risk": "药效拮抗",
        "action": "监测 INR，调整抗凝剂量",
    },
    {
        "id": "DI004",
        "drug_a": "维生素B1",
        "drug_b": "碱性药物",
        "risk": "不稳定分解",
        "action": "避免同一通路输注",
    },
    {
        "id": "DI005",
        "drug_a": "叶酸",
        "drug_b": "甲氨蝶呤",
        "risk": "影响疗效",
        "action": "注意用药顺序和时间间隔",
    },
    {
        "id": "DI006",
        "drug_a": "维生素E",
        "drug_b": "抗凝药",
        "risk": "协同增强",
        "action": "监测凝血功能",
    },
    {
        "id": "DI007",
        "drug_a": "胰岛素",
        "drug_b": "脂肪乳",
        "risk": "可能变性",
        "action": "分开输注或使用胰岛素泵",
    },
    {
        "id": "DI008",
        "drug_a": "维生素C",
        "drug_b": "维生素B12",
        "risk": "破坏B12",
        "action": "分开容器输注",
    },
    {
        "id": "DI009",
        "drug_a": "丙泊酚",
        "drug_b": "脂肪乳",
        "risk": "热量叠加",
        "action": "计入脂肪乳总量 (丙泊酚 0.9~1.1 kcal/mL)",
    },
    {
        "id": "DI010",
        "drug_a": "脂肪乳",
        "drug_b": "高浓度电解质",
        "risk": "破乳",
        "action": "一价阳离子 < 150 mmol/L；二价 < 10 mmol/L",
    },
]

# Drug class mapping for fuzzy matching
DRUG_CLASS_MAP: dict[str, list[str]] = {
    "钙剂": ["葡萄糖酸钙", "氯化钙", "钙", "Ca"],
    "磷制剂": ["甘油磷酸钠", "磷酸二氢钾", "磷酸", "磷", "PO4"],
    "脂肪乳": ["脂肪乳", "英脱利匹特", "力文", "Structolipid", "Intralipid"],
    "维生素K": ["维生素K", "VitK", "VK"],
    "华法林": ["华法林", "Warfarin"],
    "维生素B1": ["维生素B1", "VitB1", "硫胺素"],
    "碱性药物": ["碳酸氢钠", "NaHCO3"],
    "叶酸": ["叶酸", "Folic acid"],
    "甲氨蝶呤": ["甲氨蝶呤", "MTX"],
    "维生素E": ["维生素E", "VitE", "VE"],
    "抗凝药": ["华法林", "肝素", "低分子肝素", "利伐沙班", "达比加群"],
    "胰岛素": ["胰岛素", "诺和灵", "优泌林", "Insulin"],
    "维生素C": ["维生素C", "VitC", "VC", "抗坏血酸"],
    "维生素B12": ["维生素B12", "VitB12", "钴胺素"],
    "丙泊酚": ["丙泊酚", "得普利麻", "Propofol"],
}


def _matches_class(drug_name: str, drug_class: str) -> bool:
    """Check if a drug name matches a drug class (fuzzy)."""
    if drug_class not in DRUG_CLASS_MAP:
        return drug_name == drug_class
    keywords = DRUG_CLASS_MAP[drug_class]
    drug_lower = drug_name.lower()
    for kw in keywords:
        if kw.lower() in drug_lower or drug_lower in kw.lower():
            return True
    return False


def check_compatibility(drugs: list[str]) -> CompatibilityResult:
    """Check drug compatibility for a list of drug names.

    Args:
        drugs: List of drug names to check.

    Returns:
        CompatibilityResult with safety status, warnings, and violations.
    """
    result = CompatibilityResult(safe=True, warnings=[], violations=[], recommendations=[])

    for i, drug_a in enumerate(drugs):
        for j, drug_b in enumerate(drugs):
            if j <= i:
                continue

            for rule in INCOMPATIBILITY_RULES:
                class_a = rule["drug_a"]
                class_b = rule["drug_b"]

                match_a = _matches_class(drug_a, class_a)
                match_b = _matches_class(drug_b, class_b)
                match_rev = _matches_class(drug_a, class_b) and _matches_class(drug_b, class_a)

                if (match_a and match_b) or match_rev:
                    result.violations.append(
                        f"[{rule['id']}] {drug_a} + {drug_b}: {rule['risk']}"
                    )
                    result.recommendations.append(rule["action"])
                    result.safe = False

    # Check cation limits if TPN-related drugs present
    has_fat_emulsion = any("脂肪乳" in d for d in drugs)
    if has_fat_emulsion:
        result.warnings.append(
            "⚠ 脂肪乳配伍: 确保一价阳离子(Na⁺+K⁺) < 150 mmol/L, 二价阳离子(Ca²⁺+Mg²⁺) < 10 mmol/L"
        )

    if not result.safe:
        result.recommendations.insert(0, "配制顺序: 磷酸盐→电解质→钙盐→脂肪乳(最后加入)")

    return result


def check_cation_limits(
    sodium_mmol: float = 0,
    potassium_mmol: float = 0,
    calcium_mmol: float = 0,
    magnesium_mmol: float = 0,
) -> dict[str, Any]:
    """Check monovalent and divalent cation limits for TPN safety.

    Args:
        sodium_mmol: Sodium in mmol.
        potassium_mmol: Potassium in mmol.
        calcium_mmol: Calcium in mmol.
        magnesium_mmol: Magnesium in mmol.

    Returns:
        Dict with limit status and warnings.
    """
    monovalent = sodium_mmol + potassium_mmol
    divalent = calcium_mmol + magnesium_mmol

    warnings = []
    safe = True

    if monovalent > 150:
        warnings.append(f"一价阳离子 {monovalent} mmol/L 超过上限 150 mmol/L，有破乳风险")
        safe = False
    elif monovalent > 130:
        warnings.append(f"一价阳离子 {monovalent} mmol/L 接近上限 150 mmol/L")

    if divalent > 10:
        warnings.append(f"二价阳离子 {divalent} mmol/L 超过上限 10 mmol/L，有破乳风险")
        safe = False
    elif divalent > 8:
        warnings.append(f"二价阳离子 {divalent} mmol/L 接近上限 10 mmol/L")

    return {
        "safe": safe,
        "monovalent_total": monovalent,
        "monovalent_limit": 150,
        "divalent_total": divalent,
        "divalent_limit": 10,
        "warnings": warnings,
    }
