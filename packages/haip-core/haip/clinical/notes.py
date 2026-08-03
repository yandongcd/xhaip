"""实时病历生成 — FactsR 方法移植 (Corti 2025, clinician-in-the-loop).

核心思想: 就诊中实时提取"事实"(facts), 递归生成结构化病历 — 比事后一键总结更安全.

实现 (轻量版, 无 LLM 依赖):
  1. extract_facts: 从患者数据/增量事件提取结构化事实 (结构化规则, mock 可用)
  2. generate_note: 事实 → 分节病历 (主诉/现病史/既往史/检验/评估/计划), 递归补齐缺失节
  3. llm 模式: 可选 LLM 润色 (provider 注入)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

SECTION_ORDER = ["主诉", "现病史", "既往史", "检验", "评估", "计划"]


@dataclass
class Fact:
    """一条已提取事实."""

    category: str          # demographic / complaint / history / lab / exam / assessment / plan
    field: str
    value: Any
    source: str = ""       # 来源 (患者数据 / 事件 / 工具输出)
    verified: bool = True  # 是否经确认 (clinician-in-the-loop)

    def render(self) -> str:
        return f"{self.field}: {self.value}"


def extract_facts(patient: dict[str, Any] | None = None,
                  events: list[dict[str, Any]] | None = None) -> list[Fact]:
    """从患者数据与增量事件提取结构化事实 (规则式, 确定性)."""
    patient = patient or {}
    events = events or []
    facts: list[Fact] = []

    if patient.get("age") is not None:
        facts.append(Fact("demographic", "年龄", f"{patient['age']}岁", "patient"))
    if patient.get("gender"):
        facts.append(Fact("demographic", "性别", patient["gender"], "patient"))
    if patient.get("diagnosis"):
        facts.append(Fact("complaint", "诊断", patient["diagnosis"], "patient"))
    if patient.get("chief_complaint"):
        facts.append(Fact("complaint", "主诉", patient["chief_complaint"], "patient"))
    if patient.get("past_history"):
        facts.append(Fact("history", "既往史", patient["past_history"], "patient"))

    labs = patient.get("lab_results") or {}
    for k, v in labs.items():
        try:
            vf = float(v)
            if vf != 0 or k in ("血红蛋白测定", "白细胞计数", "C反应蛋白", "葡萄糖"):
                facts.append(Fact("lab", k, v, "lab_results"))
        except (TypeError, ValueError):
            facts.append(Fact("lab", k, v, "lab_results"))

    for ev in events:
        etype = ev.get("type", "")
        desc = ev.get("description", "")
        if not desc:
            continue
        cat = {"symptom": "complaint", "exam": "exam", "assessment": "assessment",
               "plan": "plan", "treatment": "plan"}.get(etype, "complaint")
        facts.append(Fact(cat, etype, desc, "event", verified=ev.get("verified", False)))

    return facts


def _lab_abnormal(facts: list[Fact]) -> list[str]:
    """标记异常检验 (简单阈值)."""
    ranges = {
        "血红蛋白测定": (110, 160), "白细胞计数": (3.5, 9.5), "血小板计数": (100, 300),
        "葡萄糖": (3.9, 6.1), "C反应蛋白": (0, 6.0), "肌钙蛋白I": (0, 0.04),
        "肾小球滤过率": (60, 200), "肌酐": (0, 104),
    }
    out = []
    for f in facts:
        if f.category != "lab":
            continue
        r = ranges.get(f.field)
        if not r:
            continue
        try:
            v = float(f.value)
            if v < r[0] or v > r[1]:
                direction = "偏低" if v < r[0] else "偏高"
                out.append(f"{f.field}={v} ({direction})")
        except (TypeError, ValueError):
            continue
    return out


def generate_note(
    patient: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
    tool_results: dict[str, Any] | None = None,
    sections: list[str] | None = None,
    include_disclaimer: bool = True,
) -> dict[str, Any]:
    """递归生成结构化病历.

    递归语义 (FactsR): 草稿 → 检查缺失节 → 从 facts 补齐 → 终稿.
    返回 {note, sections, missing, facts_count}.
    """
    patient = patient or {}
    events = events or []
    tool_results = tool_results or {}
    facts = extract_facts(patient, events)

    # 工具结果作为"计划/评估"事实
    for tool_name, result in tool_results.items():
        if isinstance(result, dict):
            urgency = result.get("urgency")
            if urgency:
                facts.append(Fact("plan", "手术时机", urgency, f"tool:{tool_name}"))
            rec = result.get("recommendation") or result.get("recommended_surgery")
            if rec:
                facts.append(Fact("plan", tool_name, rec, f"tool:{tool_name}"))

    sections = sections or SECTION_ORDER
    missing: list[str] = []
    note_sections: dict[str, str] = {}

    for sec in sections:
        content = _render_section(sec, facts, tool_results)
        if content:
            note_sections[sec] = content
        else:
            missing.append(sec)

    # 递归补齐: 缺失节再次从 facts 尝试 (第二轮)
    if missing:
        for sec in list(missing):
            content = _render_section(sec, facts, tool_results, strict=False)
            if content:
                note_sections[sec] = content
                missing.remove(sec)

    note = "\n\n".join(f"**【{sec}】**\n{note_sections[sec]}" for sec in sections if sec in note_sections)
    if include_disclaimer:
        note += ("\n\n---\n> 本病历由 AI 辅助生成 (事实提取+结构化), 需经临床医师审核确认。"
                 "不构成独立医疗决策。")

    return {
        "note": note,
        "sections": {sec: note_sections.get(sec, "") for sec in sections},
        "missing_sections": missing,
        "facts_count": len(facts),
        "facts": [f.render() for f in facts[:20]],
    }


def _render_section(sec: str, facts: list[Fact], tool_results: dict[str, Any],
                    strict: bool = True) -> str:
    """渲染单节内容 (规则模板)."""
    lines: list[str] = []
    if sec == "主诉":
        for f in facts:
            if f.category == "complaint":
                lines.append(f.render())
    elif sec == "现病史":
        for f in facts:
            if f.category in ("complaint", "exam") and f.source != "patient":
                lines.append(f.render())
    elif sec == "既往史":
        for f in facts:
            if f.category == "history":
                lines.append(f.render())
        if not lines and patient_field(facts, "既往史"):
            lines.append(f"既往史: {patient_field(facts, '既往史')}")
    elif sec == "检验":
        abnormal = _lab_abnormal(facts)
        if abnormal:
            lines.append("异常指标: " + "；".join(abnormal[:8]))
        for f in facts:
            if f.category == "lab" and f.field not in _all_lab_names(facts):
                lines.append(f.render())
        if strict and not abnormal:
            return ""
    elif sec == "评估":
        diag = patient_field(facts, "诊断")
        if diag:
            lines.append(f"初步诊断: {diag}")
        for f in facts:
            if f.category == "assessment":
                lines.append(f.render())
        if not strict and not lines:
            lines.append("待完善评估")
    elif sec == "计划":
        for f in facts:
            if f.category == "plan":
                lines.append(f.render())
        if not strict and not lines:
            lines.append("待制定诊疗计划")
    return "\n".join(lines)


def patient_field(facts: list[Fact], field_name: str) -> Any:
    for f in facts:
        if f.field == field_name:
            return f.value
    return None


def _all_lab_names(facts: list[Fact]) -> set[str]:
    return {f.field for f in facts if f.category == "lab"}


def note_to_json(note: dict[str, Any]) -> str:
    return json.dumps(note, ensure_ascii=False, indent=2, default=str)
