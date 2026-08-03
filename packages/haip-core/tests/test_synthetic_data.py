"""haip/eval 去污染 + 合成数据引擎测试."""

from __future__ import annotations

import pytest


def test_ngram_normalization():
    from haip.eval.decontaminate import _normalize, ngrams
    assert _normalize(" 患者 A，B. ") == "患者ab"
    sig = ngrams("老年髋部骨折需48小时内手术", 5)
    assert sig  # 非空
    assert len(sig) >= 1


def test_jaccard_identical():
    from haip.eval.decontaminate import jaccard, text_signature
    t = "老年髋部骨折患者应在48小时内完成手术评估"
    assert jaccard(text_signature(t), text_signature(t)) == 1.0


def test_contamination_detection():
    from haip.eval.decontaminate import check_contamination
    base = "老年髋部骨折患者应在48小时内完成手术评估并转骨科处理"
    same = check_contamination(base, base)
    assert same["contaminated"] is True
    unrelated = check_contamination("患者出现皮疹伴瘙痒", "肺炎链球菌感染的治疗指南")
    assert unrelated["contaminated"] is False


def test_check_corpus_flags():
    from haip.eval.decontaminate import check_corpus_against_refs
    corpus = ["老年髋部骨折患者应在48小时内完成手术评估并转骨科处理", "普通感冒多饮水休息"]
    refs = ["老年髋部骨折患者应在48小时内完成手术评估并转骨科处理"]
    flagged = check_corpus_against_refs(corpus, refs)
    assert len(flagged) == 1
    assert flagged[0]["index"] == 0


def test_load_rules_and_guidelines():
    from haip.eval.synthetic import load_guidelines_meta, load_rules_yaml
    rules = load_rules_yaml("timing_rules.yaml")
    assert "delay_factors" in rules
    gs = load_guidelines_meta()
    assert len(gs) > 0
    assert all("name" in g and "trust_level" in g for g in gs)


def test_synth_timing_qa_gold():
    from haip.eval.synthetic import synth_timing_qa
    item = synth_timing_qa({
        "age": 85, "diagnosis": "左股骨颈骨折",
        "lab_results": {"肌钙蛋白I": 0.5},
    })
    assert item is not None
    assert item["gold"]["urgency"] in ("emergency", "urgent", "elective")
    assert item["urgency"] == item["gold"]["urgency"]  # 金标签一致


def test_synth_guideline_qa_refs():
    from haip.eval.synthetic import synth_guideline_qa
    items = synth_guideline_qa(limit=3)
    assert 1 <= len(items) <= 3
    for it in items:
        assert it["guideline_ref"]  # 溯源非空
        assert it["trust_level"]


def test_build_corpus_and_decontamination():
    from haip.eval.synthetic import build_synthetic_corpus
    corpus = build_synthetic_corpus(timing_limit=3, guideline_limit=2)
    assert corpus["stats"]["timing_qa"] == 3
    assert corpus["stats"]["guideline_qa"] == 2
    assert corpus["decontamination"]["total"] == 5
    assert "flagged" in corpus["decontamination"]


def test_seed_cases_from_corpus(tmp_path):
    from haip.eval.synthetic import build_synthetic_corpus
    from haip.evolution.engine import seed_cases_from_corpus
    from haip.evolution.memory_base import EvolutionMemory

    mem = EvolutionMemory(db_path=str(tmp_path / "seed.db"))
    try:
        corpus = build_synthetic_corpus(timing_limit=2, guideline_limit=1)
        n = seed_cases_from_corpus(corpus["items"], memory=mem)
        assert n == 3
        assert mem.count_cases() == 3
        assert mem.get_case  # 可检索
    finally:
        mem.close()
