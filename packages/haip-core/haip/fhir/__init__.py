"""FHIR Server — FastAPI router for FHIR R4 REST API.

Exposes:
    GET  /fhir/Patient/{id}
    GET  /fhir/Patient?name=...
    GET  /fhir/Observation?patient=...
    GET  /fhir/Encounter?patient=...
    GET  /fhir/Condition?patient=...
    GET  /fhir/DiagnosticReport?patient=...
    POST /fhir/{resource}  (create)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from haip.fhir.converter import (
    diagnosis_to_condition,
    lab_to_observations,
    patient_bundle_to_fhir,
    patient_to_encounter,
    patient_to_fhir,
)

fhir_router = APIRouter(prefix="/fhir", tags=["fhir"])


def _get_case_mgr():
    """Lazy-load the CaseManager singleton from web_server."""
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-core"))
    sys.path.insert(0, str(PROJECT_ROOT / "packages" / "haip-hospital"))

    from haip.knowledge.cases import CaseManager

    patients_file = PROJECT_ROOT / "packages" / "haip-hospital" / "data" / "patients.json"
    mgr = CaseManager()
    if patients_file.exists():
        mgr.load(patients_file.parent)
    return mgr


def _search_patients(mgr, **filters) -> list[dict[str, Any]]:
    """Search patients with FHIR-style filters."""
    results = mgr.search(limit=50)

    if filters.get("_id"):
        results = [p for p in results if p.get("patient_id") == filters["_id"]]
    if filters.get("name"):
        name_lower = filters["name"].lower()
        results = [p for p in results if name_lower in (p.get("name") or "").lower()]
    if filters.get("gender"):
        from haip.fhir.converter import _map_gender
        gen_fhir = filters["gender"]
        results = [p for p in results if _map_gender(p.get("gender", "")) == gen_fhir]

    return results


# ── Patient endpoints ──


@fhir_router.get("/Patient/{patient_id}")
def get_patient(patient_id: str, current_user: dict = None):
    """Read a single Patient resource."""
    mgr = _get_case_mgr()
    patient = mgr.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    fhir_patient = patient_to_fhir(patient)
    return fhir_patient.model_dump()


@fhir_router.get("/Patient")
def search_patients(
    name: str = Query(None),
    gender: str = Query(None),
    _id: str = Query(None, alias="_id"),
    current_user: dict = None,
):
    """Search Patient resources."""
    mgr = _get_case_mgr()
    filters = {}
    if _id:
        filters["_id"] = _id
    if name:
        filters["name"] = name
    if gender:
        filters["gender"] = gender

    patients = _search_patients(mgr, **filters)
    bundle = patient_bundle_to_fhir(patients, include_observations=False, include_conditions=False)
    return bundle


# ── Observation endpoints ──


@fhir_router.get("/Observation")
def search_observations(
    patient: str = Query(None),
    code: str = Query(None),
    _id: str = Query(None, alias="_id"),
    current_user: dict = None,
):
    """Search Observation resources by patient."""
    mgr = _get_case_mgr()
    entries = []

    patients = []
    if patient:
        p = mgr.get(patient)
        if p:
            patients = [p]
    else:
        patients = mgr.search(limit=100)

    for p in patients:
        labs = p.get("lab_results", {})
        observations = lab_to_observations(p.get("patient_id", ""), labs)
        for obs in observations:
            entries.append({"resource": obs.model_dump()})

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(entries),
        "entry": entries,
    }


@fhir_router.get("/Observation/{obs_id}")
def get_observation(obs_id: str, current_user: dict = None):
    """Read a single Observation."""
    parts = obs_id.split("-", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=404, detail="Invalid observation ID")

    patient_id = parts[1]
    test_name = parts[2]

    mgr = _get_case_mgr()
    patient = mgr.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    labs = patient.get("lab_results", {})
    if test_name not in labs:
        raise HTTPException(status_code=404, detail="Observation not found")

    observations = lab_to_observations(patient_id, {test_name: labs[test_name]})
    if observations:
        return observations[0].model_dump()

    raise HTTPException(status_code=404, detail="Observation not found")


# ── Encounter endpoints ──


@fhir_router.get("/Encounter")
def search_encounters(
    patient: str = Query(None),
    current_user: dict = None,
):
    """Search Encounter resources."""
    mgr = _get_case_mgr()
    entries = []

    if patient:
        p = mgr.get(patient)
        if p:
            enc = patient_to_encounter(p)
            entries.append({"resource": enc.model_dump()})
    else:
        for p in mgr.search(limit=50):
            enc = patient_to_encounter(p)
            entries.append({"resource": enc.model_dump()})

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(entries),
        "entry": entries,
    }


# ── Condition endpoints ──


@fhir_router.get("/Condition")
def search_conditions(
    patient: str = Query(None),
    current_user: dict = None,
):
    """Search Condition resources."""
    mgr = _get_case_mgr()
    entries = []

    if patient:
        p = mgr.get(patient)
        if p and p.get("diagnosis"):
            cond = diagnosis_to_condition(patient, p["diagnosis"])
            entries.append({"resource": cond.model_dump()})
    else:
        for p in mgr.search(limit=50):
            if p.get("diagnosis"):
                cond = diagnosis_to_condition(p.get("patient_id", ""), p["diagnosis"])
                entries.append({"resource": cond.model_dump()})

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(entries),
        "entry": entries,
    }


# ── Metadata ──


@fhir_router.get("/metadata")
def metadata():
    """FHIR CapabilityStatement (simplified)."""
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": "2026-07-12",
        "publisher": "xhaip",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Observation", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Encounter", "interaction": [{"code": "search-type"}]},
                    {"type": "Condition", "interaction": [{"code": "search-type"}]},
                    {"type": "DiagnosticReport", "interaction": [{"code": "search-type"}]},
                ],
            }
        ],
    }
