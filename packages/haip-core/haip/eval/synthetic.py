"""合成数据引擎 — 金标签拒绝采样 + 指南接地 QA (Meditron 配方借鉴).

来源1: 规则金标签拒绝采样 (Meditron: retry-until-match)
  用 knowledge/rules YAML + shared.timing_engine 计算金标准,
  生成 {question, answer, gold} 合成问答, 作为进化案例库种子.
  规则引擎结果即"金标签" — 无需 LLM 人工标注 (SEAL 免标注思想).

来源2: 指南接地 QA (Meditron guidelines-qa 借鉴)
  从 knowledge/guidelines/*.yaml 元数据构造指南问答,
  带 guideline_ref 溯源 (天然满足 Citation 引擎).
"""

from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Any

from haip.eval.decontaminate import check_contamination

_KNOWLEDGE_BASE = Path(__file__).resolve().parents[4] / "packages" / "haip-hospital" / "knowledge"


def load_rules_yaml(name: str) -> dict[str, Any]:
    """加载 knowledge/rules/<name>.yaml."""
    import yaml
    path = _KNOWLEDGE_BASE / "rules" / name
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_guidelines_meta() -> list[dict[str, Any]]:
    """加载 knowledge/guidelines/*.yaml 的元数据 (name/abbr/publisher/trust)."""
    import yaml
    out: list[dict[str, Any]] = []
    gdir = _KNOWLEDGE_BASE / "guidelines"
    if not gdir.is_dir():
        return out
    for f in sorted(gdir.glob("*.yaml")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, dict) and data.get("name"):
                out.append({
                    "source_file": f.name,
                    "name": data.get("name", ""),
                    "abbr": data.get("abbr", ""),
                    "publisher": data.get("publisher", ""),
                    "version": data.get("version", ""),
                    "trust_level": data.get("trust_level", ""),
                    "description": str(data.get("description", ""))[:200],
                })
        except Exception:
            continue
    return out


# ═══════════════════════════════════════════════════
# 来源1: 规则金标签拒绝采样
# ═══════════════════════════════════════════════════

def synth_timing_qa(
    patient: dict[str, Any],
    max_attempts: int = 8,
    temperature: float = 0.7,
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    """手术时机合成问答 — 金标签来自 shared.timing_engine.

    拒绝采样语义: 若 LLM 生成答案与金标签不一致, 重试 (max_attempts).
    mock 模式: 直接用规则引擎答案 (确定性金标签, 无 LLM).
    """
    rng = rng or random.Random()
    from orthopedics.timing_engine import evaluate_timing

    gold = evaluate_timing(patient)
    urgency = gold.get("urgency", "")
    if not urgency:
        return None

    question = (f"患者 {patient.get('age', '')}岁 诊断为{patient.get('diagnosis', '')}"
                f"，lab: {_lab_summary(patient)} — 手术时机如何安排?")
    answer = gold.get("timing_conclusion", "") or gold.get("recommendation", "")
    # 拒绝采样 (模拟重试直到与金标签一致; mock 直接采纳规则答案)
    for _ in range(max_attempts):
        if rng.random() > 0.1:  # 模拟 LLM 一致率 90%
            break
    return {
        "type": "timing_qa",
        "question": question,
        "answer": answer,
        "gold": {"urgency": urgency},
        "urgency": urgency,
        "guideline_ref": gold.get("guideline_refs", []),
    }


def _lab_summary(patient: dict[str, Any]) -> str:
    labs = patient.get("lab_results") or {}
    items = []
    for k, v in list(labs.items())[:4]:
        try:
            items.append(f"{k}={float(v)}")
        except (TypeError, ValueError):
            continue
    return "; ".join(items) or "无"


def synth_rule_qa_from_patients(
    patients: list[dict[str, Any]],
    limit: int = 0,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """从数字病人批量生成规则金标签 QA (拒绝采样)."""
    rng = rng or random.Random()
    out = []
    for p in patients:
        if "股骨颈" not in str(p.get("diagnosis", "")) and "转子" not in str(p.get("diagnosis", "")) and "髋部" not in str(p.get("diagnosis", "")):
            continue
        item = synth_timing_qa(p, rng=rng)
        if item:
            out.append(item)
        if limit and len(out) >= limit:
            break
    return out


# ═══════════════════════════════════════════════════
# 来源2: 指南接地 QA
# ═══════════════════════════════════════════════════

def synth_guideline_qa(
    guidelines: list[dict[str, Any]] | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """指南元数据 → 指南接地 QA (带 trust_level/guideline_ref 溯源)."""
    guidelines = guidelines if guidelines is not None else load_guidelines_meta()
    out = []
    for g in guidelines:
        if not g.get("description"):
            continue
        out.append({
            "type": "guideline_qa",
            "question": f"《{g['name']}》的核心推荐是什么?",
            "answer": g["description"],
            "gold": {"source": g["name"]},
            "guideline_ref": [g.get("source_file", "")],
            "trust_level": g.get("trust_level", ""),
            "publisher": g.get("publisher", ""),
        })
        if limit and len(out) >= limit:
            break
    return out


# ═══════════════════════════════════════════════════
# 汇总与去污染
# ═══════════════════════════════════════════════════

def build_synthetic_corpus(
    patients: list[dict[str, Any]] | None = None,
    timing_limit: int = 20,
    guideline_limit: int = 10,
    seed: int = 42,
) -> dict[str, Any]:
    """构建合成语料 {items, decontamination, stats}."""
    rng = random.Random(seed)
    if patients is None:
        from haip.patients import load_all_patients
        patients = load_all_patients()

    items: list[dict[str, Any]] = []
    items += synth_rule_qa_from_patients(patients, limit=timing_limit, rng=rng)
    items += synth_guideline_qa(limit=guideline_limit)

    # 去污染: 合成语料 vs 指南/规则参考 (同源检查)
    ref_texts = []
    for g in load_guidelines_meta()[:20]:
        if g.get("description"):
            ref_texts.append(g["description"])
    for rule_file in ("timing_rules.yaml", "completeness_rules.yaml", "surgery_type_rules.yaml"):
        data = load_rules_yaml(rule_file)
        ref_texts.append(str(data)[:2000])

    flagged = []
    for i, item in enumerate(items):
        text = item["question"] + " " + item.get("answer", "")
        for ref in ref_texts:
            result = check_contamination(text, ref)
            if result["contaminated"]:
                flagged.append({"index": i, **result})
                break

    return {
        "items": items,
        "decontamination": {
            "flagged": flagged,
            "flagged_count": len(flagged),
            "total": len(items),
        },
        "stats": {
            "timing_qa": sum(1 for i in items if i["type"] == "timing_qa"),
            "guideline_qa": sum(1 for i in items if i["type"] == "guideline_qa"),
        },
    }


def save_corpus(corpus: dict[str, Any], path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in corpus["items"])
