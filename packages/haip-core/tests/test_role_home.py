"""R1a: RBAC 角色扩充 + 12 门户身份种子账户 + /home 按角色分流."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


class TestPortalIdentityRoles:
    """PORTAL_IDENTITY_ROLES 完整性 + 新角色权限断言."""

    def test_all_12_identities_coverage(self):
        from haip.auth.models import PORTAL_IDENTITY_ROLES, PREDEFINED_ROLES

        expected = {
            "director", "secretary", "vice-director", "dept-head", "attending",
            "head-nurse", "pharmacist", "anesthesiologist", "med-tech",
            "admin", "resident", "intern",
        }
        assert set(PORTAL_IDENTITY_ROLES) == expected
        for identity, role in PORTAL_IDENTITY_ROLES.items():
            assert role in PREDEFINED_ROLES, f"{identity} -> {role} not in PREDEFINED_ROLES"

    def test_intern_no_execute(self):
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission

        role = PORTAL_IDENTITY_ROLES["intern"]
        assert not has_permission([role], Permission.AGENT_EXECUTE)
        assert has_permission([role], Permission.AGENT_READ)
        assert has_permission([role], Permission.PATIENT_READ)

    def test_head_nurse_has_audit_read(self):
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission

        role = PORTAL_IDENTITY_ROLES["head-nurse"]
        assert role == "head_nurse"
        assert has_permission([role], Permission.AUDIT_READ)
        assert not has_permission([role], Permission.AGENT_EXECUTE)
        assert has_permission([role], Permission.PATIENT_READ)

    def test_anesthesiologist_can_execute(self):
        from haip.auth.models import PORTAL_IDENTITY_ROLES, Permission
        from haip.auth.rbac import has_permission

        role = PORTAL_IDENTITY_ROLES["anesthesiologist"]
        assert role == "anesthesiologist"
        assert has_permission([role], Permission.AGENT_EXECUTE)
        assert has_permission([role], Permission.PATIENT_READ)
        assert has_permission([role], Permission.PATIENT_WRITE)


class TestHomeRedirect:
    """GET /home 按角色分流."""

    @pytest.fixture(autouse=True)
    def setup(self):
        os.environ["HAIP_TEST_MODE"] = "true"
        from haip.web_server import app
        self.client = TestClient(app)

    def test_identity_director_302_to_dashboard(self):
        r = self.client.get("/home", params={"identity": "director"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/dashboard"

    def test_identity_pharmacist_302_to_pharmacy(self):
        r = self.client.get("/home", params={"identity": "pharmacist"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/pharmacy"

    def test_identity_intern_302_to_education(self):
        r = self.client.get("/home", params={"identity": "intern"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/agent/education"

    def test_identity_head_nurse_302_to_nurse_general(self):
        r = self.client.get("/home", params={"identity": "head-nurse"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/agent/nurse-general"

    def test_identity_med_tech_302_to_lab_critical_value(self):
        r = self.client.get("/home", params={"identity": "med-tech"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/agent/lab-critical-value"

    def test_role_resident_302_to_root(self):
        r = self.client.get("/home", params={"role": "resident"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_unknown_role_302_to_root(self):
        r = self.client.get("/home", params={"role": "nonexistent_role_xyz"}, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_no_params_302_to_root(self):
        r = self.client.get("/home", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"


class TestDemoIdentitySeeding:
    """seed_demo_identities 幂等 + 12 用户."""

    def test_seed_idempotent(self):
        from haip.auth import AuthService
        import os

        os.environ["HAIP_TEST_MODE"] = "true"
        auth = AuthService()

        # First call creates users
        n1 = auth.seed_demo_identities()
        assert n1 == 12

        # Second call is idempotent — creates 0 more
        n2 = auth.seed_demo_identities()
        assert n2 == 0

        # All 12 users exist
        from haip.auth.models import PORTAL_IDENTITY_ROLES
        for identity in PORTAL_IDENTITY_ROLES:
            user = auth.get_user(identity)
            assert user is not None, f"Missing user: {identity}"
