"""KG 实体抽取 — 从 YAML 资产提取指南/规则/BP/科室/诊断实体."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from haip.kg.store import KGStore, get_kg_store

_KNOWLEDGE_BASE = Path(__file__).resolve().parents[4] / "packages" / "haip-hospital" / "knowledge"
_GUIDELINES_DIR = _KNOWLEDGE_BASE / "guidelines"
_RULES_DIR = _KNOWLEDGE_BASE / "rules"
_BP_DIR = _KNOWLEDGE_BASE / "business_processes"
_PATIENTS_FILE = Path(__file__).resolve().parents[4] / "packages" / "haip-hospital" / "data" / "patients.json"


def _extract_guideline(g: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "id": g.get("id", ""),
        "name": g.get("name", ""),
        "abbr": g.get("abbr", ""),
        "publisher": g.get("publisher", ""),
        "trust_level": str(g.get("trust_level", "")),
        "version": str(g.get("version", "")),
        "description": str(g.get("description", ""))[:200],
        "source_file": source,
    }


def _extract_rule(rule: dict[str, Any], rule_set_id: str, source: str) -> dict[str, Any]:
    return {
        "id": rule.get("id", f"{rule_set_id}-{rule.get('decision_point','?')}"[:40]),
        "rule_set_id": rule_set_id,
        "decision_point": str(rule.get("decision_point", "") or rule.get("name", ""))[:80],
        "condition_expr": str(rule.get("condition", "") or rule.get("condition_expr", ""))[:200],
        "conclusion": str(rule.get("conclusion", ""))[:200],
        "certainty": str(rule.get("certainty", "")),
        "evidence_sources": rule.get("evidence_sources", rule.get("guideline_ref", [])),
        "source_file": source,
    }


def _extract_bp_step(step: dict[str, Any], bp_id: str, source: str, idx: int) -> dict[str, Any]:
    sid = step.get("id", f"{bp_id}-s{idx}")
    imp = step.get("implementation", {}) or {}
    return {
        "id": sid,
        "bp_id": bp_id,
        "name": str(step.get("name", ""))[:80],
        "actor": str(step.get("actor", "")),
        "description": str(step.get("description", ""))[:300],
        "decision": str(step.get("decision", "")),
        "data_used": step.get("data_used", []) or imp.get("data_used", []),
        "rule_ids": imp.get("rule_ids", []) or step.get("rule_ids", []),
        "source_file": source,
    }


def extract_all(store: KGStore | None = None) -> dict[str, int]:
    """全量实体抽取: 指南/规则/BP/科室/诊断 → KG.

    Returns {entity_type: count}
    """
    store = store or get_kg_store()
    counts: dict[str, int] = {}

    # ── 指南实体 ──
    gcnt = 0
    if _GUIDELINES_DIR.is_dir():
        for f in sorted(_GUIDELINES_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict) or not data.get("name"):
                    continue
                g = _extract_guideline(data, f.name)
                if g["id"]:
                    store.upsert_guideline(**g)
                    gcnt += 1
            except Exception:
                continue
    counts["guidelines"] = gcnt

    # ── 规则实体 ──
    rcnt = 0
    if _RULES_DIR.is_dir():
        for f in sorted(_RULES_DIR.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    raw = fh.read()
                for doc in yaml.safe_load_all(raw):
                    if not isinstance(doc, dict):
                        continue
                    rule_set = doc.get("name", f.stem)
                    rules = doc.get("rules", []) or doc.get("delay_factors", [])
                    for rule in rules:
                        gid = rule.get("id", "")
                        if not gid:
                            gid = f"{f.stem}-{rule.get('decision_point',rule.get('name','?'))}"[:40]
                        r = _extract_rule(rule, rule_set, f.name)
                        store.upsert_rule(**r)
                        rcnt += 1
            except Exception:
                continue
    counts["rules"] = rcnt

    # ── BP 步骤实体 ──
    bcnt = 0
    if _BP_DIR.is_dir():
        for f in sorted(_BP_DIR.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    continue
                bp_id = data.get("name", f.stem)
                for idx, step in enumerate(data.get("steps", [])):
                    r = _extract_bp_step(step, bp_id, f.name, idx)
                    store.upsert_bp_step(**r)
                    bcnt += 1
            except Exception:
                continue
    counts["bp_steps"] = bcnt

    # ── 科室实体 ──
    dcnt = 0
    from haip.agent import list_all, load_from_dir
    defs_dir = Path(__file__).resolve().parents[4] / "packages" / "haip-hospital" / "agents" / "definitions"
    try:
        load_from_dir(str(defs_dir))
    except Exception:
        pass
    for name, agent in list_all().items():
        store.upsert_department(
            did=name,
            name=agent.cn_name or name,
            type=str(agent.type),
            source_file=f"{name}.yaml",
        )
        dcnt += 1
    counts["departments"] = dcnt

    # ── 诊断实体 ──
    picnt = 0
    if _PATIENTS_FILE.exists():
        import json
        with open(_PATIENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        patients = data.get("patients", []) if isinstance(data, dict) else data
        seen: set[str] = set()
        for p in patients:
            icd = str(p.get("icd10", "") or p.get("patient_id", ""))
            dx = str(p.get("diagnosis", ""))
            if not dx or icd in seen:
                continue
            seen.add(icd)
            store.upsert_diagnosis(
                icd10=icd,
                name=dx,
                compatible_agents=p.get("compatible_agents", []),
                source_file="patients.json",
            )
            picnt += 1
    counts["diagnoses"] = picnt

    return counts
