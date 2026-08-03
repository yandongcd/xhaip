"""急诊预检分诊 — C1/C2 临床正确性回归测试.

覆盖 (P0-2 修复):
  - C1: SpO2 数值比较 — 仅 key 存在不再命中; SpO2<85 → I 级, 85-92 → II 级
  - C2: 括号标准语义关键词匹配 — "急性心肌梗死(ST段抬高+胸痛+大汗)" 等
"""

from __future__ import annotations

from modules.emergency_triage import triage_assess


def _triage(chief: str, vitals: dict | None = None) -> dict:
    return triage_assess(
        patient_id="P001",
        chief_complaint=chief,
        vital_signs=vitals or {},
    )


def _level(result: dict) -> str:
    findings = result.get("findings", [])
    return str(findings[0].get("分诊级别", "")) if findings else ""


# ════════════════════════════════════════════════════════
# C1: SpO2 必须数值比较, 禁止存在即命中
# ════════════════════════════════════════════════════════

class TestSpO2ValueComparison:
    def test_normal_spo2_not_level1(self):
        """回归: 任何带 SpO2 的患者不再被分诊为 I 级."""
        result = _triage("腹痛", {"SpO2": 95, "SBP": 130})
        assert _level(result) == "III"

    def test_spo2_lt85_level1(self):
        result = _triage("腹痛", {"SpO2": 82, "SBP": 130})
        assert _level(result) == "I"

    def test_spo2_85_92_level2(self):
        result = _triage("腹痛", {"SpO2": 88, "SBP": 130})
        assert _level(result) == "II"

    def test_spo2_92_boundary_level2(self):
        result = _triage("腹痛", {"SpO2": 92, "SBP": 130})
        assert _level(result) == "II"

    def test_spo2_93_level3(self):
        result = _triage("腹痛", {"SpO2": 93, "SBP": 130})
        assert _level(result) == "III"

    def test_spo2_unparseable_no_match(self):
        """无法解析的 SpO2 值不得命中任何级别."""
        result = _triage("腹痛", {"SpO2": "未测", "SBP": 130})
        assert _level(result) == "III"

    def test_spo2_missing_no_match(self):
        result = _triage("腹痛", {"SBP": 130})
        assert _level(result) == "III"

    def test_spo2_matches_via_keyword_not_value(self):
        """关键词本身命中不受数值影响."""
        result = _triage("严重呼吸窘迫", {"SpO2": 98, "SBP": 130})
        assert _level(result) == "I"


# ════════════════════════════════════════════════════════
# C2: 括号标准按语义关键词命中
# ════════════════════════════════════════════════════════

class TestParentheticalCriteria:
    def test_ami_keyword_level1(self):
        """急性心肌梗死(ST段抬高+胸痛+大汗) → 关键词 '急性心肌梗死' → I 级."""
        result = _triage("急性心肌梗死", {"SpO2": 97, "SBP": 140})
        assert _level(result) == "I"

    def test_consciousness_loss_gcs_keyword_level1(self):
        result = _triage("意识丧失", {"SpO2": 97, "SBP": 120})
        assert _level(result) == "I"

    def test_stroke_keyword_level2(self):
        """卒中(FAST阳性, 发病<4.5h) → 关键词 '卒中' → II 级."""
        result = _triage("卒中", {"SpO2": 97, "SBP": 140})
        assert _level(result) == "II"

    def test_chest_pain_level2(self):
        """胸痛(疑似ACS) → 关键词 '胸痛' → II 级."""
        result = _triage("胸痛伴大汗", {"SpO2": 96, "SBP": 160})
        assert _level(result) == "II"

    def test_severe_respiratory_distress_level2(self):
        result = _triage("严重呼吸困难", {"SpO2": 96, "SBP": 140})
        assert _level(result) == "II"

    def test_abdominal_pain_level3(self):
        """腹痛(非急腹症) → 关键词 '腹痛' → III 级."""
        result = _triage("腹痛", {"SpO2": 97, "SBP": 130})
        assert _level(result) == "III"

    def test_fullwidth_parens_stripped(self):
        """全角括号同样剥离: 意识丧失（GCS≤8）."""
        from modules.emergency_triage import _keyword_keys
        assert "意识丧失" in _keyword_keys("意识丧失（GCS≤8）")

    def test_gcs_vital_range_match(self):
        """GCS 9-13 → II 级 (意识改变)."""
        result = _triage("乏力", {"SpO2": 97, "SBP": 130, "GCS": 11})
        assert _level(result) == "II"

    def test_sbp_vital_match(self):
        """收缩压<90mmHg → II 级."""
        result = _triage("乏力", {"SpO2": 97, "SBP": 85})
        assert _level(result) == "II"

    def test_hr_vital_match(self):
        """HR>150或<40 → II 级."""
        result = _triage("乏力", {"SpO2": 97, "SBP": 130, "HR": 160})
        assert _level(result) == "II"

    def test_high_fever_level2(self):
        """高热>41°C → II 级."""
        result = _triage("发热", {"SpO2": 97, "SBP": 130, "Temp": 41.5})
        assert _level(result) == "II"
