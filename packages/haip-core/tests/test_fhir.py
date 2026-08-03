"""Tests for haip.fhir — FHIR R4 API endpoints."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root / "packages" / "haip-core"))
sys.path.insert(0, str(project_root / "packages" / "haip-hospital"))

import pytest
from fastapi.testclient import TestClient

from haip.web_server import app

client = TestClient(app)


class TestFHIRMetadata:
    def test_capability_statement(self):
        r = client.get("/fhir/metadata")
        assert r.status_code == 200
        data = r.json()
        assert data["resourceType"] == "CapabilityStatement"
        assert data["fhirVersion"] == "4.0.1"


class TestFHIRPatient:
    def test_read_patient_by_id(self):
        r = client.get("/fhir/Patient/P001")
        assert r.status_code in (200, 404)

    def test_search_patient_by_name(self):
        r = client.get("/fhir/Patient", params={"name": "张"})
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            data = r.json()
            assert data["resourceType"] == "Bundle"

    def test_search_patient_by_gender(self):
        r = client.get("/fhir/Patient", params={"gender": "male"})
        assert r.status_code in (200, 404)

    def test_search_patient_by_id(self):
        r = client.get("/fhir/Patient", params={"_id": "P001"})
        assert r.status_code in (200, 404)


class TestFHIRObservation:
    def test_search_by_patient(self):
        r = client.get("/fhir/Observation", params={"patient": "P001"})
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            data = r.json()
            assert data["resourceType"] == "Bundle"

    def test_read_observation(self):
        r = client.get("/fhir/Observation/obs-001")
        assert r.status_code in (200, 404)


class TestFHIREncounter:
    def test_search_by_patient(self):
        r = client.get("/fhir/Encounter", params={"patient": "P001"})
        assert r.status_code in (200, 404)


class TestFHIRCondition:
    def test_search_by_patient(self):
        r = client.get("/fhir/Condition", params={"patient": "P001"})
        assert r.status_code in (200, 404)
