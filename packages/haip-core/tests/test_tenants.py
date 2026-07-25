"""Tests for haip.tenants — multi-tenant management."""

import pytest
from haip.tenants import (
    TenantManager,
    Tenant,
    TenantStatus,
    init_default_tenant,
    get_tenant_manager,
)


class TestTenantModel:
    def test_default_tenant(self):
        t = Tenant(id="t1", name="测试医院")
        assert t.name == "测试医院"
        assert t.id == "t1"
        assert t.status == TenantStatus.ACTIVE

    def test_tenant_with_id(self):
        t = Tenant(id="south", name="南方医院")
        assert t.id == "south"

    def test_tenant_status_enum(self):
        assert TenantStatus.ACTIVE.value == "active"
        assert TenantStatus.SUSPENDED.value == "suspended"
        assert TenantStatus.TRIAL.value == "trial"
        assert TenantStatus.EXPIRED.value == "expired"


class TestTenantManager:
    @pytest.fixture
    def mgr(self):
        return TenantManager()

    def test_create_tenant(self, mgr):
        t = mgr.create("南方医院", hospital_name="南方医院", tenant_id="south", hospital_code="NFYY")
        assert t.id == "south"
        assert t.status == TenantStatus.ACTIVE

    def test_get_tenant(self, mgr):
        mgr.create("中山医院", hospital_name="中山医院", tenant_id="zsyy")
        t = mgr.get("zsyy")
        assert t is not None
        assert t.name == "中山医院"

    def test_get_nonexistent(self, mgr):
        assert mgr.get("nonexistent") is None

    def test_list_active(self, mgr):
        mgr.create("A医院", hospital_name="A", tenant_id="a")
        mgr.create("B医院", hospital_name="B", tenant_id="b")
        active = mgr.list_active()
        assert len(active) >= 2

    def test_list_all(self, mgr):
        mgr.create("C医院", hospital_name="C", tenant_id="c")
        all_tenants = mgr.list_all()
        assert len(all_tenants) >= 1

    def test_suspend_and_reactivate(self, mgr):
        mgr.create("D医院", hospital_name="D", tenant_id="d")
        mgr.suspend("d")
        suspended = mgr.get("d")
        assert suspended.status == TenantStatus.SUSPENDED

        mgr.activate("d")
        active = mgr.get("d")
        assert active.status == TenantStatus.ACTIVE

    def test_is_feature_enabled(self, mgr):
        mgr.create("E医院", hospital_name="E", tenant_id="e", features={"pharmacy": True, "orthopedic": False})
        assert mgr.is_feature_enabled("e", "pharmacy") is True
        assert mgr.is_feature_enabled("e", "orthopedic") is False

    def test_is_agent_enabled(self, mgr):
        mgr.create("F医院", hospital_name="F", tenant_id="f", enabled_agents=["pharmacy", "cardiology"])
        assert mgr.is_agent_enabled("f", "pharmacy") is True
        assert mgr.is_agent_enabled("f", "cardiology") is True
        assert mgr.is_agent_enabled("f", "orthopedic") is False  # not in enabled_agents list

    def test_delete_is_soft(self, mgr):
        mgr.create("G医院", hospital_name="G", tenant_id="g")
        mgr.delete("g")
        t = mgr.get("g")
        # soft delete — tenant still exists but is EXPIRED
        assert t is not None
        assert t.status == TenantStatus.EXPIRED

    def test_set_feature(self, mgr):
        mgr.create("H医院", hospital_name="H", tenant_id="h")
        mgr.set_feature("h", "pharmacy", True)
        assert mgr.is_feature_enabled("h", "pharmacy") is True
        mgr.set_feature("h", "pharmacy", False)
        assert mgr.is_feature_enabled("h", "pharmacy") is False

    def test_get_default_tenant(self, mgr):
        mgr.create("默认医院", hospital_name="默认医院", tenant_id="default")
        default = mgr.get_default()
        assert default is not None

    def test_get_his_config(self, mgr):
        mgr.create("I医院", hospital_name="I", tenant_id="i")
        config = mgr.get_his_config("i")
        assert config is not None
        assert config["type"] == "mock"


class TestInitDefaultTenant:
    def test_init_default(self):
        init_default_tenant()
        mgr = get_tenant_manager()
        default = mgr.get_default()
        assert default is not None
        assert default.name == "default"
        assert default.hospital_name == "Default Hospital"


class TestTenantSingleton:
    def test_same_instance(self):
        mgr1 = get_tenant_manager()
        mgr2 = get_tenant_manager()
        assert mgr1 is mgr2
