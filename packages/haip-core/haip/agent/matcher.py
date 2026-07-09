"""Agent Matcher — 模糊匹配 Agent 名称 (中文/英文/别名).

参照 haip-0705-2 agent_matcher.py 的 3 级降级匹配策略.
"""

from __future__ import annotations

import difflib

from haip.agent import list_all


CANONICAL_ALIASES: dict[str, list[str]] = {
    "pharmacy": ["药剂科", "药房", "pharmacy", "药学", "pharmacy agent"],
    "orthopedic-surgery": ["骨科", "创伤骨科", "骨外科", "ortho", "orthopedic", "orthopedics"],
    "cardio-surgery": ["心外科", "心血管外科", "心脏外科", "cardio", "cardiac surgery"],
    "cardio-risk": ["心脏评估", "心内科", "cardio-risk", "心脏风险评估"],
    "anesthesia-risk": ["麻醉", "麻醉评估", "anesthesia", "麻醉科"],
    "pediatrics": ["儿科", "小儿科", "peds", "pediatrics"],
    "medical-record": ["病历", "患者数据", "medical-record", "患者中心"],
    "metrics": ["指标", "数据指标", "metrics", "全院指标"],
    "pain-hub": ["疼痛", "疼痛中枢", "pain", "疼痛门户", "疼痛专病"],
    "acute-pain": ["急性疼痛", "acute pain", "术后疼痛"],
    "chronic-pain": ["慢性疼痛", "chronic pain"],
    "cancer-pain": ["癌性疼痛", "cancer pain", "癌痛"],
    "interventional-pain": ["介入疼痛", "interventional", "介入治疗"],
    "pain-rehab": ["疼痛康复", "pain rehab", "康复"],
}


def _normalize(text: str) -> str:
    """去除常见后缀。"""
    for suffix in ["agent", "智能体", "domain", "科室", "bot", "机器人", "系统", "模块", "agent", " "]:
        text = text.replace(suffix, "")
    return text.strip().lower()


def resolve(keyword: str) -> str | None:
    """3 级降级匹配: 精确 → 子串 → 模糊 difflib。"""
    kw = keyword.strip().lower()
    if not kw:
        return None

    # L1: 精确匹配
    inverted: dict[str, str] = {}
    for canonical, aliases in CANONICAL_ALIASES.items():
        for alias in aliases:
            inverted[alias.lower()] = canonical
        inverted[canonical.lower()] = canonical
    if kw in inverted:
        return inverted[kw]

    # 也尝试注册表中已有的 Agent
    for name in list_all():
        if kw == name.lower() or kw == _normalize(name):
            return name

    # L2: 子串匹配
    best_match = None
    best_len = 999
    for alias, canonical in inverted.items():
        if kw in alias:
            if len(alias) < best_len:
                best_match = canonical
                best_len = len(alias)
    if best_match:
        return best_match

    # L3: difflib 模糊匹配
    matches = difflib.get_close_matches(kw, list(inverted.keys()), n=1, cutoff=0.5)
    if matches:
        return inverted[matches[0]]

    return None


def search(keyword: str, limit: int = 5) -> list[dict]:
    """返回 Top-N 匹配结果, 含评分。"""
    results: list[dict] = []
    kw = keyword.strip().lower()
    if not kw:
        return results

    for canonical, aliases in CANONICAL_ALIASES.items():
        for alias in aliases:
            score = 0.0
            al = alias.lower()
            if kw == al:
                score = 1.0
            elif kw in al:
                score = 0.7 + (len(kw) / len(al)) * 0.2
            elif al in kw:
                score = 0.5
            elif difflib.SequenceMatcher(None, kw, al).ratio() > 0.5:
                score = difflib.SequenceMatcher(None, kw, al).ratio()
            if score > 0:
                results.append({"name": canonical, "alias": alias, "score": round(score, 2)})

    results.sort(key=lambda x: x["score"], reverse=True)
    seen = set()
    unique = []
    for r in results:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    return unique[:limit]


def get_display_name(canonical: str) -> str:
    """返回中文显示名。"""
    aliases = CANONICAL_ALIASES.get(canonical, [])
    for a in aliases:
        if any('\u4e00' <= c <= '\u9fff' for c in a):
            return a
    return canonical
