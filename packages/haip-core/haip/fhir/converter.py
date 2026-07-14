"""FHIR Converter — xhaip internal data ↔ FHIR R4 resources.

Converts:
    - patients.json records → FHIR Patient / Observation / Encounter / Condition
    - Internal lab_results → FHIR Observation
    - Internal diagnosis → FHIR Condition
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from haip.fhir.models import (
    FHIRCodeableConcept,
    FHIRCondition,
    FHIREncounter,
    FHIRIdentifier,
    FHIRObservation,
    FHIRPatient,
    FHIRPeriod,
    FHIRQuantity,
    FHIRReference,
)

# Lab test LOINC code mappings
LOINC_MAP: dict[str, dict] = {
    "albumin": {"code": "1751-7", "display": "Albumin [Mass/volume] in Serum or Plasma", "unit": "g/L"},
    "crp": {"code": "1988-5", "display": "C reactive protein [Mass/volume] in Serum or Plasma", "unit": "mg/L"},
    "creatinine": {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma", "unit": "umol/L"},
    "hb": {"code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood", "unit": "g/L"},
    "troponin": {"code": "42757-9", "display": "Troponin I.cardiac [Mass/volume] in Serum or Plasma", "unit": "ng/mL"},
    "inr": {"code": "6301-6", "display": "INR in Blood by Coagulation assay", "unit": "{ratio}"},
    "glucose": {"code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma", "unit": "mmol/L"},
    "wbc": {"code": "26464-8", "display": "Leukocytes [#/volume] in Blood", "unit": "10*9/L"},
    "platelet": {"code": "26515-9", "display": "Platelets [#/volume] in Blood", "unit": "10*9/L"},
    "bun": {"code": "3094-0", "display": "Urea nitrogen [Mass/volume] in Serum or Plasma", "unit": "mmol/L"},
    "alt": {"code": "1742-6", "display": "Alanine aminotransferase [Enzymatic activity/volume]", "unit": "U/L"},
    "ast": {"code": "1920-8", "display": "Aspartate aminotransferase [Enzymatic activity/volume]", "unit": "U/L"},
    "total_bilirubin": {"code": "1975-2", "display": "Bilirubin.total [Mass/volume] in Serum or Plasma", "unit": "umol/L"},
    "sodium": {"code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma", "unit": "mmol/L"},
    "potassium": {"code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma", "unit": "mmol/L"},
    "calcium": {"code": "2000-8", "display": "Calcium [Mass/volume] in Serum or Plasma", "unit": "mmol/L"},
    "bmi": {"code": "39156-5", "display": "Body mass index (BMI) [Ratio]", "unit": "kg/m2"},
    "pt": {"code": "5902-2", "display": "Prothrombin time (PT)", "unit": "s"},
    "aptt": {"code": "3173-2", "display": "aPTT in Blood by Coagulation assay", "unit": "s"},
    "d_dimer": {"code": "48065-7", "display": "D dimer [Mass/volume] in Blood", "unit": "mg/L"},
    "lactate": {"code": "32693-4", "display": "Lactate [Moles/volume] in Blood", "unit": "mmol/L"},
    "pct": {"code": "33959-8", "display": "Procalcitonin [Mass/volume] in Serum", "unit": "ng/mL"},
    "ph": {"code": "2744-1", "display": "pH of Blood", "unit": "[pH]"},
    "pao2": {"code": "2703-7", "display": "Oxygen [Partial pressure] in Blood", "unit": "mmHg"},
    "paco2": {"code": "2019-8", "display": "Carbon dioxide [Partial pressure] in Blood", "unit": "mmHg"},
    "spo2": {"code": "2710-2", "display": "Oxygen saturation in Blood by Pulse oximetry", "unit": "%"},
}


def patient_to_fhir(patient: dict[str, Any], base_url: str = "http://localhost:8769/fhir") -> FHIRPatient:
    """Convert an xhaip patient record to FHIR Patient resource."""
    pid = patient.get("patient_id", "")
    return FHIRPatient(
        id=pid,
        identifier=[FHIRIdentifier(
            system=f"{base_url}/identifier/patient-id",
            value=pid,
        )],
        name=[{"text": patient.get("name", ""), "family": patient.get("name", "")[0] if patient.get("name") else ""}]
        if patient.get("name") else [],
        gender=_map_gender(patient.get("gender", "")),
        birthDate=_estimate_birthdate(patient.get("age", 0)),
    )


def lab_to_observations(
    patient_id: str,
    lab_results: dict[str, float],
    base_url: str = "http://localhost:8769/fhir",
) -> list[FHIRObservation]:
    """Convert lab results to FHIR Observation resources."""
    observations = []
    today = datetime.now().strftime("%Y-%m-%d")

    for test_name, value in lab_results.items():
        loinc = LOINC_MAP.get(test_name)
        if loinc is None:
            continue

        observations.append(FHIRObservation(
            id=f"obs-{patient_id}-{test_name}",
            status="final",
            code=FHIRCodeableConcept(
                coding=[{
                    "system": "http://loinc.org",
                    "code": loinc["code"],
                    "display": loinc["display"],
                }],
                text=test_name,
            ),
            subject=FHIRReference(reference=f"Patient/{patient_id}"),
            effectiveDateTime=today,
            valueQuantity=FHIRQuantity(
                value=float(value),
                unit=loinc["unit"],
                code=loinc["unit"],
            ),
        ))

    return observations


def diagnosis_to_condition(
    patient_id: str,
    diagnosis: str,
    base_url: str = "http://localhost:8769/fhir",
) -> FHIRCondition:
    """Convert a diagnosis string to FHIR Condition resource."""
    return FHIRCondition(
        id=f"cond-{patient_id}",
        subject=FHIRReference(reference=f"Patient/{patient_id}"),
        code=FHIRCodeableConcept(
            coding=[],  # ICD-10 coding would be added here in production
            text=diagnosis,
        ),
        clinicalStatus=FHIRCodeableConcept(
            coding=[{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active",
            }]
        ),
    )


def patient_to_encounter(
    patient: dict[str, Any],
    encounter_id: str = "",
    base_url: str = "http://localhost:8769/fhir",
) -> FHIREncounter:
    """Convert a patient record to FHIR Encounter."""
    pid = patient.get("patient_id", "")
    eid = encounter_id or f"enc-{pid}"
    today = datetime.now().strftime("%Y-%m-%d")

    return FHIREncounter(
        id=eid,
        status="finished",
        subject=FHIRReference(reference=f"Patient/{pid}"),
        period=FHIRPeriod(start=today, end=""),
        reasonCode=[FHIRCodeableConcept(
            text=patient.get("diagnosis", ""),
        )],
        diagnosis=[{
            "condition": {"reference": f"Condition/cond-{pid}"},
            "rank": 1,
        }],
    )


def _map_gender(gender_str: str) -> str:
    g = gender_str.upper()
    if g in ("M", "男"):
        return "male"
    if g in ("F", "女"):
        return "female"
    return "unknown"


def _estimate_birthdate(age: int) -> str:
    if age <= 0:
        return ""
    year = datetime.now().year - age
    return f"{year}-01-01"


def patient_bundle_to_fhir(
    patients: list[dict[str, Any]],
    include_observations: bool = True,
    include_conditions: bool = True,
    base_url: str = "http://localhost:8769/fhir",
) -> dict[str, Any]:
    """Convert a batch of patients to a FHIR Bundle response."""
    entries = []

    for p in patients:
        fhir_patient = patient_to_fhir(p, base_url)
        entries.append({"resource": fhir_patient.model_dump()})

        if include_observations:
            labs = p.get("lab_results", {})
            for obs in lab_to_observations(p.get("patient_id", ""), labs, base_url):
                entries.append({"resource": obs.model_dump()})

        if include_conditions:
            diag = p.get("diagnosis", "")
            if diag:
                cond = diagnosis_to_condition(p.get("patient_id", ""), diag, base_url)
                entries.append({"resource": cond.model_dump()})

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(patients),
        "entry": entries,
    }
