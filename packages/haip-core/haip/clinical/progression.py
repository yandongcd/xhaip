"""疾病转归模型 (MED-1) — 指南驱动的概率化临床通路引擎.

虚拟病人的"物理引擎": 患者状态 + 治疗方案 → 概率化转归.
基于 AAOS/NICE 等指南的关键推荐 (48h 手术窗口 / 压疮风险 / 死亡率差异).
种子可固定 → CI 可回归测试.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PatientState(str, Enum):
    STABLE = "stable"           # 病情稳定, 可择期手术
    DETERIORATING = "deteriorating"  # 病情恶化 (延迟治疗)
    CRITICAL = "critical"       # 危急 (需急诊干预)
    RECOVERING = "recovering"   # 术后恢复中
    RECOVERED = "recovered"     # 康复
    DECEASED = "deceased"       # 死亡


# ── 指南来源转归规则 (Provenance: guideline YAML → rule) ──
# 基于 AAOS 2022 / NICE NG37 / 卫健委 2022 的关键转归差异

@dataclass
class ProgressionRule:
    """一条转归规则: 条件 → 概率化结果."""
    rule_id: str
    condition_desc: str            # 触发条件
    target_state: PatientState
    probability: float             # 0.0-1.0
    guideline_ref: str = ""        # 溯源: guideline YAML name
    key_section: str = ""          # 溯源: guideline key_section id


# ── 髋部骨折转归规则 (基于 AAOS Rec1: 48h 手术窗口) ──

ORTHO_PROGRESSION_RULES = [
    # ── 急诊手术路径 ──
    ProgressionRule("ortho-p1", "急诊手术在48h内完成",
                    PatientState.RECOVERING, 0.90, "guideline-aaos-2022", "Rec1"),
    ProgressionRule("ortho-p2", "急诊手术在48h内完成 → 并发症",
                    PatientState.DETERIORATING, 0.08, "guideline-aaos-2022", "Rec1"),
    ProgressionRule("ortho-p3", "急诊手术48h内 → 死亡",
                    PatientState.DECEASED, 0.02, "guideline-aaos-2022", "Rec1"),

    # ── 延迟手术路径 ──
    ProgressionRule("ortho-d1", "手术延迟 >48h",
                    PatientState.DETERIORATING, 0.40, "guideline-aaos-2022", "Rec1"),
    ProgressionRule("ortho-d2", "延迟手术 → 压疮",
                    PatientState.DETERIORATING, 0.20, "guideline-aaos-2022", "Rec1"),
    ProgressionRule("ortho-d3", "延迟手术 >48h → 死亡",
                    PatientState.DECEASED, 0.05, "guideline-nice-ng37", "§1.1"),

    # ── 保守治疗路径 ──
    ProgressionRule("ortho-c1", "保守治疗 (无手术)",
                    PatientState.DETERIORATING, 0.60, "guideline-aaos-2022", "Rec2"),
    ProgressionRule("ortho-c2", "保守治疗 → 康复",
                    PatientState.RECOVERING, 0.25, "guideline-aaos-2022", "Rec2"),
    ProgressionRule("ortho-c3", "保守治疗 → 死亡",
                    PatientState.DECEASED, 0.15, "guideline-aaos-2022", "Rec2"),

    # ── 手术后康复路径 ──
    ProgressionRule("ortho-r1", "术后 1 周 → 完全康复",
                    PatientState.RECOVERED, 0.70, "guideline-aaa-2022", "Rec5"),
    ProgressionRule("ortho-r2", "术后 1 周 → 继续恢复",
                    PatientState.RECOVERING, 0.25, "guideline-aaa-2022", "Rec5"),
    ProgressionRule("ortho-r3", "术后并发症 → 恶化",
                    PatientState.DETERIORATING, 0.05, "guideline-aaa-2022", "Rec5"),
]


class ProgressionEngine:
    """转归引擎: 患者 + 治疗 → 概率化下一状态."""

    def __init__(self, rules: list[ProgressionRule] | None = None, seed: int | None = 42):
        self.rules = rules or ORTHO_PROGRESSION_RULES
        self.rng = random.Random(seed)

    def select_rule(self, condition: str) -> list[ProgressionRule]:
        """匹配触发条件的规则集."""
        return [r for r in self.rules if r.condition_desc in condition or condition in r.condition_desc]

    def next_state(self, current: PatientState, condition: str) -> tuple[PatientState, ProgressionRule | None]:
        """根据当前状态 + 触发条件 → 概率化下一状态.

        Returns (next_state, applied_rule).
        """
        matched = self.select_rule(condition)
        if not matched and current == PatientState.RECOVERING:
            # 默认: 恢复 → 康复 (0.8) / 继续恢复 (0.2)
            if self.rng.random() < 0.8:
                return (PatientState.RECOVERED, None)
            return (PatientState.RECOVERING, None)
        if not matched:
            return (current, None)

        total_p = sum(r.probability for r in matched)
        if total_p >= 1.0:
            # 归一化 / 选择最高概率
            matched.sort(key=lambda r: -r.probability)
            roll = self.rng.random()
            cumulative = 0.0
            for r in matched:
                cumulative += r.probability
                if roll <= cumulative:
                    return (r.target_state, r)
            return (PatientState.STABLE, None)

        # total_p < 1.0: 剩余概率 = 保持当前状态
        roll = self.rng.random()
        cumulative = 0.0
        for r in matched:
            cumulative += r.probability
            if roll <= cumulative:
                return (r.target_state, r)
        return (current, None)

    def state_display(self, state: PatientState) -> str:
        display = {
            PatientState.STABLE: "病情稳定",
            PatientState.DETERIORATING: "病情恶化",
            PatientState.CRITICAL: "危急",
            PatientState.RECOVERING: "术后恢复中",
            PatientState.RECOVERED: "已康复",
            PatientState.DECEASED: "死亡",
        }
        return display.get(state, state.value)

    def outcome_summary(self, patient_id: str, state: PatientState, rule: ProgressionRule | None,
                        day: int, agent_action: str) -> dict[str, Any]:
        return {
            "patient_id": patient_id,
            "day": day,
            "state": state.value,
            "state_cn": self.state_display(state),
            "agent_action": agent_action,
            "trigger_condition": rule.condition_desc if rule else "",
            "guideline_ref": rule.guideline_ref if rule else "",
            "key_section": rule.key_section if rule else "",
        }
