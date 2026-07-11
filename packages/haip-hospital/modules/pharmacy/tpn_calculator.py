"""药剂科 TPN 配比计算 — 完整能量/蛋白/脂肪/葡萄糖计算 + 渗透压 + 阳离子检查.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any


def compute(
    patient_id: str = "", weight_kg: float = 0.0, energy_kcal: float = 0.0,
    age: int = 0, bmi: float = 0.0,
    is_critically_ill: bool = False,
    has_liver_disease: bool = False,
    has_renal_disease: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """TPN 全肠外营养配比计算.

    Backward compatible with v1.0; enhanced with clinical condition adjustments.
    """
    weight = weight_kg if weight_kg > 0 else 60
    is_elderly = age >= 65
    is_obese = bmi >= 30

    # Energy calculation
    if is_critically_ill:
        energy_per_kg = 25.0
        protein_per_kg = 1.8
        glucose_ratio = 0.5
        fat_ratio = 0.5
    elif is_obese:
        energy_per_kg = 18.0
        protein_per_kg = 2.0
        glucose_ratio = 0.6
        fat_ratio = 0.4
    elif has_liver_disease or has_renal_disease:
        energy_per_kg = 25.0
        protein_per_kg = 0.8
        glucose_ratio = 0.6
        fat_ratio = 0.4
    else:
        energy_per_kg = 25.0
        protein_per_kg = 1.2
        glucose_ratio = 0.6
        fat_ratio = 0.4

    if is_elderly and not is_critically_ill:
        protein_per_kg = max(protein_per_kg, 1.2)

    total_energy = energy_per_kg * weight
    amino_acid_g = protein_per_kg * weight
    nitrogen_g = amino_acid_g * 0.16
    non_protein_energy = total_energy * 0.87

    glucose_energy = non_protein_energy * glucose_ratio
    fat_energy = non_protein_energy * fat_ratio
    glucose_g = glucose_energy / 4.0
    fat_g = fat_energy / 10.0
    cnr = non_protein_energy / nitrogen_g if nitrogen_g > 0 else 0

    fluid_ml = weight * 30
    if is_elderly:
        fluid_ml = weight * 28
    if is_obese:
        fluid_ml = (weight * 0.75) * 30

    total_volume_l = fluid_ml / 1000.0
    glucose_conc = glucose_g / total_volume_l * 0.01 if total_volume_l > 0 else 0
    aa_conc = amino_acid_g / total_volume_l * 0.01 if total_volume_l > 0 else 0
    osmolarity = glucose_g * 5 + amino_acid_g * 10 + fat_g * 1.5 + 300

    high_osmolarity = osmolarity > 900
    mono_cation = 56.0
    di_cation = 6.0

    # Warnings
    warnings: list[str] = []
    messages: list[str] = []
    if osmolarity > 900:
        warnings.append(f"渗透压 {osmolarity:.0f} mOsm/L > 900，建议中心静脉输注")
    else:
        messages.append(f"渗透压 {osmolarity:.0f} mOsm/L ≤ 900，可选择外周静脉输注")
    if cnr < 100 or cnr > 200:
        warnings.append(f"热氮比 {cnr:.0f}:1，合理范围 100:1~200:1，请调整")
    else:
        messages.append(f"热氮比 {cnr:.0f}:1，在合理范围内")
    if glucose_ratio > 0.7:
        warnings.append(f"葡萄糖供能占比 {glucose_ratio*100:.0f}%，建议 ≤70%")
    if fat_ratio > 0.5:
        warnings.append(f"脂肪供能占比 {fat_ratio*100:.0f}%，建议 ≤50%")
    if fat_g / weight > 2:
        warnings.append(f"脂肪乳日剂量 {fat_g/weight:.1f} g/kg/d，建议 ≤2 g/kg/d")
    if aa_conc < 2.5:
        warnings.append(f"氨基酸浓度 {aa_conc:.1f}%，建议 ≥2.5%")

    return {
        "patient_id": patient_id,
        "total_energy_kcal": round(total_energy, 1),
        "non_protein_energy_kcal": round(non_protein_energy, 1),
        "amino_acid_g": round(amino_acid_g, 1),
        "lipid_g": round(fat_g, 1),
        "glucose_g": round(glucose_g, 1),
        "nitrogen_g": round(nitrogen_g, 2),
        "calorific_nitrogen_ratio": round(cnr, 1),
        "fluid_requirement_ml": round(fluid_ml),
        "glucose_concentration_pct": round(glucose_conc, 1),
        "amino_acid_concentration_pct": round(aa_conc, 1),
        "osmolarity_mOsmL": round(osmolarity),
        "high_osmolarity_risk": high_osmolarity,
        "monovalent_cation_mmolL": round(mono_cation, 1),
        "divalent_cation_mmolL": round(di_cation, 1),
        "energy_per_kg": energy_per_kg,
        "protein_per_kg": protein_per_kg,
        "warnings": warnings,
        "messages": messages,
        "recommendations": (
            ["渗透压 > 900 mOsm/L，建议中心静脉输注"] if high_osmolarity
            else ["配方合理，可外周输注"]
        ),
    }
