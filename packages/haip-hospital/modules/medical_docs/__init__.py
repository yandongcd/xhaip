"""住院医病历书写辅助 — 首次病程记录 / 出院小结 结构化草稿.

原则:
  - 草稿仅为骨架整理, 所有临床判断字段来自医生输入或病历数据
  - 每份草稿自动创建签核单 (pending), 医生签核前不视为病历
  - 患者数据来自数字病人库 (haip.patients.PATIENTS_FILE)
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from haip.togaf.knowledge_agent import KnowledgeAgent

_agent = KnowledgeAgent(agent_name="medical-docs", department="全院")
_GUIDELINES = [
    "电子病历应用管理规范 (2023)",
    "医疗机构病历管理规定 (2013)",
    "国家卫健委 病历书写基本规范",
    "ICD-10 疾病分类与代码",
]
_agent.rule_engine.load_all()

_DISCLAIMER = "本文书为 AI 辅助生成草稿, 须经医生审核修改并签核后方可归入病历。"

_INCOMPLETE_MARKERS = ("待补充", "待明确", "待完善", "请医生")


def _completeness(sections: dict) -> tuple[float, list[str]]:
    """统计待补充章节, 返回 (完整度, 待补充章节名列表)。"""
    incomplete = [k for k, v in sections.items()
                  if any(m in str(v) for m in _INCOMPLETE_MARKERS)]
    total = len(sections)
    ratio = round((total - len(incomplete)) / total, 2) if total else 0.0
    return ratio, incomplete


def _load_patient(patient_id: str) -> dict:
    try:
        from haip.patients import load_all_patients
        for p in load_all_patients():
            if p.get("patient_id") == patient_id:
                return p
        return {}
    except Exception:  # noqa: BLE001 — 数据不可用时走占位
        import logging
        logging.getLogger(__name__).warning("_load_patient 失败: patient_id=%s", patient_id, exc_info=True)
    return {}


def _patient_header(p: dict, patient_id: str) -> str:
    if not p:
        return f"患者 {patient_id} (信息待补充)"
    return (f"{p.get('name', '?')} , {p.get('gender', '?')}, {p.get('age', '?')} 岁, "
            f"{p.get('department', '')}, 病历号 {patient_id}")


def _create_signoff(tool: str, patient_id: str, content: str) -> str:
    try:
        from haip.signoff import get_signoff_manager
        return get_signoff_manager().create(
            agent="medical-docs", tool=tool, patient_id=patient_id,
            output_summary=content, risk_level="medium")
    except Exception:  # noqa: BLE001
        return ""


def draft_progress_note(patient_id: str = "", chief_complaint: str = "",
                        present_illness: str = "", exam_findings: str = "",
                        past_history: str = "", aux_exams: str = "",
                        diagnosis: str = "", plan: str = "",
                        **kwargs: Any) -> dict:
    """首次病程记录草稿。"""
    p = _load_patient(patient_id)
    warnings: list[str] = []
    if not p:
        warnings.append(f"患者 {patient_id} 未在数字病人库中找到, 基本信息为占位")

    dx = diagnosis or p.get("diagnosis", "") or "待明确 (请医生填写)"
    labs = p.get("lab_results") or {}
    aux = aux_exams or (
        "; ".join(f"{k} {v}" for k, v in list(labs.items())[:8]) if labs else "待完善")

    sections = {
        "患者信息": _patient_header(p, patient_id),
        "记录时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "主诉": chief_complaint or "待补充",
        "现病史": present_illness or "待补充",
        "既往史": past_history or p.get("conditions") and "、".join(p.get("conditions", [])) or "待补充",
        "体格检查": exam_findings or "待补充",
        "辅助检查": aux,
        "初步诊断": dx,
        "诊疗计划": plan or "1. 完善相关检查; 2. 对症支持治疗; 3. 请上级医师查房指导 (请医生修订)",
    }
    content = "【首次病程记录】\n" + "\n".join(f"{k}: {v}" for k, v in sections.items())
    ratio, incomplete = _completeness(sections)
    if incomplete:
        warnings.append(f"{len(incomplete)} 个章节待补充 ({'、'.join(incomplete)}), 签核前必须完成")
    sid = _create_signoff("draft_progress_note", patient_id, content)
    return {
        "status": "ok", "note_type": "首次病程记录",
        "sections": sections, "content": content,
        "completeness": ratio,
        "signoff_id": sid, "warnings": warnings,
        "disclaimer": _DISCLAIMER,
    }


def draft_discharge_summary(patient_id: str = "", course: str = "",
                            discharge_meds: list | None = None,
                            followup: str = "", admission_summary: str = "",
                            discharge_status: str = "", discharge_diagnosis: str = "",
                            **kwargs: Any) -> dict:
    """出院小结草稿。"""
    p = _load_patient(patient_id)
    warnings: list[str] = []
    if not p:
        warnings.append(f"患者 {patient_id} 未在数字病人库中找到, 基本信息为占位")
    meds = discharge_meds or []
    dx = discharge_diagnosis or p.get("diagnosis", "") or "待明确 (请医生填写)"

    sections = {
        "患者信息": _patient_header(p, patient_id),
        "出院日期": datetime.now().strftime("%Y-%m-%d"),
        "入院情况": admission_summary or (p.get("scenario") or "待补充"),
        "诊疗经过": course or "待补充",
        "出院情况": discharge_status or "一般情况可, 生命体征平稳 (请医生核实修订)",
        "出院诊断": dx,
        "出院医嘱": "\n".join(f"  {i+1}. {m}" for i, m in enumerate(meds)) if meds else "待补充",
        "随访计划": followup or "待补充",
    }
    content = "【出院小结】\n" + "\n".join(f"{k}: {v}" for k, v in sections.items())
    ratio, incomplete = _completeness(sections)
    if incomplete:
        warnings.append(f"{len(incomplete)} 个章节待补充 ({'、'.join(incomplete)}), 签核前必须完成")
    sid = _create_signoff("draft_discharge_summary", patient_id, content)
    return {
        "status": "ok", "note_type": "出院小结",
        "sections": sections, "content": content,
        "completeness": ratio,
        "signoff_id": sid, "warnings": warnings,
        "disclaimer": _DISCLAIMER,
    }
