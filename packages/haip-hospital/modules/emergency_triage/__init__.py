"""急诊预检分诊智能体 — 三区四级 + 红旗识别 + 绿色通道.

业务流来源:
  - 中国急诊预检分诊专家共识 (2018)
  - 三区四级分诊标准 (卫健委 2011)
  - FAST 卒中快速筛查
  - 南方医院急诊分诊SOP (T2)
"""
from __future__ import annotations

import math
import re

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="emergency-triage", department="急诊科")
_GUIDELINES = [
    "中国急诊预检分诊专家共识 (2018)",
    "三区四级分诊标准 (卫健委 2011)",
    "FAST 卒中快速筛查 (AHA/ASA)",
    "南方医院急诊分诊SOP (T2适配)",
]
_agent.rule_engine.load_all()

# ── 三区四级分诊规则 ──

# Level I: 濒危 (Red Zone) — 立即抢救
LEVEL_I_CRITERIA = [
    "心脏骤停", "呼吸停止", "严重呼吸窘迫(SpO2<85%)",
    "收缩压<70mmHg", "意识丧失(GCS≤8)", "癫痫持续状态",
    "严重创伤(ISS>16, 活动性大出血)", "过敏性休克",
    "急性心肌梗死(ST段抬高+胸痛+大汗)",
]

# Level II: 危重 (Red Zone) — 15分钟内处理
LEVEL_II_CRITERIA = [
    "SpO2 85-92%", "收缩压<90mmHg", "HR>150或<40",
    "意识改变(GCS 9-13)", "严重呼吸困难", "胸痛(疑似ACS)",
    "卒中(FAST阳性, 发病<4.5h)", "严重创伤(ISS 9-15)",
    "高热>41°C", "严重疼痛(NRS≥7)", "活动性出血(可控)",
]

# Level III: 急症 (Yellow Zone) — 30分钟内处理
LEVEL_III_CRITERIA = [
    "轻度呼吸困难(SpO2>92%)", "中度疼痛(NRS 4-6)",
    "发热39-41°C", "轻度脱水", "稳定创伤(ISS<9)",
    "腹痛(非急腹症)", "头晕/眩晕(非卒中)", "轻度过敏反应",
]

# Level IV: 非急症 (Green Zone) — 可等待
LEVEL_IV_CRITERIA = [
    "轻微外伤", "轻度疼痛(NRS<4)", "低热<39°C",
    "慢性病复诊", "皮肤问题", "健康咨询",
]

# Red flag patterns for specific diseases
RED_FLAG_PATTERNS = {
    "胸痛_ACS": ["胸痛", "胸闷", "压榨感", "放射痛", "大汗", "恶心"],
    "卒中": ["面瘫", "口角歪斜", "肢体无力", "言语不清", "突发行走不稳", "剧烈头痛"],
    "严重创伤": ["车祸", "坠落", "高能量损伤", "多发伤", "开放性骨折", "活动性出血"],
    "呼吸困难": ["严重呼吸困难", "端坐呼吸", "发绀", "三凹征"],
    "意识障碍": ["意识不清", "昏迷", "抽搐", "持续癫痫"],
    "休克": ["低血压", "皮肤湿冷", "少尿", "意识改变", "脉细速"],
    "过敏": ["皮疹+呼吸困难", "喉头水肿", "过敏性休克史"],
    "大出血": ["呕血", "黑便", "咯血", "大量阴道出血", "外伤大出血"],
}


def triage_assess(**kwargs) -> dict:
    """三区四级分诊评估."""
    pid = kwargs.get("patient_id", "")
    chief = kwargs.get("chief_complaint", "")
    vitals = kwargs.get("vital_signs", {})

    level = "III"
    zone = "黄区"
    basis = []

    cc = chief.lower() if chief else ""

    # Level I check
    for c in LEVEL_I_CRITERIA:
        if _match(cc, c, vitals):
            level = "I"
            zone = "红区"
            basis.append(f"濒危—{c}")
            break

    # Level II check
    if level == "III":
        for c in LEVEL_II_CRITERIA:
            if _match(cc, c, vitals):
                level = "II"
                zone = "红区"
                basis.append(f"危重—{c}")
                break

    # Level IV check
    if level == "III":
        for c in LEVEL_IV_CRITERIA:
            if _match(cc, c, vitals):
                level = "IV"
                zone = "绿区"
                basis.append(f"非急症—{c}")
                break

    if not basis:
        basis.append("急症—需进一步评估")

    guides = _agent.search_guidelines("急诊分诊") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"分诊评估 — {level}级 {zone}",
        findings=[{"分诊级别": level, "分区": zone, "依据": basis}],
        guidelines=guides,
        recommendations=[
            f"{zone}{level}级 → {'立即抢救' if level == 'I' else '需紧急处理' if level == 'II' else '优先处理' if level == 'III' else '可等待'}",
            "所有AI分诊建议须经分诊护士确认",
        ],
    )


def red_flag_detect(**kwargs) -> dict:
    """危险信号识别."""
    chief = kwargs.get("chief_complaint", "")
    vitals = kwargs.get("vital_signs", {})
    cc = chief.lower() if chief else ""

    red_flags = []
    for flag_name, keywords in RED_FLAG_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in cc)
        if score >= 2:
            red_flags.append({"flag": flag_name, "matched": score, "keywords": [kw for kw in keywords if kw in cc]})

    # Vital sign based flags
    if isinstance(vitals, dict):
        spo2 = float(vitals.get("SpO2", 100) or 100)
        sbp = float(vitals.get("SBP", 120) or 120)
        gcs = int(vitals.get("GCS", 15) or 15)

        if spo2 < 90:
            red_flags.append({"flag": "低氧血症", "value": f"SpO2={spo2}%"})
        if sbp < 90:
            red_flags.append({"flag": "休克_低血压", "value": f"SBP={sbp}mmHg"})
        if gcs <= 8:
            red_flags.append({"flag": "意识障碍_GCS≤8", "value": f"GCS={gcs}"})

    return {
        "status": "ok",
        "red_flags": red_flags,
        "count": len(red_flags),
        "alert": "🔴 存在危险信号" if red_flags else "✅ 未检测到危险信号",
    }


def green_channel_check(**kwargs) -> dict:
    """绿色通道触发检查."""
    chief = kwargs.get("chief_complaint", "")
    red_flags = kwargs.get("red_flags", [])
    cc = chief.lower() if chief else ""

    channels = []

    # Chest pain center
    if any(kw in cc for kw in ["胸痛", "胸闷", "心梗"]):
        channels.append("胸痛中心绿色通道")
    if any(r.get("flag") == "胸痛_ACS" for r in red_flags):
        channels.append("胸痛中心绿色通道")

    # Stroke center — FAST
    if any(kw in cc for kw in ["面瘫", "肢体无力", "言语不清", "口角歪斜"]):
        channels.append("卒中中心绿色通道")

    # Trauma center
    if any(kw in cc for kw in ["车祸", "坠落", "高能量", "多发伤"]):
        channels.append("创伤中心绿色通道")

    # Upper GI bleeding
    if any(kw in cc for kw in ["呕血", "黑便", "血便"]):
        channels.append("危险性上消化道出血绿色通道")

    # High-risk pregnancy
    if any(kw in cc for kw in ["孕妇", "孕", "产前出血", "子痫"]):
        channels.append("高危孕产妇绿色通道")

    return {
        "status": "ok",
        "channels": channels,
        "action": f"建议启动: {', '.join(channels)}" if channels else "无需启动绿色通道",
    }


def triage_record(**kwargs) -> dict:
    """生成结构化分诊记录."""
    pid = kwargs.get("patient_id", "")
    level = kwargs.get("triage_level", "")
    zone = kwargs.get("triage_zone", "")
    red_flags = kwargs.get("red_flags", [])
    basis = kwargs.get("basis", "")

    record = {
        "患者ID": pid,
        "分诊时间": "2026-07-26",  # production: datetime.now()
        "分诊级别": f"{level}级",
        "分诊区域": zone,
        "危险信号": red_flags if isinstance(red_flags, list) else [],
        "分诊依据": basis,
        "AI建议": "仅供分诊护士参考，最终以医护人员判断为准",
        "分诊护士": "__________",
        "确认时间": "__________",
    }

    return {
        "status": "ok",
        "summary": f"分诊记录 — {level}级{zone}",
        "record": record,
        "disclaimer": "本记录为AI辅助生成，须经分诊护士审核签名后方可归档",
    }


_VITAL_ALIASES = {
    "spo2": "SpO2", "收缩压": "SBP", "hr": "HR", "gcs": "GCS",
    "高热": "Temp", "发热": "Temp", "低热": "Temp", "体温": "Temp",
}


def _vital_value(vitals: dict, key: str) -> float | None:
    """Read a vital value safely; unparseable/missing → None (never matches)."""
    v = vitals.get(key, vitals.get(key.lower()))
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _vital_match(criterion: str, vitals: dict) -> bool:
    """Compare numeric vital thresholds embedded in a criterion against vitals.

    Handles: SpO2<85% / SpO2 85-92% / SpO2>92%, 收缩压<90mmHg,
    HR>150或<40, GCS≤8 / GCS 9-13, 高热>41°C / 发热39-41°C / 低热<39°C.
    Missing or unparseable values never match (no existence-only hit).
    """
    if not isinstance(vitals, dict):
        return False
    lower = criterion.lower()
    last_key: str | None = None
    for part in re.split(r"或", lower):
        part = part.strip()
        if not part:
            continue
        key = next((k for alias, k in _VITAL_ALIASES.items() if alias in part), None)
        if key is None:
            key = last_key
        else:
            last_key = key
        if key is None:
            continue
        v = _vital_value(vitals, key)
        if v is None:
            continue
        m = re.search(r"(\d+)\s*[-–]\s*(\d+)", part)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            if lo <= v <= hi:
                return True
        for op, thr in re.findall(r"([<>]=?|≤|≥)\s*(\d+)", part):
            t = float(thr)
            if op == "<" and v < t:
                return True
            if op in ("<=", "≤") and v <= t:
                return True
            if op == ">" and v > t:
                return True
            if op in (">=", "≥") and v >= t:
                return True
    return False


def _keyword_keys(criterion: str) -> list[str]:
    """Build match keywords: strip parenthetical content (() and （）),
    then split on 或 and / so semantic keywords become matchable."""
    keys: list[str] = []
    for part in re.split(r"[或/]", criterion.lower()):
        for ch in "()（）":
            part = part.split(ch, 1)[0]
        part = part.strip(" ,，、;；+")
        if part:
            keys.append(part)
    return keys


def _match(text: str, criterion: str, vitals: dict) -> bool:
    """Keyword matching (parenthetical-stripped) + numeric vital threshold check."""
    if any(kw in text for kw in _keyword_keys(criterion)):
        return True
    return _vital_match(criterion, vitals)


# ── v2.0 扩展: 群伤检伤分类 START ──


def mass_casualty_triage(**kwargs) -> dict:
    """START 群伤检伤分类 — Simple Triage and Rapid Treatment.

    适用于灾难/重大事故/批量伤员场景.
    分类: RED(立即)/YELLOW(延迟)/GREEN(轻伤)/BLACK(死亡).
    """
    patients = kwargs.get("patients", [])

    if not isinstance(patients, list) or not patients:
        return {"status": "error", "message": "需要患者列表 (patients: list[dict])"}

    results = {"RED": [], "YELLOW": [], "GREEN": [], "BLACK": [], "total": len(patients)}

    for p in patients:
        pid = p.get("patient_id", p.get("id", "unknown"))
        resp = int(p.get("resp_rate", p.get("RR", 18)) or 18)
        pulse = int(p.get("pulse", p.get("HR", 80)) or 80)
        mental = p.get("mental", p.get("consciousness", "alert"))
        can_walk = p.get("can_walk", True)

        category = "GREEN"

        # START algorithm: breathing → circulation → mental
        if resp == 0:
            # Check airway repositioning
            category = "BLACK"  # not breathing after airway
        elif resp > 30 or pulse == 0 or pulse < 40 or mental not in ("alert", "清醒", "能执行指令"):
            category = "RED"
        elif resp < 10 or pulse > 120 or not can_walk:
            category = "YELLOW"

        results[category].append({"id": pid, "RR": resp, "HR": pulse, "mental": mental})

    # Priority ranking within RED
    if results["RED"]:
        results["RED"].sort(key=lambda x: (x["RR"] > 30, x["HR"] < 60), reverse=True)

    return {
        "status": "ok",
        "summary": f"START检伤分类完成 — RED:{len(results['RED'])} YELLOW:{len(results['YELLOW'])} GREEN:{len(results['GREEN'])} BLACK:{len(results['BLACK'])}",
        "results": results,
        "protocol": "START (Simple Triage and Rapid Treatment)",
        "recommendations": [
            "RED: 立即抢救/手术 — 优先转运",
            "YELLOW: 延迟处理 — 可等待数小时",
            "GREEN: 轻伤 — 可自行行走, 最晚处理",
            "BLACK: 已死亡或不可救治 — 资源不足时最后处理",
        ],
    }
