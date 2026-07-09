"""TOGAF 10 Architecture Governance — Core Metamodel + Organization + Builder + Audit
+ BP Governance Validator + Clinical Role Perspectives.

This package is NOT an Agent. It is the architectural governance foundation
that all Agents in xhaip derive from and are validated against.
"""

from __future__ import annotations

from haip.togaf.metamodel import (
    EntityType, RelationshipType,
    ENTITY_TYPES, RELATIONSHIP_TYPES,
)
from haip.togaf.organization import (
    OrgNode, RoleDef, OrgTree,
    ROLES, ROLE_BY_ID, ROLE_BY_ORG,
    build_org_tree, list_orgs, list_roles, get_role, get_org,
)

from haip.togaf.validator import (
    CheckResult, ValidationReport,
    validate_agent, validate_all, print_all_reports,
)

from haip.togaf.builder import (
    ArchitectureNode, ArchitectureEdge, Architecture4A,
    build_4a, build_to_dict, list_domains,
)

from haip.togaf.audit import (
    ArchNode, ArchEdge, ArchitectureLandscape,
    auto_discover, audit_environment, export_landscape,
)

from haip.togaf.layout import (
    layout_graph, NodeDict, EdgeDict, LayoutNode,
)

from haip.togaf.templates import (
    render_template, list_templates, TEMPLATE_MANIFEST,
)

from haip.togaf.governance import (
    BPCheckResult, BPValidationReport,
    validate_business_processes, validate_business_processes_detail,
    load_governance_rules, get_bp_governance_rules,
)

from haip.togaf.roles import (
    RoleDef as ClinicalRoleDef,
    ROLES as CLINICAL_ROLES,
    list_roles as list_clinical_roles,
    get_role as get_clinical_role,
    view_patient_as_role,
    view_patient_as_anesthesiologist,
    view_patient_as_attending,
    view_patient_as_pharmacist,
    view_patient_as_clinical_pharmacist,
    view_patient_as_review_pharmacist,
    view_patient_as_iv_compounding_pharmacist,
    view_patient_as_dietitian,
    view_patient_as_head_nurse,
    check_range,
)

__all__ = [
    # metamodel
    "EntityType", "RelationshipType",
    "ENTITY_TYPES", "RELATIONSHIP_TYPES",
    # organization
    "OrgNode", "RoleDef", "OrgTree",
    "ROLES", "ROLE_BY_ID", "ROLE_BY_ORG",
    "build_org_tree", "list_orgs", "list_roles", "get_role", "get_org",
    # validator
    "CheckResult", "ValidationReport",
    "validate_agent", "validate_all", "print_all_reports",
    # builder
    "ArchitectureNode", "ArchitectureEdge", "Architecture4A",
    "build_4a", "build_to_dict", "list_domains",
    # audit
    "ArchNode", "ArchEdge", "ArchitectureLandscape",
    "auto_discover", "audit_environment", "export_landscape",
    # layout
    "layout_graph", "NodeDict", "EdgeDict", "LayoutNode",
    # templates
    "render_template", "list_templates", "TEMPLATE_MANIFEST",
    # governance
    "BPCheckResult", "BPValidationReport",
    "validate_business_processes", "validate_business_processes_detail",
    "load_governance_rules", "get_bp_governance_rules",
    # clinical roles
    "ClinicalRoleDef", "CLINICAL_ROLES",
    "list_clinical_roles", "get_clinical_role",
    "view_patient_as_role",
    "view_patient_as_anesthesiologist",
    "view_patient_as_attending",
    "view_patient_as_pharmacist",
    "view_patient_as_clinical_pharmacist",
    "view_patient_as_review_pharmacist",
    "view_patient_as_iv_compounding_pharmacist",
    "view_patient_as_dietitian",
    "view_patient_as_head_nurse",
    "check_range",
]
