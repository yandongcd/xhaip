"""药剂科 TPN 配比计算."""

def compute(patient_id: str = "", weight_kg: float = 0.0, energy_kcal: float = 0.0, **kwargs):
    if energy_kcal <= 0:
        energy_kcal = weight_kg * 25  # 默认 25 kcal/kg

    amino_g = round(weight_kg * 1.2, 1)    # 1.2g/kg 氨基酸
    lipid_g = round(weight_kg * 1.0, 1)    # 1.0g/kg 脂肪乳
    glucose_g = round((energy_kcal - amino_g * 4 - lipid_g * 9) / 4, 1)

    osmolarity = round(amino_g * 10 + glucose_g * 5 + 300, 0)
    high_osmolarity = osmolarity > 1200

    return {
        "patient_id": patient_id, "energy_kcal": energy_kcal,
        "amino_acid_g": amino_g, "lipid_g": lipid_g, "glucose_g": glucose_g,
        "osmolarity_mOsmL": osmolarity,
        "high_osmolarity_risk": high_osmolarity,
        "recommendations": (
            ["渗透压 > 1200 mOsm/L, 建议中心静脉输注"] if high_osmolarity
            else ["配方合理, 可外周输注"]
        ),
    }
