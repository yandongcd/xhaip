"""药剂科 营养途径推荐."""

def route(patient_id: str = "", gi_function: str = "", **kwargs):
    gi_ok = gi_function.lower() in ("normal", "ok", "functional", "正常", "可")
    return {
        "patient_id": patient_id, "gi_function": gi_function,
        "recommended_route": "EN" if gi_ok else "PN",
        "reason": "胃肠道功能正常，优先肠内营养" if gi_ok else "胃肠道功能障碍，推荐肠外营养",
    }
