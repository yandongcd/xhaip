"""健康素养自适应通信 (B5 HLAC) — 根据患者理解水平调整 agent 输出.

Level 1 (低): 通俗语言, 避免术语 → "换个金属关节, 手术约1.5小时"
Level 3 (中): 标准医学术语 → "全髋关节置换术(THA), 生物型假体"
Level 5 (高): 全文循证 → "AAOS 2022 Rec2, Garden IV, THA优于HA(证据Ⅰ级)"
"""

from __future__ import annotations

import re
from typing import Any

HLAC_LEVEL_NAMES = {1: "基础", 3: "标准", 5: "循证"}


def assess_hlac_level(patient_text: str) -> int:
    """评估患者健康素养等级 (1-5, 基于文本复杂度)."""
    # 简单启发式: 术语密度 + 句子复杂度
    medical_terms = r"肌钙蛋白|INR|D|二聚体|eGFR|CRP|ASA分级|RCRI|Caprini|KDIGO|骨密度|假体|髓内钉|内固定|关节置换"
    term_count = len(re.findall(medical_terms, patient_text))
    total_words = len(patient_text.replace(" ", ""))
    if term_count == 0 and total_words < 100:
        return 1
    if term_count <= 2:
        return 3
    return 5


def _simplify(text: str, level: int) -> str:
    """术语替换表 (Level 1 用通俗语言)."""
    if level >= 3:
        return text

    replacements = [
        ("人工全髋关节置换术", "换一套金属髋关节"),
        ("THA", "换髋关节手术"),
        ("PFNA", "髓内钉钢钉固定"),
        ("依诺肝素", "预防血栓的药(肚皮针)"),
        ("低分子肝素", "防血栓针"),
        ("DVT预防", "防腿部血栓"),
        ("围术期", "手术前后"),
        ("全麻", "全身麻醉(睡着做手术)"),
        ("择期手术", "不着急,安排时间做的手术"),
        ("急诊手术", "马上要做的手术,有生命危险"),
        ("骨密度", "骨头硬度检查"),
        ("内固定", "用钢钉把骨头接起来"),
        ("关节置换", "换关节"),
        ("禁忌症", "不能用的原因"),
        ("抗凝", "防止血液凝固"),
        ("心肌酶谱", "抽血查心脏健康"),
        ("ASA III", "身体状况差(麻醉风险较高)"),
        ("EKG", "心电图(检查心脏跳动)"),
        ("髋部骨折", "大腿根部的骨头断裂"),
        ("股骨颈骨折", "大腿球头下面的骨头断裂"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _expand(text: str, level: int) -> str:
    """循证扩展 (Level 5 加指南引用)."""
    if level < 5:
        return text

    evidence_map = {
        "THA": " (AAOS 2022 Rec2: Garden IV型骨折, T1级推荐)",
        "PFNA": " (CSCO 2020: 转子间骨折金标准, T1级推荐)",
        "低分子肝素": " (ACCP 2021: Caprini评分指导下, T1级推荐)",
        "48h内": " (NICE NG37 §1.1: 入院当天或次日手术, T1级推荐)",
        "择期": " (AAOS 2022: 高风险需MDT会诊后, T1级推荐)",
    }
    for kw, ev in evidence_map.items():
        if kw in text:
            text = text.replace(kw, kw + ev)
    return text


class HLACAdapter:
    """健康素养自适应 — 包装 agent 输出."""

    def __init__(self, level: int = 3):
        self.level = level

    def adapt(self, text: str) -> dict[str, Any]:
        original = text
        text = _simplify(text, self.level)
        text = _expand(text, self.level)

        return {
            "hlac_level": self.level,
            "hlac_level_name": HLAC_LEVEL_NAMES.get(self.level, "标准"),
            "adapted_text": text,
            "original_length": len(original),
            "simplified": self.level < 3,
            "evidence_expanded": self.level >= 5,
        }

    def wrap_agent_output(self, agent_output: dict[str, Any], key: str = "reply") -> dict[str, Any]:
        """包装 agent 字典输出, 附加 HLAC 版本."""
        output = dict(agent_output)
        if key in output:
            adapted = self.adapt(str(output[key]))
            output[key] = adapted["adapted_text"]
            output["hlac"] = adapted
        return output
