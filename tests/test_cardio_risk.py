"""cardio_risk 高血压分级 — C3 临床正确性回归测试.

覆盖 (P0-2 修复):
  - 分支顺序 + 守卫修正: 145/80 → 1级(ISH), 160/90 → 2级, 150/100 → 2级,
    150/110 → 3级, 120/80 → 正常高值
  - 中文高血压防治指南 2024 分级 (按收缩/舒张较高档位定级)
"""

from __future__ import annotations

from modules.cardio_risk import _classify_bp, evaluate_htn


class TestClassifyBp:
    def test_145_80_ish_grade1(self):
        """单纯收缩期高血压: SBP 140-159 + DBP<90 → 1 级 ISH."""
        r = _classify_bp(145, 80)
        assert r["level"] == 1
        assert "ISH" in r["grade_cn"]

    def test_160_90_grade2(self):
        r = _classify_bp(160, 90)
        assert r["level"] == 2
        assert r["grade"] == "2级"

    def test_150_100_grade2(self):
        """SBP 1 级档但 DBP 2 级档 → 按较高档位 2 级."""
        r = _classify_bp(150, 100)
        assert r["level"] == 2
        assert r["grade"] == "2级"

    def test_150_110_grade3(self):
        r = _classify_bp(150, 110)
        assert r["level"] == 3
        assert r["grade"] == "3级"

    def test_120_80_normal_high(self):
        r = _classify_bp(120, 80)
        assert r["level"] == 0
        assert r["grade"] == "正常高值"

    def test_110_75_normal(self):
        r = _classify_bp(110, 75)
        assert r["level"] == 0
        assert r["grade"] == "正常"

    def test_165_80_ish_grade2(self):
        """SBP 2 级档 + DBP<90 → 2 级 ISH."""
        r = _classify_bp(165, 80)
        assert r["level"] == 2
        assert "ISH" in r["grade_cn"]

    def test_185_75_ish_grade3(self):
        r = _classify_bp(185, 75)
        assert r["level"] == 3

    def test_140_90_grade1(self):
        r = _classify_bp(140, 90)
        assert r["level"] == 1
        assert r["grade"] == "1级"

    def test_139_89_normal_high(self):
        r = _classify_bp(139, 89)
        assert r["level"] == 0
        assert r["grade"] == "正常高值"


class TestEvaluateHtn:
    def test_evaluate_htn_145_80_level1(self):
        """真实患者 (P001) 端到端: 145/80 → 1 级 (ISH)."""
        r = evaluate_htn(patient_id="P001", sbp=145, dbp=80)
        assert r["status"] == "ok"
        assert r["bp_classification"]["level"] == 1
        assert "ISH" in r["bp_classification"]["grade_cn"]

    def test_evaluate_htn_160_90_level2(self):
        r = evaluate_htn(patient_id="P001", sbp=160, dbp=90)
        assert r["bp_classification"]["level"] == 2
