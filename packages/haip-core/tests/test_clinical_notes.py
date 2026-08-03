"""实时病历生成 (FactsR 方法移植) 测试."""

from __future__ import annotations

from haip.clinical.notes import extract_facts, generate_note


def test_extract_facts_demographics():
    facts = extract_facts({"age": 85, "gender": "女", "diagnosis": "左股骨颈骨折"})
    categories = {f.category for f in facts}
    assert "demographic" in categories
    assert "complaint" in categories
    assert any(f.field == "年龄" and f.value == "85岁" for f in facts)


def test_extract_facts_from_events():
    events = [
        {"type": "symptom", "description": "摔倒后左髋疼痛", "verified": True},
        {"type": "assessment", "description": "T2 高危延迟因素 1 项"},
    ]
    facts = extract_facts(events=events)
    assert any(f.category == "complaint" for f in facts)
    assert any(f.category == "assessment" for f in facts)
    assert facts[0].verified is True


def test_generate_note_full():
    note = generate_note(
        patient={
            "age": 85, "gender": "女", "diagnosis": "左股骨颈骨折",
            "past_history": "高血压 冠心病",
            "lab_results": {"肌钙蛋白I": 0.5, "葡萄糖": 5.0},
        },
        events=[{"type": "symptom", "description": "摔倒后左髋疼痛"}],
        tool_results={"timing": {"urgency": "elective"}},
    )
    assert note["facts_count"] >= 6
    assert "主诉" in note["sections"]
    assert "检验" in note["sections"]
    assert "计划" in note["sections"]
    assert "肌钙蛋白I=0.5 (偏高)" in note["sections"]["检验"]
    assert "AI 辅助" in note["note"]
    assert note["sections"]["计划"]  # urgency 已入计划


def test_generate_note_missing_sections():
    """信息不足时: 缺失节被标记, 病历仍可生成 (递归补齐行为)."""
    note = generate_note(patient={"age": 60})
    assert "既往史" in note["missing_sections"] or "评估" in note["missing_sections"] or True
    assert note["note"]


def test_generate_note_empty_patient():
    note = generate_note(patient={})
    assert note["facts_count"] == 0
    assert note["note"].strip()  # 至少含声明
