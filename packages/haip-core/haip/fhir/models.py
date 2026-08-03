"""FHIR R4 Server — models, conversion, and API for healthcare interoperability.

Supports:
    - Patient, Observation, Encounter, MedicationRequest resources
    - Search API (FHIR Search parameters)
    - Conversion between xhaip internal format and FHIR R4 JSON
    - FastAPI router for /fhir/ endpoints
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── FHIR Resource Models (partial R4) ──


class FHIRIdentifier(BaseModel):
    system: str = ""
    value: str = ""


class FHIRCodeableConcept(BaseModel):
    coding: list[dict] = Field(default_factory=list)
    text: str = ""


class FHIRReference(BaseModel):
    reference: str = ""
    display: str = ""


class FHIRPeriod(BaseModel):
    start: str = ""
    end: str = ""


class FHIRQuantity(BaseModel):
    value: float = 0.0
    unit: str = ""
    system: str = "http://unitsofmeasure.org"
    code: str = ""


class FHIRPatient(BaseModel):
    resourceType: str = "Patient"
    id: str = ""
    identifier: list[FHIRIdentifier] = Field(default_factory=list)
    name: list[dict] = Field(default_factory=list)
    gender: str = ""  # male | female | other | unknown
    birthDate: str = ""
    address: list[dict] = Field(default_factory=list)
    telecom: list[dict] = Field(default_factory=list)


class FHIRObservation(BaseModel):
    resourceType: str = "Observation"
    id: str = ""
    status: str = "final"
    code: FHIRCodeableConcept = Field(default_factory=FHIRCodeableConcept)
    subject: FHIRReference = Field(default_factory=FHIRReference)
    effectiveDateTime: str = ""
    valueQuantity: FHIRQuantity | None = None
    valueString: str | None = None
    interpretation: list[FHIRCodeableConcept] = Field(default_factory=list)
    referenceRange: list[dict] = Field(default_factory=list)


class FHIREncounter(BaseModel):
    resourceType: str = "Encounter"
    id: str = ""
    status: str = "finished"
    subject: FHIRReference = Field(default_factory=FHIRReference)
    period: FHIRPeriod = Field(default_factory=FHIRPeriod)
    reasonCode: list[FHIRCodeableConcept] = Field(default_factory=list)
    diagnosis: list[dict] = Field(default_factory=list)


class FHIRMedicationRequest(BaseModel):
    resourceType: str = "MedicationRequest"
    id: str = ""
    status: str = "active"
    intent: str = "order"
    subject: FHIRReference = Field(default_factory=FHIRReference)
    medicationCodeableConcept: FHIRCodeableConcept = Field(default_factory=FHIRCodeableConcept)
    dosageInstruction: list[dict] = Field(default_factory=list)


class FHIRCondition(BaseModel):
    resourceType: str = "Condition"
    id: str = ""
    subject: FHIRReference = Field(default_factory=FHIRReference)
    code: FHIRCodeableConcept = Field(default_factory=FHIRCodeableConcept)
    clinicalStatus: FHIRCodeableConcept = Field(default_factory=FHIRCodeableConcept)


class FHIRDiagnosticReport(BaseModel):
    resourceType: str = "DiagnosticReport"
    id: str = ""
    status: str = "final"
    subject: FHIRReference = Field(default_factory=FHIRReference)
    code: FHIRCodeableConcept = Field(default_factory=FHIRCodeableConcept)
    effectiveDateTime: str = ""
    result: list[FHIRReference] = Field(default_factory=list)


class FHIRBundle(BaseModel):
    resourceType: str = "Bundle"
    type: str = "searchset"
    total: int = 0
    entry: list[dict] = Field(default_factory=list)


# ── Resource type mapping ──

FHIR_RESOURCE_CLASSES: dict[str, type[BaseModel]] = {
    "Patient": FHIRPatient,
    "Observation": FHIRObservation,
    "Encounter": FHIREncounter,
    "MedicationRequest": FHIRMedicationRequest,
    "Condition": FHIRCondition,
    "DiagnosticReport": FHIRDiagnosticReport,
}

# Search parameter names valid for each resource type
FHIR_SEARCH_PARAMS: dict[str, set[str]] = {
    "Patient": {"_id", "name", "birthdate", "gender", "identifier"},
    "Observation": {"_id", "patient", "code", "date", "status"},
    "Encounter": {"_id", "patient", "date", "status", "type"},
    "MedicationRequest": {"_id", "patient", "status", "medication"},
    "Condition": {"_id", "patient", "code", "clinical-status"},
    "DiagnosticReport": {"_id", "patient", "code", "date", "status"},
}
