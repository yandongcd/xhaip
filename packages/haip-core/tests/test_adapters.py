"""Tests for haip.adapters — HIS adapter abstraction."""

import pytest
from haip.adapters import (
    MockHISAdapter,
    HISAdapterRegistry,
    PatientRecord,
    get_adapter_registry,
    get_his_adapter,
)
import inspect


class TestPatientRecord:
    def test_default_record(self):
        r = PatientRecord(patient_id="P001", name="张三")
        assert r.patient_id == "P001"
        assert r.name == "张三"
        assert r.height_cm == 0
        assert r.weight_kg == 0
        assert r.lab_results == {}
        assert r.medications == []
        assert r.allergies == []

    def test_record_with_data(self):
        r = PatientRecord(
            patient_id="P002",
            name="李四",
            gender="F",
            birth_date="1985-06-15",
            age=39,
            department="心内科",
            diagnosis="高血压",
            height_cm=165.0,
            weight_kg=60.0,
            bmi=22.0,
            lab_results={"血糖": 5.6},
            medications=[{"name": "氨氯地平", "dose": "5mg"}],
            allergies=[{"name": "青霉素", "severity": "severe"}],
        )
        assert r.birth_date == "1985-06-15"
        assert r.lab_results == {"血糖": 5.6}
        assert len(r.medications) == 1
        assert r.medications[0]["name"] == "氨氯地平"
        assert len(r.allergies) == 1
        assert r.allergies[0]["name"] == "青霉素"

    def test_record_with_lab_results_dict(self):
        r = PatientRecord(
            patient_id="P003",
            name="王五",
            lab_results={"Glucose": 5.6, "WBC": 7.2},
        )
        assert r.lab_results["Glucose"] == 5.6
        assert r.lab_results["WBC"] == 7.2


class TestMockHISAdapter:
    @pytest.fixture
    def adapter(self):
        return MockHISAdapter()

    def test_get_medications_returns_coroutine(self, adapter):
        result = adapter.get_medications("P001")
        # async method returns a coroutine when called synchronously
        assert inspect.iscoroutine(result)

    def test_get_allergies_returns_coroutine(self, adapter):
        result = adapter.get_allergies("P001")
        assert inspect.iscoroutine(result)

    def test_get_lab_results_returns_coroutine(self, adapter):
        result = adapter.get_lab_results("nonexistent")
        assert inspect.iscoroutine(result)

    def test_health_check_returns_coroutine(self, adapter):
        result = adapter.health_check()
        assert inspect.iscoroutine(result)


class TestHISAdapterRegistry:
    @pytest.fixture
    def registry(self):
        return HISAdapterRegistry()

    def test_register_and_get(self, registry):
        adapter = MockHISAdapter()
        registry.register("south", adapter)
        assert registry.get("south") is adapter

    def test_get_nonexistent_returns_fallback(self, registry):
        # HISAdapterRegistry.get always returns an adapter (auto-creates fallback)
        result = registry.get("nonexistent")
        assert isinstance(result, MockHISAdapter)

    def test_set_and_get_default(self, registry):
        adapter = MockHISAdapter()
        registry.set_default(adapter)
        result = registry.get("unknown_tenant")
        assert result is adapter

    def test_list_tenants(self, registry):
        registry.register("t1", MockHISAdapter())
        registry.register("t2", MockHISAdapter())
        tenants = registry.list_tenants()
        assert "t1" in tenants
        assert "t2" in tenants

    def test_registry_get_returns_registered_adapter(self):
        # get_his_adapter uses the global singleton. Test via registry directly.
        registry = HISAdapterRegistry()
        adapter = MockHISAdapter()
        registry.register("convenient", adapter)
        result = registry.get("convenient")
        assert result is adapter


class TestAdapterSingleton:
    def test_same_registry(self):
        r1 = get_adapter_registry()
        r2 = get_adapter_registry()
        assert r1 is r2
