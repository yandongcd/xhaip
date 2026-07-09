"""药剂科 处方审核."""

def check(patient_id: str = "", prescription_items: list | None = None, **kwargs):
    items = prescription_items or []
    warnings = []
    for item in items:
        name = item.get("name", "")
        dose = item.get("dose", "")
        if "华法林" in name and any("肝素" in i.get("name", "") for i in items):
            warnings.append("华法林与肝素联用，需每日监测 INR")
        if "庆大霉素" in name and any("呋塞米" in i.get("name", "") for i in items):
            warnings.append("氨基糖苷类与利尿剂联用，肾毒性风险增加")
    return {
        "patient_id": patient_id, "items_count": len(items),
        "risk_level": "高" if len(warnings) >= 2 else ("中" if warnings else "低"),
        "warnings": warnings, "passed": len(warnings) == 0,
    }
