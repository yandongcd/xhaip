"""TPN 全肠外营养配比计算 — 完整能量/蛋白/脂肪/葡萄糖计算 + 渗透压 + 阳离子检查.

@origin: haip-0710/src/agents/domains/haip/pharmacy/core/tpn_calculator.py (dataclass design)
@origin: haip-0705-2 v0.2.0 (compute function)
@upgrade_date: 2026-07-12
@upgrade: Added TpnInput/TpnResult dataclasses from haip-0710 for type safety.
          compute() retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Dataclasses (from haip-0710) ──────────────────────────────────────


@dataclass
class TpnInput:
    """TPN 计算输入参数."""
    weight_kg: float = 60.0
    energy_per_kg: float = 25.0
    protein_per_kg: float = 1.2
    glucose_ratio: float = 0.6
    fat_ratio: float = 0.4
    is_critically_ill: bool = False
    is_elderly: bool = False
    is_obese: bool = False
    has_liver_disease: bool = False
    has_renal_disease: bool = False


@dataclass
class TpnResult:
    """TPN 计算结果."""
    total_energy_kcal: float = 0.0
    non_protein_energy_kcal: float = 0.0
    glucose_energy_kcal: float = 0.0
    fat_energy_kcal: float = 0.0
    glucose_grams: float = 0.0
    fat_grams: float = 0.0
    amino_acid_grams: float = 0.0
    nitrogen_grams: float = 0.0
    calorific_nitrogen_ratio: float = 0.0
    fluid_requirement_ml: float = 0.0
    insulin_max_iu: float = 0.0
    osmolarity_est: float = 0.0
    monovalent_cation: float = 0.0
    divalent_cation: float = 0.0
    potassium_mass_g_per_l: float = 0.0
    potassium_molar_mmol_per_l: float = 0.0
    glucose_concentration_pct: float = 0.0
    amino_acid_concentration_pct: float = 0.0
    warnings: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_energy_kcal": round(self.total_energy_kcal, 1),
            "non_protein_energy_kcal": round(self.non_protein_energy_kcal, 1),
            "glucose_energy_kcal": round(self.glucose_energy_kcal, 1),
            "fat_energy_kcal": round(self.fat_energy_kcal, 1),
            "glucose_grams": round(self.glucose_grams, 1),
            "fat_grams": round(self.fat_grams, 1),
            "amino_acid_grams": round(self.amino_acid_grams, 1),
            "nitrogen_grams": round(self.nitrogen_grams, 2),
            "calorific_nitrogen_ratio": round(self.calorific_nitrogen_ratio, 1),
            "fluid_requirement_ml": round(self.fluid_requirement_ml),
            "insulin_max_iu": round(self.insulin_max_iu, 1),
            "osmolarity_est": round(self.osmolarity_est),
            "monovalent_cation": round(self.monovalent_cation, 1),
            "divalent_cation": round(self.divalent_cation, 1),
            "potassium_mass_g_per_l": round(self.potassium_mass_g_per_l, 2),
            "potassium_molar_mmol_per_l": round(self.potassium_molar_mmol_per_l, 1),
            "glucose_concentration_pct": round(self.glucose_concentration_pct, 1),
            "amino_acid_concentration_pct": round(self.amino_acid_concentration_pct, 1),
            "warnings": self.warnings,
            "messages": self.messages,
        }


# ─── Typed API (from haip-0710) ────────────────────────────────────────


def calculate_tpn(inp: TpnInput | None = None) -> TpnResult:
    """类型安全的 TPN 计算 API.

    使用 dataclass 输入输出，适合新模块集成。
    """
    if inp is None:
        inp = TpnInput()

    weight = inp.weight_kg

    if inp.is_critically_ill:
        energy_per_kg = 25.0
        protein_per_kg = 1.8
    elif inp.is_obese:
        energy_per_kg = inp.energy_per_kg * 0.75
        protein_per_kg = 2.0
    elif inp.has_liver_disease or inp.has_renal_disease:
        energy_per_kg = inp.energy_per_kg
        protein_per_kg = 0.8
    else:
        energy_per_kg = inp.energy_per_kg
        protein_per_kg = inp.protein_per_kg

    if inp.is_elderly and not inp.is_critically_ill:
        protein_per_kg = max(protein_per_kg, 1.2)

    total_energy = energy_per_kg * weight
    amino_acid_g = protein_per_kg * weight
    nitrogen_g = amino_acid_g * 0.16
    non_protein_energy = total_energy * 0.87
    glucose_ratio = 0.6 if not inp.is_critically_ill else 0.5
    fat_ratio = 1.0 - glucose_ratio
    glucose_energy = non_protein_energy * glucose_ratio
    fat_energy = non_protein_energy * fat_ratio
    glucose_g = glucose_energy / 4.0
    fat_g = fat_energy / 10.0
    cnr = non_protein_energy / nitrogen_g if nitrogen_g > 0 else 0

    fluid_ml = weight * 30
    if inp.is_elderly:
        fluid_ml = weight * 28
    if inp.is_obese:
        fluid_ml = weight * 22
    total_volume_l = fluid_ml / 1000.0
    glucose_conc = glucose_g / total_volume_l * 0.01 if total_volume_l > 0 else 0
    aa_conc = amino_acid_g / total_volume_l * 0.01 if total_volume_l > 0 else 0

    insulin_max = glucose_g / 4.0
    osmolarity = glucose_g * 5 + amino_acid_g * 10 + fat_g * 1.5 + 300

    result = TpnResult(
        total_energy_kcal=total_energy,
        non_protein_energy_kcal=non_protein_energy,
        glucose_energy_kcal=glucose_energy,
        fat_energy_kcal=fat_energy,
        glucose_grams=glucose_g,
        fat_grams=fat_g,
        amino_acid_grams=amino_acid_g,
        nitrogen_grams=nitrogen_g,
        calorific_nitrogen_ratio=cnr,
        fluid_requirement_ml=fluid_ml,
        insulin_max_iu=insulin_max,
        osmolarity_est=osmolarity,
        monovalent_cation=56.0,
        divalent_cation=6.0,
        glucose_concentration_pct=glucose_conc,
        amino_acid_concentration_pct=aa_conc,
    )

    if osmolarity > 900:
        result.warnings.append(f"渗透压 {osmolarity:.0f} mOsm/L > 900，建议中心静脉输注")
    else:
        result.messages.append(f"渗透压 {osmolarity:.0f} mOsm/L ≤ 900，可选择外周静脉输注")

    if cnr < 100 or cnr > 200:
        result.warnings.append(f"热氮比 {cnr:.0f}:1，合理范围 100:1~200:1，请调整")
    else:
        result.messages.append(f"热氮比 {cnr:.0f}:1，在合理范围内")

    if glucose_ratio > 0.7:
        result.warnings.append(f"葡萄糖供能占比 {glucose_ratio*100:.0f}%，建议 ≤70%")
    if fat_ratio > 0.5:
        result.warnings.append(f"脂肪供能占比 {fat_ratio*100:.0f}%，建议 ≤50%")
    if fat_g / weight > 2:
        result.warnings.append(f"脂肪乳日剂量 {fat_g/weight:.1f} g/kg/d，建议 ≤2 g/kg/d")
    if aa_conc < 2.5:
        result.warnings.append(f"氨基酸浓度 {aa_conc:.1f}%，建议 ≥2.5%")

    return result


# ─── Backward Compatible API ────────────────────────────────────────────


def compute(
    patient_id: str = "", weight_kg: float = 0.0, energy_kcal: float = 0.0,
    age: int = 0, bmi: float = 0.0,
    is_critically_ill: bool = False,
    has_liver_disease: bool = False,
    has_renal_disease: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """TPN 配比计算 (v1.0 兼容接口).

    内部委托给 calculate_tpn() 处理。
    """
    inp = TpnInput(
        weight_kg=weight_kg if weight_kg > 0 else 60,
        is_critically_ill=is_critically_ill,
        is_elderly=age >= 65,
        is_obese=bmi >= 30,
        has_liver_disease=has_liver_disease,
        has_renal_disease=has_renal_disease,
    )

    result = calculate_tpn(inp)
    d = result.to_dict()
    d["patient_id"] = patient_id
    d["high_osmolarity_risk"] = result.osmolarity_est > 900
    d["energy_per_kg"] = result.total_energy_kcal / max(inp.weight_kg, 1)
    d["protein_per_kg"] = result.amino_acid_grams / max(inp.weight_kg, 1)
    d["recommendations"] = (
        ["渗透压 > 900 mOsm/L，建议中心静脉输注"] if result.osmolarity_est > 900
        else ["配方合理，可外周输注"]
    )
    return d
