"""Tests for haip.data — Data Product adapter layer."""

import tempfile
from pathlib import Path

import pytest

from haip.data import (
    DataProduct,
    DataProductRegistry,
    DataSourceAdapter,
    MockDataSource,
    SQLiteDataSource,
    get_registry,
)


class TestSQLiteDataSource:
    def test_connect_and_query(self):
        ds = SQLiteDataSource(db_path=":memory:", table="test")
        ds.connect()
        ds._conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        ds._conn.execute("INSERT INTO test VALUES (1, '张三')")
        results = ds.query({"name": "张三"})
        assert len(results) == 1
        assert results[0]["name"] == "张三"
        ds.close()

    def test_query_empty_params(self):
        ds = SQLiteDataSource(db_path=":memory:", table="test")
        ds.connect()
        ds._conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        ds._conn.execute("INSERT INTO test VALUES (1, 'A'), (2, 'B')")
        results = ds.query({})
        assert len(results) == 2
        ds.close()

    def test_query_auto_connects_when_not_connected(self):
        # Use a file-based db so the table persists after close/reconnect
        db_path = tempfile.mktemp(suffix=".db")
        try:
            ds = SQLiteDataSource(db_path=db_path, table="test")
            ds.connect()
            ds._conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            ds._conn.execute("INSERT INTO test VALUES (1, 'X')")
            ds._conn.commit()
            ds.close()
            # Now _conn is None — query() calls connect() automatically
            results = ds.query({})
            assert len(results) == 1
            assert results[0]["name"] == "X"
            ds.close()
        finally:
            Path(db_path).unlink(missing_ok=True)


class TestMockDataSource:
    def test_mock_returns_fixture(self):
        ds = MockDataSource(data=[{"id": 1, "name": "测试"}])
        results = ds.query({})
        assert len(results) == 1
        assert results[0]["name"] == "测试"

    def test_mock_filters_by_params(self):
        ds = MockDataSource(data=[
            {"id": 1, "name": "张三", "dept": "内科"},
            {"id": 2, "name": "李四", "dept": "外科"},
        ])
        results = ds.query({"dept": "内科"})
        assert len(results) == 1
        assert results[0]["name"] == "张三"


class TestDataProduct:
    def test_query_delegates_to_adapter(self):
        ds = MockDataSource(data=[{"lab": "血糖", "value": "5.6"}])
        dp = DataProduct(
            name="LAB-GLUCOSE",
            description="血糖结果",
            security_label="SENSITIVE",
            owner_department="检验科",
            adapter=ds,
        )
        # MockDataSource filters by params, so pass empty to get all
        results = dp.query({})
        assert results[0]["value"] == "5.6"

    def test_get_schema_from_adapter(self):
        ds = MockDataSource(data=[{"lab": "血糖", "value": "5.6"}])
        dp = DataProduct(
            name="LAB-GLUCOSE",
            description="血糖结果",
            security_label="SENSITIVE",
            owner_department="检验科",
            field_schema={"lab": "str", "value": "str"},
            adapter=ds,
        )
        schema = dp.get_schema()
        # get_schema() returns adapter.schema(), not the field_schema directly
        assert schema["type"] == "mock"
        assert schema["count"] == 1

    def test_get_schema_no_adapter_returns_field_schema(self):
        dp = DataProduct(
            name="TEST",
            description="d",
            security_label="NORMAL",
            owner_department="D",
            field_schema={"lab": "str"},
        )
        schema = dp.get_schema()
        assert "lab" in schema


class TestDataProductRegistry:
    @pytest.fixture
    def registry(self):
        r = DataProductRegistry()
        ds = MockDataSource(data=[{"id": 1}])
        dp = DataProduct(
            name="DP-TEST",
            description="测试数据产品",
            security_label="NORMAL",
            owner_department="测试科",
            adapter=ds,
        )
        r.register(dp)
        return r

    def test_register_and_get(self, registry):
        dp = registry.get("DP-TEST")
        assert dp is not None
        assert dp.name == "DP-TEST"

    def test_get_nonexistent(self, registry):
        assert registry.get("NONEXISTENT") is None

    def test_list_all(self, registry):
        all_dp = registry.list_all()
        assert len(all_dp) >= 1

    def test_list_by_department(self, registry):
        dept_dp = registry.list_by_department("测试科")
        assert len(dept_dp) >= 1

    def test_list_by_department_none(self, registry):
        assert registry.list_by_department("不存在的科室") == []

    def test_list_by_security(self, registry):
        normal_dp = registry.list_by_security("NORMAL")
        assert len(normal_dp) >= 1

    def test_seed_defaults(self, registry):
        registry.seed_defaults()
        assert len(registry.list_all()) >= 10  # 11 default products + 1 test


class TestDataProductSingleton:
    def test_same_registry(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2
