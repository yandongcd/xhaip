"""Tests for Sprint 6: Data Product Adapter."""

import pytest

from haip.data import (
    DataProduct, DataSourceAdapter, SQLiteDataSource, MockDataSource,
    DataProductRegistry, get_registry,
)


class TestDataSources:
    def test_mock_source_connect(self):
        ds = MockDataSource([{"id": 1, "name": "test"}])
        ds.connect()
        assert ds._connected is True

    def test_mock_source_query(self):
        ds = MockDataSource([
            {"patient_id": "P001", "name": "张三"},
            {"patient_id": "P002", "name": "李四"},
        ])
        results = ds.query({"patient_id": "P001"})
        assert len(results) == 1
        assert results[0]["name"] == "张三"

    def test_mock_source_empty(self):
        ds = MockDataSource()
        results = ds.query({"key": "val"})
        assert results == []

    def test_sqlite_source_basic(self):
        ds = SQLiteDataSource(":memory:", table="test")
        ds.connect()
        ds._conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        ds._conn.execute("INSERT INTO test VALUES (1, 'hello')")
        ds._conn.commit()
        results = ds.query({"id": 1})
        assert len(results) == 1
        assert results[0]["name"] == "hello"
        ds.close()


class TestDataProduct:
    def test_basic(self):
        dp = DataProduct(name="DP-HIS-PATIENT", security_label="SENSITIVE")
        assert dp.name == "DP-HIS-PATIENT"
        assert dp.security_label == "SENSITIVE"

    def test_query_with_adapter(self):
        ds = MockDataSource([{"id": 1}])
        dp = DataProduct(name="test", adapter=ds)
        results = dp.query({"id": 1})
        assert len(results) == 1

    def test_query_no_adapter(self):
        dp = DataProduct(name="test")
        assert dp.query() == []

    def test_schema(self):
        ds = MockDataSource([{"id": 1}])
        dp = DataProduct(name="test", adapter=ds)
        s = dp.get_schema()
        assert s["type"] == "mock"


class TestRegistry:
    def test_register_and_get(self):
        reg = DataProductRegistry()
        dp = DataProduct(name="DP-HIS-PATIENT")
        reg.register(dp)
        assert reg.get("DP-HIS-PATIENT") is dp
        assert reg.get("nonexistent") is None

    def test_seed_defaults(self):
        reg = DataProductRegistry()
        reg.seed_defaults()
        products = reg.list_all()
        assert "DP-HIS-PATIENT" in products
        assert "DP-LIS-LAB" in products
        assert "DP-EMR-NOTE" in products
        assert len(products) == 11

    def test_list_by_department(self):
        reg = DataProductRegistry()
        reg.seed_defaults()
        nursing = reg.list_by_department("护理部")
        assert len(nursing) == 2

    def test_list_by_security(self):
        reg = DataProductRegistry()
        reg.seed_defaults()
        normal = reg.list_by_security("NORMAL")
        assert any(p.name == "DP-NIS-VITAL" for p in normal)

    def test_restricted_excluded(self):
        reg = DataProductRegistry()
        reg.seed_defaults()
        normal = reg.list_by_security("NORMAL")
        restricted_names = {p.name for p in normal}
        assert "DP-EMR-NOTE" not in restricted_names  # RESTRICTED


class TestGlobalRegistry:
    def test_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_pre_seeded(self):
        reg = get_registry()
        assert reg.get("DP-HIS-PATIENT") is not None
