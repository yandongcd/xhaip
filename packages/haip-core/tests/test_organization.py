"""测试 organization.py — 组织结构和角色查询."""

from __future__ import annotations

import pytest

from haip.togaf.organization import (
    OrgNode,
    OrgTree,
    RoleDef,
    build_org_tree,
    get_org,
    get_role,
    list_orgs,
    list_roles,
)


class TestOrgNode:
    def test_default_construction(self):
        node = OrgNode(id="dept-01", name="骨外科", type="clinical")
        assert node.id == "dept-01"
        assert node.name == "骨外科"
        assert node.type == "clinical"
        assert node.parent == ""
        assert node.description == ""
        assert node.children == []

    def test_with_children(self):
        child = OrgNode(id="sub", name="Sub", type="clinical")
        parent = OrgNode(id="parent", name="Parent", type="clinical", children=[child])
        assert len(parent.children) == 1
        assert parent.children[0].name == "Sub"


class TestRoleDef:
    def test_default_construction(self):
        role = RoleDef(id="R001", name="主任", org_id="D01", org_name="内科", level="科主任", icon="👨‍⚕️")
        assert role.id == "R001"
        assert role.name == "主任"
        assert role.org_id == "D01"
        assert role.level == "科主任"
        assert role.icon == "👨‍⚕️"
        assert role.focus_areas == []
        assert role.description == ""


class TestBuildOrgTree:
    def test_returns_org_tree(self):
        tree = build_org_tree()
        assert isinstance(tree, OrgTree)
        assert len(tree.roots) > 0

    def test_all_roots_have_no_parent(self):
        tree = build_org_tree()
        for root in tree.roots:
            assert root.parent == ""

    def test_leadership_is_first_root(self):
        tree = build_org_tree()
        assert tree.roots[0].type == "leadership"


class TestListOrgs:
    def test_returns_all_orgs(self):
        orgs = list_orgs()
        assert len(orgs) > 50  # 71 departments expected

    def test_filter_by_type(self):
        clinical = list_orgs(org_type="clinical")
        assert len(clinical) > 0
        for org in clinical:
            assert org.type == "clinical"

    def test_admin_type(self):
        admin = list_orgs(org_type="admin")
        assert len(admin) > 0

    def test_empty_for_unknown_type(self):
        result = list_orgs(org_type="nonsense")
        assert result == []

    def test_each_org_has_unique_id(self):
        orgs = list_orgs()
        ids = [o.id for o in orgs]
        assert len(ids) == len(set(ids))


class TestListRoles:
    def test_returns_all_roles_without_filter(self):
        roles = list_roles()
        assert len(roles) > 100  # 184+ roles expected

    def test_filter_by_org_id(self):
        ortho_roles = list_roles(org_id="breast_center")
        assert len(ortho_roles) > 0
        for r in ortho_roles:
            assert r.org_id == "breast_center"

    def test_filter_by_level(self):
        dept_heads = list_roles(level="科主任")
        assert len(dept_heads) > 0
        for r in dept_heads:
            assert r.level == "科主任"

    def test_filter_by_org_and_level(self):
        result = list_roles(org_id="breast_center", level="科主任")
        assert len(result) == 1
        assert result[0].org_id == "breast_center"
        assert result[0].level == "科主任"

    def test_empty_for_unknown_org(self):
        assert list_roles(org_id="nonexistent_org") == []

    def test_each_role_has_unique_id(self):
        roles = list_roles()
        ids = [r.id for r in roles]
        assert len(ids) == len(set(ids))


class TestGetRole:
    def test_existing_role(self):
        role = get_role("breastcenter_attending")
        assert role is not None
        assert role.org_id == "breast_center"

    def test_unknown_role(self):
        assert get_role("nonexistent_role_id") is None


class TestGetOrg:
    def test_existing_org(self):
        org = get_org("breast_center")
        assert org is not None

    def test_unknown_org(self):
        assert get_org("nonexistent_org") is None
