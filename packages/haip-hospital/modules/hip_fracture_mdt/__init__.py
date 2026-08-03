"""老年髋部骨折围术期多学科管理智能体 — A2 HipFractureMDT.

全流程: 骨折分型→48h窗口评估→MDT协调→围术期方案→术后随访.
依赖: cardio-risk(心血管) / anesthesia(麻醉) / pain-management(镇痛) / mdt(会诊协议)
"""
from __future__ import annotations

from haip.a2a.mdt_orchestrator import get_mdt_orchestrator
from haip.a2a.mdt_protocol import MDTStatus
from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="hip-fracture-mdt", department="创伤骨科")
_GUIDELINES = [
    "国家卫健委《老年髋部骨折诊疗与管理指南(2022年版)》",
    "NICE NG37 髋部骨折管理 (2023)",
    "AAOS 老年髋部骨折循证临床实践指南 (2022)",
    "CSCO 股骨颈骨折/转子间骨折诊疗指南 (2018/2020)",
    "ACCP 抗栓治疗与血栓预防指南 (2021)",
]
_agent.rule_engine.load_all()

# ── Garden 分型 → 手术方案映射 ──
FRACTURE_SURGERY_MAP = {
    "Garden I": {"type": "股骨颈 不完全/外展嵌插", "surgery": "保守治疗或空心螺钉内固定", "urgency": "择期(72h内)"},
    "Garden II": {"type": "股骨颈 完全无移位", "surgery": "空心螺钉内固定(3枚)", "urgency": "48h内"},
    "Garden III": {"type": "股骨颈 部分移位", "surgery": "半髋关节置换(骨水泥型)", "urgency": "48h内"},
    "Garden IV": {"type": "股骨颈 完全移位", "surgery": "全髋关节置换(THA)", "urgency": "48h内"},
    "31A1": {"type": "转子间 简单两部分(稳定)", "surgery": "DHS滑动髋螺钉或PFNA髓内钉", "urgency": "48h内"},
    "31A2": {"type": "转子间 粉碎性(不稳定)", "surgery": "PFNA髓内钉", "urgency": "48h内"},
    "31A3": {"type": "转子间 反斜型(不稳定)", "surgery": "PFNA髓内钉", "urgency": "48h内"},
}

# T2 8因素层次决策 (from orthopedic-surgery rules)
T2_FACTORS = [
    ("心脏", ["心功能不全", "不稳定心绞痛", "严重心律失常", "EF<40%"]),
    ("肺", ["严重COPD", "低氧血症", "SpO2<90%"]),
    ("脑", ["近期卒中<3月", "严重颈动脉狭窄"]),
    ("抗凝", ["双抗", "华法林", "DOAC", "INR>1.5"]),
    ("贫血", ["Hb<80"]),
    ("肾", ["eGFR<30", "透析"]),
    ("感染", ["WBC>12", "PCT>0.5", "活动性感染"]),
    ("血糖", ["随机血糖>16.7", "HbA1c>10%"]),
]


def fracture_classify(**kwargs) -> dict:
    """骨折分型诊断 + 手术方案关联."""
    pid = kwargs.get("patient_id", "")
    xray = kwargs.get("xray_findings", "")
    p = _agent.get_patient(pid) or {}

    dx = str(p.get("diagnosis", "")).lower()
    xray_lower = xray.lower() if xray else ""

    classification = None
    for key, info in FRACTURE_SURGERY_MAP.items():
        key_lower = key.lower()
        if key_lower in dx or key_lower in xray_lower or key_lower.replace(" ", "") in dx:
            classification = {"name": key, **info}
            break

    if not classification:
        classification = {"name": "待分型", "type": "需X线明确", "surgery": "待骨科评估", "urgency": "尽快"}

    return _agent.clinical_result(
        summary=f"骨折分型 — {classification['name']}: {classification['type']}",
        patient=p,
        findings=[{"分型": classification["name"], "类型": classification["type"],
                   "推荐术式": classification["surgery"], "手术紧迫度": classification["urgency"]}],
        recommendations=[
            "老年髋部骨折 → 力争48h内手术 (国家卫健委2022指南)",
            "入院即启动绿色通道: ECG/胸片/心超/凝血/血常规/肝肾功/血糖",
            "24h内完成心内科+麻醉科+老年科会诊",
        ],
    )


def surgical_timing(**kwargs) -> dict:
    """48h手术窗口评估 — T2 8因素层次决策."""
    pid = kwargs.get("patient_id", "")
    p = _agent.get_patient(pid) or {}

    dx = str(p.get("diagnosis", "")).lower()
    labs = p.get("lab_results", {}) or {}
    age = p.get("age", 0)

    delays = []
    for category, keywords in T2_FACTORS:
        matched = [kw for kw in keywords if kw.lower() in dx or
                   (isinstance(labs, dict) and any(kw.lower() in str(v).lower() for k, v in labs.items()))]
        if matched:
            delays.append({"类别": category, "匹配项": matched, "处理": f"需{category}相关科室会诊+优化"})

    can_48h = len(delays) == 0
    urgency = "48h内可手术" if can_48h else f"需术前优化({len(delays)}项)"
    if any(d["类别"] in ("心脏", "脑", "抗凝") for d in delays):
        urgency = "🟠 高危因素需MDT评估手术时机"

    rules = _agent.search_rules("手术时机") or []
    return _agent.clinical_result(
        summary=f"手术时机评估 — {urgency}",
        patient=p,
        findings=[{"48h可行性": "是" if can_48h else "否", "延迟因素": delays,
                   "因素数量": len(delays), "年龄": age}],
        rules=rules,
        recommendations=[
            "无高危因素 → 直接进入手术流程 (48h内)" if can_48h else "存在高危因素 → MDT评估后决定手术时机",
            "卧床>48h → DVT/PE/肺炎/压疮风险显著升高",
        ],
    )


def mdt_coordinate(**kwargs) -> dict:
    """MDT多学科协调 — 并行调用专科Agent."""
    pid = kwargs.get("patient_id", "")
    question = kwargs.get("question", "老年髋部骨折围术期评估")

    participants = ["cardio-risk", "anesthesia", "nurse-general"]
    orchestrator = get_mdt_orchestrator()

    try:
        session = orchestrator.run_session(
            patient_id=pid,
            question=question,
            participants=participants,
            timeout=180,
        )
    except Exception as exc:
        # Graceful fallback without MDT: report the failure truthfully
        return {
            "status": "error",
            "error": f"MDT协调失败: {exc}",
            "summary": "MDT协调未完成（降级模式，请参考各专科独立评估结果）",
            "participants": participants,
            "mode": "offline_fallback",
            "recommendations": [
                "心内科: 请参考 cardio-risk 评估",
                "麻醉科: 请参考 anesthesia 评估",
                "护理: 请参考 nurse-general 评估",
                "所有评估结果须经MDT首席组长人工审核确认",
            ],
        }

    return {
        "status": "ok",
        "session_id": session.session_id,
        "summary": session.consensus or "各专科意见已汇总",
        "participants": session.participants,
        "opinions": [{"agent": o.agent_name, "recommendation": o.recommendation,
                       "confidence": o.confidence} for o in session.opinions],
        "divergences": len(session.divergences),
        "deadlocked": session.status == MDTStatus.DEADLOCKED,
        "needs_human_review": len(session.divergences) > 0,
    }


def perioperative_plan(**kwargs) -> dict:
    """围术期综合方案 — 手术+麻醉+护理+康复四维."""
    pid = kwargs.get("patient_id", "")
    fracture_type = kwargs.get("fracture_type", "")
    asa_level = int(kwargs.get("asa_level", 2) or 2)
    p = _agent.get_patient(pid) or {}

    surgery_info = FRACTURE_SURGERY_MAP.get(fracture_type, FRACTURE_SURGERY_MAP.get("31A2", {"surgery": "PFNA髓内钉"}))

    plan = {
        "手术方案": [
            f"推荐术式: {surgery_info.get('surgery', '待评估')}",
            f"手术时机: {surgery_info.get('urgency', '48h内')}",
            "术前备血: 悬浮红细胞 2U + 血浆 400mL (老年髋部骨折常规)",
            "预防性抗生素: 头孢唑林 2g IV (切皮前30-60min)",
        ],
        "麻醉方案": [
            "ASA {} → {}".format(asa_level, "椎管内麻醉(腰麻)优先" if asa_level <= 3 else "全身麻醉+有创监测"),
            "术后镇痛: 多模式镇痛 (神经阻滞+NASIDs+必要时阿片)",
            "有抗凝药 → 按ASRA指南调整停药/桥接",
        ],
        "护理方案": [
            "术前: Braden压疮评分 + Morse跌倒评分 + Caprini VTE评分",
            "术后24h: 被动关节活动 + 良肢位摆放 + 踝泵运动",
            "术后48h: 床旁坐起 + 下肢肌力训练 + 助行器站立",
            "防跌倒: 高危标识 + 床栏 + 防滑鞋 + 家属陪护",
        ],
        "康复方案": [
            "术后24h: 被动关节活动度训练 15min×2次/天",
            "术后48-72h: 助行器辅助站立+步行训练 30min/天",
            "术后1周: Harris评分基线 + FIM功能独立性评分",
            "出院前: 居家康复指导+防跌倒教育+骨质疏松管理",
        ],
    }

    vte_rules = _agent.search_rules("VTE") or []
    return _agent.clinical_result(
        summary=f"围术期方案 — {fracture_type or '髋部骨折'} ASA{asa_level}",
        patient=p,
        findings=[{k: v for k, v in plan.items()}],
        rules=vte_rules,
        recommendations=[
            "48h内完成手术 → 降低死亡率+并发症率 (国家卫健委2022指南 ⅠA级推荐)",
            "术后24h启动VTE药物预防(依诺肝素40mg qd) — 出血风险可接受时",
            "术后即开始康复训练 — 早期活动是降低并发症的关键",
            "所有方案须经MDT首席组长审核确认后方可执行",
        ],
    )


def followup_schedule(**kwargs) -> dict:
    """术后随访计划."""
    pid = kwargs.get("patient_id", "")
    surgery_date = kwargs.get("surgery_date", "")

    schedule = [
        {"节点": "术后1周", "项目": "伤口评估 + 拆线 + VTE筛查 + Harris评分基线", "方式": "骨科门诊"},
        {"节点": "术后1月", "项目": "Harris评分 + X线复查(骨折愈合) + VTE复查 + 功能评估", "方式": "骨科门诊"},
        {"节点": "术后3月", "项目": "Harris评分 + X线 + 骨密度(DXA) + 骨质疏松治疗启动", "方式": "骨科门诊+老年科"},
        {"节点": "术后6月", "项目": "Harris评分 + 功能独立性(FIM) + 生活质量(SF-36)", "方式": "骨科门诊"},
        {"节点": "术后12月", "项目": "年度综合评估 + Harris评分 + 对侧髋部骨折风险评估", "方式": "骨科门诊+老年科"},
    ]

    osteoporosis = [
        "所有老年髋部骨折患者 → 术后常规启动骨质疏松治疗(钙剂+VitD+双膦酸盐)",
        "DXA骨密度: 术后3月复查 + 每年随访",
        "预防跌倒: 居家环境评估+步态训练+视力检查",
    ]

    return {
        "status": "ok",
        "summary": "术后12月随访计划已生成",
        "schedule": schedule,
        "osteoporosis_management": osteoporosis,
        "recommendations": [
            "首次随访: 术后1周拆线+评估",
            "关键节点: 术后3月启动骨质疏松系统治疗",
            "长期目标: 恢复独立行走 + 预防对侧骨折",
            "所有随访须录入Harris评分追踪系统",
        ],
    }
