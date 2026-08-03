"""跃迁模块综合测试 — KG/审问Guard/MASB/ARP/ASVP/存活知识/转归/公平/溯源/HLAC."""

from __future__ import annotations

import pytest

# ═══════════════ KG ═══════════════

def test_kg_extract_entities():
    from haip.kg import extract_all
    counts = extract_all()
    assert counts["guidelines"] > 0
    assert counts["departments"] > 0
    assert counts["diagnoses"] > 0


def test_kg_relations_build():
    from haip.kg import build_all_relations, stats
    build_all_relations()
    s = stats()
    assert s["relations"] > 0


def test_kg_query_by_diagnosis():
    from haip.kg import build_all_relations, by_diagnosis, extract_all
    extract_all()
    build_all_relations()
    result = by_diagnosis("股骨颈骨折")
    assert "guidelines" in result
    assert "rules" in result


def test_kg_trace_evidence():
    from haip.kg import build_all_relations, extract_all, trace_evidence
    extract_all()
    build_all_relations()
    ev = trace_evidence("surgery-type-001")
    assert "guidelines" in ev


# ═══════════════ 审问式 Guard ═══════════════

def test_interrogate_mock_safe_fallback():
    from haip.guard.interrogate import interrogate
    from haip.llm.mock import MockProvider
    report = interrogate("建议手术", provider=MockProvider({}))
    assert report.requires_human_review is True  # 解析失败 → 安全降级


def test_interrogate_parse_json():
    from haip.guard.interrogate import _parse_interrogation
    parsed = _parse_interrogation('{"challenges": [{"dimension": "x", "passed": true}]}')
    assert parsed is not None
    assert parsed[0]["dimension"] == "x"


def test_guard_verifier_interrogation_field():
    from haip.guard.verifier import GuardVerifier
    from haip.llm.mock import MockProvider
    v = GuardVerifier(llm_provider=MockProvider({}))
    r = v.verify("建议手术", scenario="手术决策")
    assert hasattr(r, "interrogated")


# ═══════════════ MASB ═══════════════

def test_masb_evaluate_block():
    from haip.eval.masb import SafetyBenchmark
    sb = SafetyBenchmark()
    sc = sb.scenarios[0]
    r = sb.evaluate(sc["dangerous_action"], sc, {"passed": False})
    assert r["passed"] is True  # Guard 拦截了危险推荐


def test_masb_run_all():
    from haip.eval.masb import SafetyBenchmark
    sb = SafetyBenchmark()
    outputs = [(s["safe_action"], None) for s in sb.scenarios]
    r = sb.run_all(agent_outputs=outputs)
    assert r["pass_rate"] >= 0
    assert r["total_scenarios"] >= 5


# ═══════════════ ARP ═══════════════

def test_arp_hierarchy_gate():
    from haip.eval.arp import ARPExaminer, ARPLevel
    ex = ARPExaminer()
    # 未过前置等级不能考高级
    c = ex.examine("test-agent", ARPLevel.ATTENDING)
    assert c.passed is False
    assert "认证" in c.details.get("error", "")  # 前置条件门控生效


def test_arp_criteria_structure():
    from haip.eval.arp import ARP_CRITERIA, ARPLevel
    for level in ARPLevel:
        assert ARP_CRITERIA[level]["pass_rate"] > 0


# ═══════════════ ASVP ═══════════════

def test_asvp_generate_scenarios():
    from haip.eval.asvp import AdversarialScenarioGenerator
    scs = AdversarialScenarioGenerator().generate(count=4)
    assert len(scs) >= 4
    assert all(s.id for s in scs)


def test_asvp_run_all():
    from haip.eval.asvp import RedTeamEvaluator
    report = RedTeamEvaluator().run_all()
    assert report["total_attacks"] > 0
    assert "by_attack_pattern" in report


def test_asvp_guard_rules_proposal():
    from haip.eval.asvp import RedTeamEvaluator
    ev = RedTeamEvaluator()
    ev.run_all()
    rules = ev.propose_guard_rules()
    assert isinstance(rules, list)


# ═══════════════ 存活知识库 ═══════════════

def test_living_snapshot(tmp_path):
    from haip.knowledge.living import check_guideline_changes, update_snapshot
    snap_file = str(tmp_path / "snap.json")
    r = update_snapshot(snap_file)
    assert r["guidelines_scanned"] > 0
    changes = check_guideline_changes(snap_file)
    assert isinstance(changes, list)


# ═══════════════ 转归引擎 ═══════════════

def test_progression_emergency_path():
    from haip.clinical.progression import PatientState, ProgressionEngine
    eng = ProgressionEngine(seed=42)
    outcomes = []
    for _ in range(50):
        s, _ = eng.next_state(PatientState.STABLE, "急诊手术在48h内完成")
        outcomes.append(s)
    recovering = sum(1 for s in outcomes if s == PatientState.RECOVERING)
    assert recovering >= 35  # 90% 概率 → 50次应≥35


def test_progression_delay_worse():
    from haip.clinical.progression import PatientState, ProgressionEngine
    eng = ProgressionEngine(seed=42)
    emergency_deteriorating = 0
    delay_deteriorating = 0
    for _ in range(100):
        s, _ = eng.next_state(PatientState.STABLE, "急诊手术在48h内完成")
        if s == PatientState.DETERIORATING:
            emergency_deteriorating += 1
    for _ in range(100):
        s, _ = eng.next_state(PatientState.STABLE, "手术延迟 >48h")
        if s == PatientState.DETERIORATING:
            delay_deteriorating += 1
    assert delay_deteriorating > emergency_deteriorating


# ═══════════════ 虚拟病人 ═══════════════

def test_patient_agent_complaint():
    from haip.clinical.patient_agent import PatientAgent
    p = PatientAgent({"patient_id": "P1", "age": 80, "gender": "女",
                      "diagnosis": "股骨颈骨折", "scenario": "摔倒后左髋疼痛"})
    complaint = p.complain()
    assert "股骨颈骨折" in complaint


def test_patient_agent_treatment_outcome():
    from haip.clinical.patient_agent import PatientAgent
    p = PatientAgent({"patient_id": "P2", "age": 85, "diagnosis": "股骨颈骨折"}, seed=42)
    state, rule = p.receive_treatment("急诊手术在48h内完成")
    assert state.value in ("recovering", "deteriorating", "deceased", "stable")
    assert rule is None or rule.guideline_ref


def test_patient_agent_is_alive():
    from haip.clinical.patient_agent import PatientAgent
    p = PatientAgent({"patient_id": "P3", "diagnosis": "髋部骨折"})
    assert p.is_alive() is True
    assert p.is_recovered() is False


# ═══════════════ 公平性 ═══════════════

def test_fairness_gender():
    from haip.clinical.fairness import check_gender_fairness
    patients = [{"diagnosis": "心肌梗死", "gender": "M"},
                {"diagnosis": "心肌梗死", "gender": "M"},
                {"diagnosis": "心肌梗死", "gender": "F"}]
    r = check_gender_fairness(patients)
    assert "gender_gaps" in r


def test_fairness_age_strata():
    from haip.clinical.fairness import check_age_stratification
    patients = [{"age": 20}, {"age": 50}, {"age": 70}, {"age": 85}]
    r = check_age_stratification(patients)
    assert r["strata"]["青年"] > 0
    assert r["strata"]["高龄"] > 0


# ═══════════════ TOGAF-AI 溯源 ═══════════════

def test_trace_recorder():
    from haip.togaf.trace import TraceRecorder
    recorder = TraceRecorder("orthopedic-surgery", "P1")
    recorder.record_kg_query("股骨颈骨折", [{"name": "AAOS"}], "T1")
    recorder.record_rule_execution("timing-rule-t2-001", "high_weight>=1", "elective")
    recorder.record_guard_interrogation(True, 8, 3)
    trace = recorder.finalize("最终结论")
    d = trace.to_dict()
    assert len(d["steps"]) == 3
    assert trace.has_guideline_evidence()
    assert trace.has_rule_execution()
    assert trace.has_guard_interrogation()


# ═══════════════ HLAC ═══════════════

def test_hlac_adapt():
    from haip.clinical.hlac import HLACAdapter
    a = HLACAdapter(level=1)
    r = a.adapt("建议行人工全髋关节置换术(THA)治疗")
    assert "换" in r["adapted_text"] or "髋" in r["adapted_text"]
    assert r["simplified"] is True


def test_hlac_evidence_expand():
    from haip.clinical.hlac import HLACAdapter
    a = HLACAdapter(level=5)
    r = a.adapt("建议48h内行THA手术")
    assert "AAOS" in r["adapted_text"] or "NICE" in r["adapted_text"]
    assert r["evidence_expanded"] is True


def test_hlac_wrap_agent_output():
    from haip.clinical.hlac import HLACAdapter
    a = HLACAdapter(level=1)
    out = a.wrap_agent_output({"reply": "建议THA"})
    assert "hlac" in out
    assert out["hlac"]["hlac_level"] == 1


# ═══════════════ EvalTrajectory ═══════════════

def test_trajectory_protocol():
    from haip.evolution.trajectory import EvalTrajectory, ToolCallRecord
    t = EvalTrajectory(
        agent="orthopedic-surgery",
        patient={"age": 80, "diagnosis": "股骨颈骨折"},
        tool_calls=[ToolCallRecord(tool="timing_decision", ok=True)],
        gold={"urgency": "emergency"},
    )
    assert t.question_text() != ""
    assert t.has_failed() is False
    assert t.passed_count() == 1


# ═══════════════ 基准适配器 ═══════════════

def test_benchmark_list():
    from haip.eval.benchmark import list_benchmarks
    assert "builtin-eval" in list_benchmarks()


def test_benchmark_builtin_adapter():
    from haip.eval.benchmark import BuiltinAdapter
    a = BuiltinAdapter()
    assert a.setup() is True


def test_benchmark_cp_env_placeholder():
    from haip.eval.benchmark import CPEnvAdapter
    a = CPEnvAdapter()
    assert a.setup() is False  # 未安装外部环境
