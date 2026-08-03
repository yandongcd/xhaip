"""HIS Adapter abstraction layer — pluggable integration with hospital IT systems.

Architecture:
    HISAdapter (ABC)
    ├── FHIRAdapter      — Standard FHIR R4 endpoint
    ├── HL7v2Adapter     — MLLP/TCP HL7 v2 messaging
    ├── RestHISAdapter   — REST API (custom HIS endpoints)
    └── MockHISAdapter   — Development/testing fallback

Each adapter normalizes data into a common PatientRecord format.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PatientRecord:
    """Normalized patient record from any HIS adapter."""

    patient_id: str
    name: str = ""
    gender: str = ""
    birth_date: str = ""
    age: int = 0
    department: str = ""
    diagnosis: str = ""
    admission_date: str = ""
    discharge_date: str = ""

    # Vital signs
    height_cm: float = 0
    weight_kg: float = 0
    bmi: float = 0

    # Lab results (key: test_name, value: numeric)
    lab_results: dict[str, float] = field(default_factory=dict)

    # Medications
    medications: list[dict[str, Any]] = field(default_factory=list)

    # Allergies
    allergies: list[dict[str, Any]] = field(default_factory=list)

    # Raw source data (for debugging)
    source_data: dict[str, Any] = field(default_factory=dict)
    source_system: str = ""


class HISAdapter(ABC):
    """Abstract base for all HIS adapter implementations.

    Subclasses implement a specific integration protocol (FHIR, HL7 v2, REST, etc.)
    and normalize data into PatientRecord format.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    async def get_patient(self, patient_id: str) -> PatientRecord | None:
        """Retrieve a single patient."""
        ...

    @abstractmethod
    async def search_patients(
        self,
        name: str = "",
        department: str = "",
        limit: int = 50,
    ) -> list[PatientRecord]:
        """Search for patients."""
        ...

    @abstractmethod
    async def get_lab_results(self, patient_id: str) -> dict[str, float]:
        """Get lab results for a patient."""
        ...

    async def get_medications(self, patient_id: str) -> list[dict[str, Any]]:
        """Get current medications for a patient (optional)."""
        return []

    async def get_allergies(self, patient_id: str) -> list[dict[str, Any]]:
        """Get allergies for a patient (optional)."""
        return []

    async def health_check(self) -> bool:
        """Check if the HIS system is reachable (optional)."""
        return True


class MockHISAdapter(HISAdapter):
    """Mock HIS adapter for development and testing.

    Uses the built-in patients.json as the data source.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._patients: dict[str, PatientRecord] = {}
        self._load_mock_data()

    def _load_mock_data(self):
        """Load patients from the built-in JSON data."""
        import json
        from pathlib import Path

        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent / "packages" / "haip-hospital" / "data" / "patients.json",
            Path("packages/haip-hospital/data/patients.json"),
        ]
        for path in candidates:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    patients = data.get("patients", data if isinstance(data, list) else [])
                    for p in patients:
                        record = self._convert_to_record(p)
                        self._patients[record.patient_id] = record
                except Exception:
                    logger.debug("Mock HIS 数据加载失败: %s", path, exc_info=True)
                break

    def _convert_to_record(self, p: dict[str, Any]) -> PatientRecord:
        return PatientRecord(
            patient_id=p.get("patient_id", ""),
            name=p.get("name", ""),
            gender=p.get("gender", ""),
            age=p.get("age", 0),
            department=p.get("department", ""),
            diagnosis=p.get("diagnosis", ""),
            height_cm=p.get("height_cm", 0),
            weight_kg=p.get("weight_kg", 0),
            lab_results=p.get("lab_results", {}),
            medications=p.get("medications", []),
            allergies=p.get("allergies", []),
            source_data=p,
            source_system="mock-his",
        )

    async def get_patient(self, patient_id: str) -> PatientRecord | None:
        return self._patients.get(patient_id)

    async def search_patients(
        self,
        name: str = "",
        department: str = "",
        limit: int = 50,
    ) -> list[PatientRecord]:
        results = []
        for record in self._patients.values():
            if name and name.lower() not in record.name.lower():
                continue
            if department and department != record.department:
                continue
            results.append(record)
            if len(results) >= limit:
                break
        return results

    async def get_lab_results(self, patient_id: str) -> dict[str, float]:
        patient = self._patients.get(patient_id)
        return patient.lab_results if patient else {}

    async def health_check(self) -> bool:
        return len(self._patients) > 0


# ── Adapter Registry ──


class HISAdapterRegistry:
    """Registry for HIS adapters — one per hospital/tenant."""

    def __init__(self):
        self._adapters: dict[str, HISAdapter] = {}
        self._default: HISAdapter | None = None

    def register(self, tenant_id: str, adapter: HISAdapter):
        self._adapters[tenant_id] = adapter

    def set_default(self, adapter: HISAdapter):
        self._default = adapter

    def get(self, tenant_id: str = "") -> HISAdapter:
        """Get the adapter for a tenant, or the default."""
        if tenant_id and tenant_id in self._adapters:
            return self._adapters[tenant_id]
        if self._default:
            return self._default
        # Auto-create fallback
        self._default = MockHISAdapter()
        return self._default

    def list_tenants(self) -> list[str]:
        return list(self._adapters.keys())


# Global registry
_adapter_registry = HISAdapterRegistry()


def get_adapter_registry() -> HISAdapterRegistry:
    """Get the global HIS adapter registry."""
    return _adapter_registry


def get_his_adapter(tenant_id: str = "") -> HISAdapter:
    """Get the HIS adapter for the given tenant."""
    return _adapter_registry.get(tenant_id)
