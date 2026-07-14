"""Data validation module — validate patient data quality and integrity.

Provides:
    - Required field validation
    - Type checking
    - Range checking
    - Data quality scoring
    - Integration with existing validate_patients.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Result of a data validation run."""

    total_records: int = 0
    passed: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_blocking(self) -> bool:
        """Check if there are blocking errors (total failure)."""
        return self.failed > 0 and self.passed == 0

    @property
    def quality_score(self) -> float:
        """Calculate data quality score (0.0 - 1.0)."""
        if self.total_records == 0:
            return 0.0
        return self.passed / self.total_records


# Required fields per data type
REQUIRED_PATIENT_FIELDS = {"patient_id", "age", "gender", "department", "diagnosis"}
OPTIONAL_PATIENT_FIELDS = {"name", "weight_kg", "height_cm", "lab_results", "compatible_agents", "provenance"}
VALID_GENDERS = {"M", "F", "男", "女"}

# Valid age range
MIN_AGE = 0
MAX_AGE = 150

# Lab value ranges (sanity checks)
LAB_RANGES: dict[str, tuple[float, float]] = {
    "albumin": (5, 80),        # g/L
    "crp": (0, 500),           # mg/L
    "creatinine": (10, 2000),  # umol/L
    "hb": (20, 250),           # g/L
    "troponin": (0, 100),      # ng/mL
    "inr": (0.5, 20),          # ratio
    "glucose": (1, 50),        # mmol/L
    "wbc": (0, 100),           # 10^9/L
    "platelet": (0, 2000),     # 10^9/L
    "bmi": (5, 80),            # kg/m2
    "spo2": (30, 100),         # %
    "ph": (6.5, 8.0),          # pH
    "paco2": (10, 200),        # mmHg
    "pao2": (20, 800),         # mmHg
}


def validate_patient(patient: dict[str, Any], index: int = 0) -> list[dict[str, Any]]:
    """Validate a single patient record. Returns list of errors found."""
    errors = []
    pid = patient.get("patient_id", f"index-{index}")

    # Required fields
    for rf in REQUIRED_PATIENT_FIELDS:
        if rf not in patient or patient[rf] is None:
            errors.append({
                "patient_id": pid,
                "field": rf,
                "error": f"Missing required field: {rf}",
                "severity": "error",
            })

    # Gender validation
    gender = patient.get("gender", "")
    if gender and gender not in VALID_GENDERS:
        errors.append({
            "patient_id": pid,
            "field": "gender",
            "error": f"Invalid gender: {gender}, expected M/F/男/女",
            "severity": "warning",
        })

    # Age validation
    age = patient.get("age", patient.get("age_months"))
    if age is not None and (age < MIN_AGE or age > MAX_AGE):
        errors.append({
            "patient_id": pid,
            "field": "age",
            "error": f"Age out of range: {age} (valid: {MIN_AGE}-{MAX_AGE})",
            "severity": "error",
        })

    # Lab value validation
    lab_results = patient.get("lab_results", {})
    for test_name, value in lab_results.items():
        if test_name in LAB_RANGES:
            low, high = LAB_RANGES[test_name]
            if value is not None:
                try:
                    v = float(value)
                    if v < low or v > high:
                        errors.append({
                            "patient_id": pid,
                            "field": f"lab_results.{test_name}",
                            "error": f"Lab value out of range: {test_name}={v} (valid: {low}-{high})",
                            "severity": "warning",
                        })
                except (ValueError, TypeError):
                    errors.append({
                        "patient_id": pid,
                        "field": f"lab_results.{test_name}",
                        "error": f"Invalid lab value: {test_name}={value}",
                        "severity": "error",
                    })

    return errors


def validate_patients(
    patients: list[dict[str, Any]],
    strict: bool = False,
) -> ValidationResult:
    """Validate a list of patient records.

    Args:
        patients: List of patient records.
        strict: If True, warnings are treated as errors.

    Returns:
        ValidationResult with pass/fail counts and error details.
    """
    result = ValidationResult(total_records=len(patients))

    for i, patient in enumerate(patients):
        errors = validate_patient(patient, i)
        has_errors = any(e["severity"] == "error" for e in errors)
        has_warnings = any(e["severity"] == "warning" for e in errors)

        if has_errors or (strict and has_warnings):
            result.failed += 1
            result.errors.extend(errors)
        else:
            result.passed += 1
            if has_warnings:
                result.warnings.extend(errors)

    return result


def validate_patients_file(filepath: str, strict: bool = False) -> ValidationResult:
    """Validate a patients.json file.

    Args:
        filepath: Path to the patients.json file.
        strict: If True, warnings are treated as errors.

    Returns:
        ValidationResult.
    """
    import json
    from pathlib import Path

    path = Path(filepath)
    if not path.exists():
        return ValidationResult(errors=[{
            "patient_id": "N/A",
            "field": "file",
            "error": f"File not found: {filepath}",
            "severity": "error",
        }])

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult(errors=[{
            "patient_id": "N/A",
            "field": "file",
            "error": f"Invalid JSON: {e}",
            "severity": "error",
        }])

    patients = data.get("patients", data if isinstance(data, list) else [])
    return validate_patients(patients, strict=strict)
