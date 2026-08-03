"""TOGAF 10 Architecture Governance — Core Metamodel + Organization + Builder + Audit
+ BP Governance Validator + Clinical Role Perspectives.

This package is NOT an Agent. It is the architectural governance foundation
that all Agents in xhaip derive from and are validated against.
"""

from __future__ import annotations

from haip.togaf.audit import (
    ArchEdge,
    ArchitectureLandscape,
    ArchNode,
    audit_environment,
    auto_discover,
    export_landscape,
)
from haip.togaf.builder import (
    Architecture4A,
    ArchitectureEdge,
    ArchitectureNode,
    build_4a,
    build_to_dict,
    list_domains,
)
from haip.togaf.governance import (
    BPCheckResult,
    BPValidationReport,
    get_bp_governance_rules,
    load_governance_rules,
    validate_business_processes,
    validate_business_processes_detail,
)
from haip.togaf.layout import (
    EdgeDict,
    LayoutNode,
    NodeDict,
    layout_graph,
)
from haip.togaf.metamodel import (
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    EntityType,
    RelationshipType,
)
from haip.togaf.organization import (
    ROLE_BY_ID,
    ROLE_BY_ORG,
    ROLES,
    OrgNode,
    OrgTree,
    RoleDef,
    build_org_tree,
    get_org,
    get_role,
    list_orgs,
    list_roles,
)
from haip.togaf.roles import (
    ROLES as CLINICAL_ROLES,
)
from haip.togaf.roles import (
    RoleDef as ClinicalRoleDef,
)
from haip.togaf.roles import (
    check_range,
    view_patient_as_anesthesiologist,
    view_patient_as_attending,
    view_patient_as_clinical_pharmacist,
    view_patient_as_dietitian,
    view_patient_as_head_nurse,
    view_patient_as_iv_compounding_pharmacist,
    view_patient_as_pharmacist,
    view_patient_as_review_pharmacist,
    view_patient_as_role,
)
from haip.togaf.roles import (
    get_role as get_clinical_role,
)
from haip.togaf.roles import (
    list_roles as list_clinical_roles,
)
from haip.togaf.templates import (
    TEMPLATE_MANIFEST,
    list_templates,
    render_template,
)
from haip.togaf.validator import (
    CheckResult,
    ValidationReport,
    print_all_reports,
    validate_agent,
    validate_all,
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
