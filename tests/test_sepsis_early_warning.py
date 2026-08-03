"""sepsis_early_warning — C5 数据源错位回归测试.

覆盖 (P0-2 修复):
  - qSOFA/NLR 从 vital_signs 大写键读取 (SpO2/SBP/HR/Temp/GCS/RR/NEUT/LYMPH),
    lab_results 兜底, kwargs vital_signs 优先
  - 真实患者 (P374) 上 NLR 由 lab_results ANC 兜底计算为非默认值
  - 数据缺失时回退默认值且不报错
"""

from __future__ import annotations

from modules.sepsis_early_warning import immune_status, sepsis_score


class TestQsofaDataSource:
    def test_qsofa_from_kwargs_vital_signs(self):
        """vital_signs 大写键 → qSOFA 非默认 (3/3)."""
        r = sepsis_score(patient_id="P001", vital_signs={"RR": 24, "SBP": 95, "GCS": 13})
        assert r["status"] == "ok"
        assert r["qsofa"] == 3

    def test_qsofa_partial_from_vital_signs(self):
        r = sepsis_score(patient_id="P001", vital_signs={"RR": 25, "SBP": 120, "GCS": 15})
        assert r["qsofa"] == 1

    def test_qsofa_lowercase_keys(self):
        """小写键 (respiratory_rate/sbp/gcs) 兼容."""
        r = sepsis_score(patient_id="P001",
                         vital_signs={"respiratory_rate": 24, "sbp": 90, "gcs": 14})
        assert r["qsofa"] == 3

    def test_qsofa_defaults_when_missing(self):
        """无任何数据 → 默认值 (qSOFA 0), 不报错."""
        r = sepsis_score(patient_id="P001")
        assert r["status"] == "ok"
        assert r["qsofa"] == 0

    def test_pct_from_real_patient(self):
        """真实患者 P374: lab_results PCT=1.3 → 局部感染可能."""
        r = sepsis_score(patient_id="P374")
        assert r["pct"] == 1.3
        assert "局部感染" in r["pct_level"]


class TestNlrDataSource:
    def test_nlr_from_kwargs_vital_signs(self):
        """vital_signs 大写键 NEUT/LYMPH → NLR 非默认."""
        r = immune_status(patient_id="P001", vital_signs={"NEUT": 18, "LYMPH": 0.8})
        assert r["status"] == "ok"
        assert r["nlr"] == 22.5
        assert r["immune_status"] == "免疫低下"

    def test_nlr_from_real_patient_anc_fallback(self):
        """真实患者 P374: 无 NEUT/LYMPH, lab_results ANC=5.7 兜底 → NLR=3.8 (非默认)."""
        r = immune_status(patient_id="P374")
        assert r["nlr"] == 3.8
        assert r["nlr"] != 2.7  # 旧默认值 4.0/1.5 已不再被误用

    def test_nlr_defaults_when_missing(self):
        """无任何数据 → 默认值, 不报错."""
        r = immune_status(patient_id="P-NOT-EXIST")
        assert r["status"] == "ok"
        assert r["nlr"] == 2.7

    def test_nlr_lowercase_lab_keys(self):
        """patients_v2 风格小写 lab 键 (neutrophil/lymphocyte)."""
        r = immune_status(patient_id="P001", vital_signs={"neutrophil": 12, "lymphocyte": 2.0})
        assert r["nlr"] == 6.0
