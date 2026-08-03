"""记忆注入 (层2) — AgentLoop 推理前检索多源上下文注入 prompt.

多源: 案例库(向量) + KG(结构化) + A2A调用历史(最近).
MemGPT 式机制, 但 xhaip 的多源检索更结构化可溯源.
"""

from __future__ import annotations

from typing import Any


def _extract_keywords(query: str) -> list[str]:
    """从 query 提取诊断/症状关键词."""
    import re
    # 匹配常见诊断词 (中文) + 英文疾病词
    cn_dx = re.findall(r"[\u4e00-\u9fff]{2,10}(?:骨折|梗死|感染|衰竭|疾病|综合征|癌|瘤)", query)
    en_dx = re.findall(r"\b(?:fracture|infarction|stroke|failure|infection|disease|hip|femoral)\w*", query, re.IGNORECASE)
    return (cn_dx + en_dx)[:6]


def retrieve_cases(query: str, agent: str, k: int = 3) -> list[dict[str, Any]]:
    """从进化案例库检索相似案例."""
    try:
        from haip.evolution.memory_base import get_evolution_memory
        memory = get_evolution_memory()
        return memory.search_cases(agent, query, k=k)
    except Exception:
        return []


def retrieve_kg(query: str, k: int = 3) -> dict[str, Any]:
    """从 KG 检索相关指南/规则."""
    try:
        from haip.kg import by_diagnosis
        kw = _extract_keywords(query)
        if not kw:
            return {}
        result = by_diagnosis(kw[0])
        return {
            "guidelines": result.get("guidelines", [])[:k],
            "rules": result.get("rules", [])[:k],
        }
    except Exception:
        return {}


def retrieve_history(agent: str, tool: str = "", k: int = 5) -> list[dict[str, Any]]:
    """从 A2A 调用历史检索最近同类调用."""
    try:
        from haip.a2a import get_history
        history = get_history(limit=50)
        matched = [h for h in history if h.get("agent") == agent]
        if tool:
            matched = [h for h in matched if h.get("tool") == tool]
        return matched[-k:]
    except Exception:
        return []


def build_memory_context(query: str, agent: str, k_cases: int = 3,
                         k_kg: int = 2, k_history: int = 3) -> str:
    """构建注入 prompt 的上下文文本."""
    parts: list[str] = []

    # 案例库
    cases = retrieve_cases(query, agent, k_cases)
    if cases:
        parts.append("[相关历史案例]")
        for c in cases[:k_cases]:
            gold_urgency = (c.get("gold") or {}).get("urgency", "")
            answer = c.get("answer") or {}
            parts.append(
                f"- {c.get('question', '')[:60]} → "
                f"{answer.get('urgency', answer.get('recommended_surgery', ''))}"
                + (f" (金标准: {gold_urgency})" if gold_urgency else "")
            )

    # KG
    kg = retrieve_kg(query, k_kg)
    if kg and (kg.get("guidelines") or kg.get("rules")):
        parts.append("[相关指南]")
        for g in kg.get("guidelines", [])[:k_kg]:
            parts.append(f"- {g.get('name', '')[:50]} (trust: {g.get('trust_level', '')})")
        for r in kg.get("rules", [])[:k_kg]:
            parts.append(f"- 规则: {str(r.get('conclusion', ''))[:50]}")

    # 调用历史
    history = retrieve_history(agent, k=k_history)
    if history:
        parts.append("[近期同类决策]")
        for h in history[-k_history:]:
            parts.append(f"- {h.get('tool', '')}: {h.get('status', '')}")

    return "\n".join(parts)


def inject_into_system_prompt(system_prompt: str, memory_context: str) -> str:
    """将记忆上下文附加到 system prompt."""
    if not memory_context:
        return system_prompt
    return f"{system_prompt}\n\n# 参考上下文 (来自历史案例/指南/决策记录)\n{memory_context}\n\n请结合以上参考信息进行推理，但以最新指南为准。"
