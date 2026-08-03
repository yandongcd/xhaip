"""KG 查询引擎 — 按诊断/agent/证据链查询知识图谱."""

from __future__ import annotations

import json
from typing import Any

from haip.kg.store import KGStore, get_kg_store


def _to_list(v: Any) -> list[str]:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return [v]
    return list(v) if v else []


def _rows(store: KGStore, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    with store._lock:
        conn = store._get_conn()
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def by_diagnosis(dx_name: str, store: KGStore | None = None) -> dict[str, Any]:
    """按诊断名查询: → 相关指南/规则/检查/科室."""
    store = store or get_kg_store()
    diag_lower = dx_name.lower().replace(" ", "").replace("骨折", "")

    # 匹配诊断
    diags = _rows(store,
        "SELECT * FROM kg_diagnoses WHERE LOWER(REPLACE(name, ' ', '')) LIKE ?",
        [f"%{diag_lower}%"])

    guidelines: list[dict] = []
    rules: list[dict] = []
    depts: set[str] = set()

    # 从诊断→兼容agent→科室
    for d in diags:
        agents = _to_list(d.get("compatible_agents", "[]"))
        for a in agents:
            depts.add(a)

    # 指南查询: 按科室关键词匹配
    for dept in list(depts)[:5]:
        g_rows = _rows(store,
            "SELECT * FROM kg_guidelines WHERE 1=1 LIMIT 30", [])
        for g in g_rows:
            if not guidelines and g.get("name") or any(kw in str(g.get("name", "")).lower() for kw in ("hip", "fracture", "orthop", "髋", "骨", "femoral", "surgery")):
                guidelines.append(g)

    # 从指南id找规则 (通过 kg_relations: guides relation)
    for g in guidelines[:5]:
        rels = _rows(store,
            "SELECT * FROM kg_relations WHERE relation_type='guides' AND source_id = ?",
            [g["id"]])
        for rel in rels:
            rule_rows = _rows(store, "SELECT * FROM kg_rules WHERE id LIKE ?", [f"%{rel['target_id']}%"])
            rules.extend(rule_rows)
        if not rules:
            rule_rows = _rows(store, "SELECT * FROM kg_rules LIMIT 15", [])
            rules = rule_rows

    if not guidelines:
        guidelines = _rows(store, "SELECT * FROM kg_guidelines LIMIT 10", [])

    total_rels = _rows(store, "SELECT COUNT(*) as cnt FROM kg_relations", [])
    return {
        "diagnosis": dx_name,
        "matched_diagnoses": len(diags),
        "departments": sorted(depts) if depts else [],
        "guidelines": guidelines[:10],
        "rules": rules[:15],
        "relations": total_rels[0]["cnt"] if total_rels else 0,
    }


def trace_evidence(rule_id: str, store: KGStore | None = None) -> dict[str, Any]:
    """追溯某条规则的证据链: rule → guideline."""
    store = store or get_kg_store()
    rule_rows = _rows(store, "SELECT * FROM kg_rules WHERE id LIKE ?", [f"%{rule_id}%"])
    rels = _rows(store,
        "SELECT * FROM kg_relations WHERE relation_type='guides' AND target_id LIKE ?",
        [f"%{rule_id}%"])
    guidelines = []
    for rel in rels:
        gid = rel["source_id"]
        g_rows = _rows(store, "SELECT * FROM kg_guidelines WHERE id = ? OR name = ?", [gid, gid])
        guidelines.extend(g_rows)
    return {
        "rule_id": rule_id,
        "rule_records": rule_rows[:5],
        "guidelines": [{k: v for k, v in g.items() if k in ("id", "name", "trust_level", "publisher")} for g in guidelines],
        "trust_level": rels[0]["trust_level"] if rels else "",
    }


def find_conflicts(dx_name: str, store: KGStore | None = None) -> list[dict[str, Any]]:
    """找冲突: 同一诊断不同指南推荐不同 rule."""
    store = store or get_kg_store()
    diag_lower = dx_name.lower().replace(" ", "").replace("骨折", "")
    rel_rows = _rows(store,
        "SELECT r.* FROM kg_relations r JOIN kg_diagnoses d ON r.source_id LIKE '%' || d.name || '%' WHERE LOWER(REPLACE(d.name,' ','')) LIKE ? AND r.relation_type='guides'",
        [f"%{diag_lower}%"])
    if not rel_rows:
        return []
    from collections import Counter
    ruling = Counter()
    for r in rel_rows:
        ruling[r["target_id"]] += 1
    return [{"rule_id": k, "guideline_count": v} for k, v in ruling.most_common() if v >= 2]


def stats(store: KGStore | None = None) -> dict[str, Any]:
    store = store or get_kg_store()
    return {
        "entities": store.count_entities(),
        "relations": store.count_relations(),
    }
