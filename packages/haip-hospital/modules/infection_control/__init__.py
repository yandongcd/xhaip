"""医院感染监测智能体 — MDRO监测/暴发检测/SSI监测/集束化依从性/环境卫生学."""
from __future__ import annotations

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="infection-control", department="医院感染管理科")
_GUIDELINES = [
    "WS/T 312-2009 医院感染监测规范",
    "SHEA/IDSA/APIC 2022 急症医院感染预防策略",
    "CDC/NHSN 手术部位感染监测定义 2024",
    "中国医院协会《医院感染预防与控制评价规范》",
    "WHO《多重耐药菌全球防控指南》",
]
_agent.rule_engine.load_all()

_MDRO_TARGETS = ["MRSA", "VRE", "CRE", "CRAB", "CRPA", "MDR-TB", "ESBL"]


def mdro_surveillance(**kwargs) -> dict:
    """多重耐药菌主动监测."""
    time_range = kwargs.get("time_range", "7d")
    department = kwargs.get("department", "")

    # In production, this would query LIS via MCP
    findings = {
        "监测周期": time_range,
        "目标科室": department or "全院",
        "监测菌种": _MDRO_TARGETS,
        "检测结果": "需接入LIS微生物培养+药敏数据",
    }
    alerts = ["MDRO主动监测已启动 — 需接入LIS实时数据源完成自动化筛查"]

    guides = _agent.search_guidelines("多重耐药菌监测") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"MDRO监测 — {time_range} / {department or '全院'}",
        guidelines=guides,
        alerts=alerts,
        findings=[findings],
        recommendations=[
            "每日从LIS同步微生物培养+药敏结果",
            "自动标记MRSA/VRE/CRE/CRAB/CRPA等目标MDRO",
            "按科室/时间/菌种三维统计并生成趋势报告",
        ],
    )


def outbreak_detection(**kwargs) -> dict:
    """医院感染暴发检测."""
    cases = kwargs.get("cases", [])
    time_window = kwargs.get("time_window", 7)

    findings = {
        "时间窗口": f"{time_window}天",
        "上报病例数": len(cases) if isinstance(cases, list) else 0,
    }

    alerts = []
    if isinstance(cases, list) and len(cases) >= 3:
        alerts.append(f"⚡ 橙色预警: 同病区{time_window}天内≥3例MDRO — 高度疑似院感暴发")
        alerts.append("建议: 立即启动院感暴发调查流程 (隔离+追踪+上报)")

    guides = _agent.search_guidelines("院感暴发") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"院感暴发检测 — {time_window}天窗口",
        guidelines=guides,
        alerts=alerts,
        findings=[findings],
        recommendations=[
            "≥3例同源MDRO → 橙色预警 → 启动调查",
            "≥5例同源MDRO → 红色预警 → 上报医务处+CDC",
            "所有暴发事件需完成24h初步调查报告+72h完整调查报告",
        ],
    )


def ssi_monitor(**kwargs) -> dict:
    """手术部位感染(SSI)监测."""
    surgery_records = kwargs.get("surgery_records", [])

    findings = {
        "监测标准": "CDC/NHSN 2024 定义",
        "手术记录数": len(surgery_records) if isinstance(surgery_records, list) else 0,
        "切口分级": "I(清洁)/II(清洁-污染)/III(污染)/IV(污秽)",
        "监测窗口": "术后30天(无植入物) / 术后90天(有植入物)",
    }
    alerts = ["SSI监测需对接手术麻醉系统+术后再入院数据"]

    guides = _agent.search_guidelines("手术部位感染") or _GUIDELINES
    return _agent.clinical_result(
        summary="SSI监测 — CDC/NHSN标准",
        guidelines=guides,
        alerts=alerts,
        findings=[findings],
        recommendations=[
            "自动采集手术记录(切口等级/NNIS评分/手术时长/预防性抗生素)",
            "术后30天/90天追踪再入院及切口分泌物培养结果",
            "计算SSI发生率并与NHSN基准对比",
        ],
    )


def hai_bundle_compliance(**kwargs) -> dict:
    """院感集束化措施依从性."""
    department = kwargs.get("department", "")
    date = kwargs.get("date", "")

    bundles = {
        "CLABSI": "中心静脉导管相关血流感染预防集束(5项): 手卫生/最大无菌屏障/氯己定消毒/股静脉避免/每日评估拔管",
        "CAUTI": "导尿管相关尿路感染预防集束(4项): 严格指征/无菌操作/固定防牵拉/每日评估拔管",
        "VAP": "呼吸机相关肺炎预防集束(5项): 床头抬高30-45°/每日镇静中断/拔管评估/口腔护理/气囊压力",
    }

    findings = {
        "目标科室": department or "全院",
        "评估日期": date or "今日",
        "集束清单": list(bundles.keys()),
        "依从性数据": "需接入护理记录+ICU监测数据",
    }

    guides = _agent.search_guidelines("集束化措施") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"院感集束化依从性 — {department or '全院'}",
        guidelines=guides,
        findings=[findings],
        recommendations=[f"{k}: {v}" for k, v in bundles.items()],
    )


def environmental_surveillance(**kwargs) -> dict:
    """环境卫生学监测."""
    location = kwargs.get("location", "")
    sample_type = kwargs.get("sample_type", "")

    findings = {
        "监测地点": location or "全院重点部门",
        "监测类型": sample_type or "空气+物表+内镜",
        "标准依据": "GB 15982-2012 医院消毒卫生标准 / WS/T 367-2012 医疗机构消毒技术规范",
    }

    guides = _agent.search_guidelines("环境卫生学") or _GUIDELINES
    return _agent.clinical_result(
        summary=f"环境卫生学监测 — {location or '重点部门'}",
        guidelines=guides,
        findings=[findings],
        recommendations=[
            "手术室: 空气沉降菌 ≤4 CFU/皿(30min) / 物表 ≤5 CFU/cm²",
            "ICU/NICU: 每月空气培养+物表采样",
            "内镜: 每条内镜洗消后ATP检测+每月微生物培养",
            "血液透析室: 透析用水细菌<100 CFU/mL / 内毒素<0.25 EU/mL",
        ],
    )
