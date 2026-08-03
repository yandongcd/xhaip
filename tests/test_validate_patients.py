"""validate_patients.py 校验逻辑单元测试 (T1: 数据质量护栏)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS.resolve()))

from validate_patients import (  # noqa: E402
    check_date_consistency,
    check_gender_diagnosis,
    check_lab_fields,
    check_provenance,
    check_template_residue,
)


def _patient(**overrides) -> dict:
    base = {
        "patient_id": "P001",
        "gender": "F",
        "diagnosis": "高血压",
        "provenance": {"source": "synthetic", "institution": "xhaip_patient_generator"},
    }
    base.update(overrides)
    return base


class TestCheckGenderDiagnosis:
    def test_female_only_diagnosis_on_male_fails(self):
        level, msg = check_gender_diagnosis(_patient(gender="M", diagnosis="子宫肌瘤"))
        assert level == "fail"
        assert "female-only" in msg

    def test_ok_diagnosis_passes(self):
        level, _ = check_gender_diagnosis(_patient(gender="M", diagnosis="高血压"))
        assert level == "pass"

    def test_no_gender_warns(self):
        level, msg = check_gender_diagnosis(_patient(gender="", diagnosis="高血压"))
        assert level in ("warn", "pass")


class TestCheckProvenance:
    def test_missing_provenance_warns(self):
        level, msg = check_provenance(_patient(provenance=None))
        assert level == "warn"
        assert "provenance" in msg.lower() or "Missing" in msg

    def test_provenance_without_source_warns(self):
        level, msg = check_provenance(_patient(provenance={"institution": "x"}))
        assert level == "warn"

    def test_complete_provenance_passes(self):
        level, _ = check_provenance(_patient(
            provenance={"source": "synthetic", "origin_repo": "xhaip_v1.0",
                        "institution": "xhaip_patient_generator"}))
        assert level == "pass"


class TestCheckTemplateResidue:
    def test_oncology_residue_warns(self):
        patient = _patient(diagnosis="高血压", treatment_plan="行化疗方案治疗")
        level, msg = check_template_residue(patient)
        assert level == "warn"
        assert "化疗方案" in msg

    def test_cancer_patient_no_warning(self):
        patient = _patient(diagnosis="肺癌", treatment_plan="行化疗方案治疗")
        level, _ = check_template_residue(patient)
        assert level == "pass"


class TestCheckLabFields:
    def test_missing_lab_results_passes(self):
        level, _ = check_lab_fields(_patient())
        assert level in ("pass", "warn")


class TestCheckDateConsistency:
    def test_missing_dates_passes(self):
        level, _ = check_date_consistency(_patient())
        assert level in ("pass", "warn")


class TestProductionData:
    """对真实患者数据的冒烟校验 — provenance 覆盖率护栏。"""

    def test_all_patients_have_provenance(self):
        data_file = SCRIPTS.parent / "packages" / "haip-hospital" / "data" / "patients.json"
        data = json.loads(data_file.read_text(encoding="utf-8"))
        patients = data["patients"]
        assert len(patients) > 1000
        missing = [p["patient_id"] for p in patients if "provenance" not in p]
        assert not missing, f"{len(missing)} patients missing provenance"
