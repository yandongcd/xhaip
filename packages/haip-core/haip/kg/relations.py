"""KG 关系构建 — 指南→规则 / BP→科室 / 规则→证据 等关系自动构建."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from haip.kg.store import KGStore, get_kg_store

_KNOWLEDGE_BASE = Path(__file__).resolve().parents[4] / "packages" / "haip-hospital" / "knowledge"
_GUIDELINES_DIR = _KNOWLEDGE_BASE / "guidelines"
_BP_DIR = _KNOWLEDGE_BASE / "business_processes"


def build_all_relations(store: KGStore | None = None) -> dict[str, int]:
    """自动构建全部关系.

    Relations:
      - guides: guideline → rule
      - recommended_by: rule → guideline (reverse evidence)
      - performed_by: bp_step → department
      - uses_rule: bp_step → rule
      - diagnosed_by: diagnosis → agent (compatible_agents)
    """
    store = store or get_kg_store()
    store.clear_relations()
    counts: dict[str, int] = {}

    # ── guides: guideline → rule (from key_sections.rule_ids) ──
    gcnt = 0
    if _GUIDELINES_DIR.is_dir():
        for f in sorted(_GUIDELINES_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    continue
                gid = data.get("id", "") or data.get("name", "")
                trust = str(data.get("trust_level", ""))
                for ks in data.get("key_sections", []) or []:
                    rule_ids = ks.get("rule_ids", []) or []
                    for rid in rule_ids:
                        store.add_relation("guideline", gid, "guides", "rule", str(rid),
                                           trust_level=trust, evidence=f"{f.name}#{ks.get('id','')}")
                        gcnt += 1
            except Exception:
                continue
    counts["guides"] = gcnt

    # ── recommended_by: rule → guideline (reverse) ──
    rcnt = 0
    if _GUIDELINES_DIR.is_dir():
        for f in sorted(_GUIDELINES_DIR.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    continue
                gid = data.get("id", "") or data.get("name", "")
                trust = str(data.get("trust_level", ""))
                g_ref = data.get("guideline_ref", []) or []
                for s in data.get("rule_sets_covered", []) or []:
                    for gid_target in (g_ref if g_ref else [s]):
                        store.add_relation("guideline", gid, "recommends", "guideline", str(gid_target)[:60],
                                           trust_level=trust, evidence=f.name)
                        rcnt += 1
            except Exception:
                continue
    counts["recommends"] = rcnt

    # ── performed_by: bp_step → department ──
    pcnt = 0
    if _BP_DIR.is_dir():
        for f in sorted(_BP_DIR.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    continue
                for step in data.get("steps", []):
                    actor = (step.get("actor", "") or "").strip()
                    if not actor:
                        continue
                    # actor 可能是 "主治医生 + 护士长" 形式, 拆成多个
                    sid = step.get("id", step.get("name", ""))
                    for a in actor.replace("+", "、").replace("/", "、").split("、"):
                        a = a.strip().rstrip("医生").rstrip("师")
                        if a:
                            store.add_relation("bp_step", str(sid), "performed_by", "department", a,
                                               evidence=f.name)
                            pcnt += 1
            except Exception:
                continue
    counts["performed_by"] = pcnt

    # ── uses_rule: bp_step → rule ──
    ucnt = 0
    if _BP_DIR.is_dir():
        for f in sorted(_BP_DIR.glob("*.yaml")):
            try:
                with open(f, encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    continue
                for step in data.get("steps", []):
                    imp = step.get("implementation", {}) or {}
                    rule_ids = imp.get("rule_ids", []) or step.get("rule_ids", []) or []
                    for rid in rule_ids:
                        store.add_relation("bp_step", str(step.get("id", step.get("name", ""))),
                                           "uses_rule", "rule", str(rid), evidence=f.name)
                        ucnt += 1
            except Exception:
                continue
    counts["uses_rule"] = ucnt

    return counts
