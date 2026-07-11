"""介入疼痛治疗评估 — 适应症筛选 + 影像学准入 + 术后安全监测.

Port from haip-0705-2 v0.2.0.
"""

from __future__ import annotations

from typing import Any

IMAGING_REQUIREMENTS = {
    "神经阻滞": ["超声引导/C臂"],
    "脉冲射频": ["C臂/CT引导"],
    "射频热凝": ["C臂/CT引导"],
    "椎体成形术": ["术前MRI", "C臂引导"],
    "椎间孔镜/脊柱内镜": ["术前MRI", "术中C臂/CT"],
}

PROCEDURES = [
    {"name": "神经阻滞",
     "indications": ["腰椎间盘", "神经根", "带状疱疹", "三叉神经", "枕神经", "肋间神经"],
     "contra_abs": ["感染", "凝血障碍"]},
    {"name": "脉冲射频 (PRF)",
     "indications": ["神经根", "带状疱疹", "膝关节炎"],
     "contra_abs": ["感染", "凝血障碍"]},
    {"name": "射频热凝 (RFA)",
     "indications": ["小关节", "骶髂关节", "三叉神经", "膝关节炎"],
     "contra_abs": ["感染", "凝血障碍"]},
    {"name": "椎体成形术",
     "indications": ["骨质疏松", "压缩性骨折", "椎体转移"],
     "contra_abs": ["感染", "凝血障碍", "后壁不完整"]},
    {"name": "椎间孔镜/脊柱内镜",
     "indications": ["腰椎间盘突出", "腰椎管狭窄"],
     "contra_abs": ["感染", "凝血障碍", "马尾", "不稳定"]},
]


def assess_indications(
    patient_id: str = "",
    diagnosis: str = "",
    pain_nrs: int = 0, duration_months: int = 0,
    has_infection: bool = False,
    lab_inr: float = 0.0, lab_plt: float = 250.0,
    pacemaker: bool = False,
    **kwargs: Any,
) -> dict:
    """介入治疗适应症评估 — 5 种手术方案匹配."""
    dx = (diagnosis or "").lower()
    has_coagulopathy = lab_inr > 1.5 or lab_plt < 50

    eligible: list[dict] = []
    for proc in PROCEDURES:
        match = any(ind in dx for ind in proc["indications"])
        if not match:
            continue
        contra_triggered: list[str] = []
        if has_infection:
            contra_triggered.append("穿刺部位感染")
        if has_coagulopathy:
            contra_triggered.append("凝血功能障碍")
        for c in proc["contra_abs"]:
            if c in dx:
                contra_triggered.append(c)
        if pacemaker and proc["name"] in ("脉冲射频", "射频热凝", "脊髓电刺激"):
            contra_triggered.append("体内电子设备")

        suit = "绝对禁忌" if len(contra_triggered) >= 1 else "适应"
        score = 0 if suit == "绝对禁忌" else 90
        if duration_months >= 3 and suit == "适应":
            score += 5
        if pain_nrs >= 5 and suit == "适应":
            score += 5

        eligible.append({
            "name": proc["name"],
            "suitability": suit,
            "score": min(score, 100),
            "contraindications": contra_triggered,
        })

    eligible.sort(key=lambda p: p["score"], reverse=True)
    top = eligible[0]["name"] if eligible else "暂无适用方案"
    indicated = len(eligible) > 0

    return {
        "status": "ok",
        "indicated": indicated,
        "patient_id": patient_id,
        "eligible_procedures": eligible,
        "summary": f"介入治疗评估: 首选={top} ({len(eligible)}项可选)",
    }


def gate(has_mri: bool = False, has_ct: bool = False,
         target_procedure: str = "", completed_exams: list | None = None,
         **kwargs: Any) -> dict:
    """影像学准入检查 — 按手术类型验证."""
    gate_passed = has_mri or has_ct
    missing: list[str] = []

    if target_procedure and completed_exams:
        required = IMAGING_REQUIREMENTS.get(target_procedure, [])
        _MODALITIES = {"MRI", "CT", "C臂", "超声", "X线"}
        for req in required:
            req_mods = {m for m in _MODALITIES if m.lower() in req.lower()}
            matched = any(
                any(m.lower() in ex.lower() for m in req_mods) for ex in completed_exams
            )
            if not matched:
                missing.append(req)
        gate_passed = len(missing) == 0

    return {
        "status": "ok",
        "gate_passed": gate_passed,
        "has_mri": has_mri, "has_ct": has_ct,
        "missing_exams": missing if missing else (["无"] if gate_passed else ["缺失必需影像"]),
        "summary": f"影像学准入: {'PASS' if gate_passed else f'FAIL-缺{len(missing)}项'}",
    }


def postop(procedure: str = "", signs: dict | None = None,
           vital_signs: dict | None = None,
           postop_hours: int = 0, pain_nrs: int = 0,
           neurological: str = "",
           **kwargs: Any) -> dict:
    """术后安全监测 — 感染/神经损伤/出血/血肿."""
    signs = signs or {}
    vs = vital_signs or signs
    temp = float(vs.get("temp", 37))
    hr = float(vs.get("hr", 72))
    neuro = (neurological or "").lower()
    postop_h = postop_hours or 999

    complication_detected = False
    complications: list[str] = []
    alerts: list[str] = []

    if postop_h <= 72:
        if temp > 38.0 and (hr > 90 or pain_nrs > 6):
            complication_detected = True
            complications.append("术后感染")
            alerts.append(f"体温 {temp}℃ + HR {hr}bpm — 疑似{procedure}术后感染")
        if temp > 38.5:
            complication_detected = True
            if "术后感染" not in complications:
                complications.append("感染")
            alerts.append("血培养+CRP+ESR+影像，抗生素经验治疗，通知主管医生")
        if "肌力" in neuro or "感觉减退" in neuro or "无力" in neuro:
            complication_detected = True
            complications.append("神经损伤")
            alerts.append(f"术后神经功能缺损 — {neurological}")
            alerts.append("急诊 MRI 评估，通知主刀医生")
        if "出血" in neuro or "血肿" in neuro or pain_nrs >= 9:
            complication_detected = True
            if "神经损伤" not in complications:
                complications.append("出血/血肿")
            alerts.append("急诊 CT/MRI 排除椎管内血肿，测凝血功能")

    # Backward compatible signs-based check
    if not complication_detected:
        if signs.get("temp", 0) > 38.0:
            complication_detected = True
            complications.append("fever")
        if signs.get("redness") or signs.get("swelling"):
            complication_detected = True
            complications.append("local_infection")
        if signs.get("neurologic_deficit"):
            complication_detected = True
            complications.append("neurologic")

    if not complication_detected:
        alerts = ["术后恢复正常"]

    return {
        "status": "ok",
        "complication_detected": complication_detected,
        "complications": complications,
        "alerts": alerts,
        "procedure": procedure,
        "summary": (
            f"术后并发症预警: {', '.join(complications)} — {len(alerts)}项告警" if complication_detected
            else "术后72h安全监测: PASS"
        ),
    }
