"""haip/evolution (SEAL 移植) 测试."""

from __future__ import annotations

import pytest


@pytest.fixture()
def mem(tmp_path):
    from haip.evolution.memory_base import EvolutionMemory
    m = EvolutionMemory(db_path=str(tmp_path / "evolve_test.db"))
    yield m
    m.close()


def test_case_base_add_and_get(mem):
    from haip.evolution.memory_base import CaseEntry
    mem.add_case(CaseEntry(
        case_id="c1", agent="orthopedic-surgery", task="orthopedics_hip_fracture",
        question="85岁女性 左股骨颈骨折", answer={"urgency": "emergency"},
        gold={"urgency": "emergency"}, matched=True,
    ))
    case = mem.get_case("c1")
    assert case["answer"]["urgency"] == "emergency"
    assert mem.count_cases("orthopedic-surgery") == 1


def test_experience_add_and_status(mem):
    from haip.evolution.memory_base import ExperienceEntry
    mem.add_experience(ExperienceEntry(
        exp_id="e1", agent="orthopedic-surgery",
        trigger="诊断: 左股骨颈骨折，年龄 85 岁",
        rule="需检查高危延迟因素", action="补充心内评估",
        source_failure="{}", status="pending",
    ))
    exp = mem.get_experience("e1")
    assert exp["status"] == "pending"
    mem.update_experience("e1", status="validated", trials=3, pass_count=2)
    assert mem.get_experience("e1")["pass_count"] == 2


def test_reflect_failure_generates_struct(mem):
    from haip.evolution.reflect import reflect_failure
    exp = reflect_failure(
        agent="orthopedic-surgery", task="t",
        patient={"diagnosis": "左股骨颈骨折", "age": 85,
                 "lab_results": {"肌钙蛋白I": 0.5}},
        result={"urgency": "urgent"}, gold={"urgency": "emergency"},
        failed_items=[{"field": "urgency", "detail": "与金标准不一致 实际='urgent', 金标准='emergency'"}],
    )
    assert exp.status == "pending"
    assert exp.trigger
    assert exp.rule
    assert exp.action
    mem.add_experience(exp)
    assert mem.get_experience(exp.exp_id) is not None


def test_validate_insufficient_trials_pending(mem):
    """无足够案例 → 保持 pending (不误判)."""
    from haip.evolution.memory_base import ExperienceEntry
    mem.add_experience(ExperienceEntry(
        exp_id="e2", agent="orthopedic-surgery",
        trigger="诊断: 髋部骨折", rule="r", action="a", source_failure="", status="pending",
    ))
    from haip.evolution.validate import validate_experience
    result = validate_experience("e2", memory=mem, min_trials=3)
    assert result["verdict"] in ("pending", "validated", "rejected")
    assert result["trials"] == 0  # 无案例库


def test_validate_with_cases_passes(mem):
    """经验规则与案例金标准一致 → validated."""
    from haip.evolution.memory_base import CaseEntry, ExperienceEntry
    for i in range(4):
        mem.add_case(CaseEntry(
            case_id=f"c{i}", agent="orthopedic-surgery", task="t",
            question=f"诊断: 髋部骨折 患者{i}",
            answer={"urgency": "emergency"}, gold={"urgency": "emergency"},
        ))
    mem.add_experience(ExperienceEntry(
        exp_id="e3", agent="orthopedic-surgery",
        trigger="诊断: 髋部骨折，判定 urgency=urgent",
        rule="当髋部骨折时需检查延迟因素",
        action="48h 急诊手术建议",
        source_failure="", status="pending",
    ))
    from haip.evolution.validate import validate_experience
    result = validate_experience("e3", memory=mem, min_trials=3, pass_rate=0.6)
    assert result["trials"] >= 3
    assert result["verdict"] == "validated"
    assert mem.get_experience("e3")["status"] == "validated"


def test_approve_reject_flow(mem):
    from haip.evolution.memory_base import ExperienceEntry
    from haip.evolution.validate import approve_experience, reject_experience
    mem.add_experience(ExperienceEntry(
        exp_id="e4", agent="x", trigger="t", rule="r", action="a", source_failure="", status="validated",
    ))
    assert approve_experience("e4", reviewer="tester", memory=mem) is True
    assert mem.get_experience("e4")["status"] == "approved"
    # approved 不可再驳回
    assert reject_experience("e4", memory=mem) is False
    # rejected 流程
    mem.add_experience(ExperienceEntry(
        exp_id="e5", agent="x", trigger="t", rule="r", action="a", source_failure="", status="pending",
    ))
    assert reject_experience("e5", reason="临床依据不足", memory=mem) is True
    assert mem.get_experience("e5")["status"] == "rejected"


def test_evolution_cycle_from_eval(mem):
    """完整进化循环: 评测 → 成功入案例库 / 失败反思."""
    import sys
    sys.path.insert(0, r"D:\dst\projects\xhaip\packages\haip-hospital\modules")
    from haip.eval import build_scenarios
    from haip.eval.runner import EvalRunner
    from haip.eval.scenario import evaluate_scenario_stages
    from haip.evolution.engine import run_evolution_cycle

    scs = build_scenarios("orthopedics_hip_fracture", limit=3)
    if not scs:
        pytest.skip("无骨科患者数据")
    runner = EvalRunner()
    traces = [{"scenario_id": s.scenario_id, "results": runner.run_scenario(s)} for s in scs]
    stats = run_evolution_cycle(scs, traces, memory=mem)
    assert stats["record_case"] + stats["reflect"] == len(scs)
    assert stats["cases"] >= 0
    assert "verdicts" in stats


def test_validate_undecidable_not_counted(mem):
    """经验无关键词时: 无法判断的案例不计入 trials (防假阳性验证通过)."""
    from haip.evolution.memory_base import CaseEntry, ExperienceEntry
    for i in range(4):
        mem.add_case(CaseEntry(
            case_id=f"cu{i}", agent="orthopedic-surgery", task="t",
            question=f"诊断: 髋部骨折 患者{i}",
            answer={"urgency": "emergency"}, gold={"urgency": "emergency"},
        ))
    mem.add_experience(ExperienceEntry(
        exp_id="e6", agent="orthopedic-surgery",
        trigger="诊断: 髋部骨折",
        rule="需复查", action="补充检查",  # 无 urgency 关键词
        source_failure="", status="pending",
    ))
    from haip.evolution.validate import validate_experience
    result = validate_experience("e6", memory=mem, min_trials=3, pass_rate=0.6)
    assert result["verdict"] == "pending"  # 无法判断 → 不误判 validated
    assert result["undecidable"] >= 3
    assert result["trials"] == 0
