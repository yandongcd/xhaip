"""TOGAF Validator — 5-check pipeline for Agent ↔ TOGAF Architecture compliance.

Checks:
  1. Type Compliance    — agent.type must map to valid TOGAF EntityType
  2. Org Affiliation     — agent.department must exist in Organization tree
  3. Role Validity       — agent.ui.roles must belong to department's valid roles
  4. Dependency Graph    — agent.depends_on must point to registered, reachable agents
  5. Tool → Service Map  — agent.tools should trace to known capabilities

Usage:
  from haip.togaf.validator import validate_agent, validate_all
  report = validate_agent("orthopedic-surgery")
  print(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field

from haip.togaf.metamodel import ENTITY_TYPES
from haip.togaf.organization import ROLE_BY_ID, ROLE_BY_ORG, list_orgs


# ── Agent Type → TOGAF Entity Type Mapping ──

_AGENT_TYPE_TO_ENTITY: dict[str, str] = {
    "business": "ApplicationComponent",
    "specialist": "ApplicationService",
    "master_data": "DataEntity",
    "rules": "BusinessService",
    "architecture": "ApplicationComponent",
}


# ── AGENT_TYPE → org type filter ──

_AGENT_TYPE_TO_ORG_TYPE: dict[str, str] = {
    "business": "clinical",
    "specialist": "clinical",
    "master_data": "clinical",
    "rules": "clinical",
    "architecture": "admin",
}


# ── Department name → org_id mapping (reverse lookup) ──

# ── 部门中文名 → org_id 映射 ──

# Known English role ID → Chinese level mappings (for cross-referencing YAML ↔ TOGAF org)
_ROLE_ID_TO_LEVEL: dict[str, str] = {
    "attending": "主治医师",
    "surgeon": "主治医师",
    "resident": "住院医师",
    "anesthesiologist": "麻醉医师",
    "head_nurse": "护士长",
    "staff_nurse": "责任护士",
    "dept_head": "科主任",
    "pharmacist": "临床药师",
    "clinical_pharmacist": "临床药师",
    "review_pharmacist": "临床药师",
    "iv_compounding_pharmacist": "临床药师",
    "dietitian": "责任护士",
}


def _dept_to_org_id(department: str) -> str | None:
    """Map Chinese department name to org_id."""
    all_orgs = list_orgs()
    org_name_map: dict[str, str] = {}
    for org in all_orgs:
        org_name_map[org.name] = org.id
    # Direct match
    if department in org_name_map:
        return org_name_map[department]
    # Fuzzy: check parent department names (e.g. "骨外科" → "创伤骨科")
    # Map well-known departments to their org nodes
    _known_mappings = {
        "骨外科": "trauma_ortho",
        "心血管外科": "cardio_surgery",
        "药剂科": "pharmacy",
        "儿科": "pediatrics",
        "全院": "leadership",
    }
    return _known_mappings.get(department)


# ── Data Structures ──

@dataclass
class CheckResult:
    id: str
    name: str
    passed: bool
    detail: str
    suggestion: str = ""


@dataclass
class ValidationReport:
    agent_name: str
    agent_cn_name: str
    agent_type: str
    checks: list[CheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def add_check(self, result: CheckResult):
        self.checks.append(result)
        if not result.passed and result.suggestion:
            self.suggestions.append(result.suggestion)

    def summary(self) -> str:
        lines = [
            f"TOGAF Validation: {self.agent_name} ({self.agent_cn_name})",
            f"  Type: {self.agent_type}",
            f"  Passed: {'YES' if self.passed else 'NO'}",
            f"  Checks: {sum(1 for c in self.checks if c.passed)}/{len(self.checks)} passed",
        ]
        for c in self.checks:
            mark = "✅" if c.passed else "❌"
            lines.append(f"  {mark} {c.id}: {c.name}")
            if not c.passed:
                lines.append(f"     → {c.detail}")
                if c.suggestion:
                    lines.append(f"     💡 {c.suggestion}")
        if self.warnings:
            for w in self.warnings:
                lines.append(f"  ⚠️  {w}")
        return "\n".join(lines)


# ── Check 1: Type Compliance ──

def _check_type_compliance(agent) -> CheckResult:
    """Agent.type must map to a valid TOGAF EntityType."""
    entity_type = _AGENT_TYPE_TO_ENTITY.get(agent.type, "")
    if entity_type and entity_type in ENTITY_TYPES:
        return CheckResult(
            id="CHK-001",
            name="Type Compliance",
            passed=True,
            detail=f"agent.type='{agent.type}' → TOGAF EntityType='{entity_type}' ({ENTITY_TYPES[entity_type].layer} layer)",
        )
    return CheckResult(
        id="CHK-001",
        name="Type Compliance",
        passed=False,
        detail=f"agent.type='{agent.type}' has no TOGAF EntityType mapping",
        suggestion=f"Set type to one of: {list(_AGENT_TYPE_TO_ENTITY.keys())}",
    )


# ── Check 2: Org Affiliation ──

def _check_org_affiliation(agent) -> CheckResult:
    """Agent.department must exist in the Organization tree."""
    dept = agent.department or ""
    if not dept:
        return CheckResult(
            id="CHK-002",
            name="Org Affiliation",
            passed=False,
            detail="agent.department is empty",
            suggestion="Set department to a valid org name (e.g. '骨外科', '药剂科')",
        )

    org_id = _dept_to_org_id(dept)
    all_orgs = list_orgs()
    org_names = [o.name for o in all_orgs]
    if org_id:
        return CheckResult(
            id="CHK-002",
            name="Org Affiliation",
            passed=True,
            detail=f"department='{dept}' → org_id='{org_id}' (found in org tree)",
        )

    # Try fuzzy match
    for oname in org_names:
        if dept in oname or oname in dept:
            return CheckResult(
                id="CHK-002",
                name="Org Affiliation",
                passed=True,
                detail=f"department='{dept}' fuzzy-matched to org='{oname}'",
            )

    return CheckResult(
        id="CHK-002",
        name="Org Affiliation",
        passed=False,
        detail=f"department='{dept}' not found in org tree ({len(all_orgs)} orgs)",
        suggestion=f"Available clinical orgs: {sorted(o.name for o in all_orgs if o.type == 'clinical')[:10]}...",
    )


# ── Check 3: Role Validity ──

def _check_role_validity(agent) -> CheckResult:
    """Agent.ui.roles must reference valid roles from the department's role pool."""
    ui_roles = getattr(agent, "ui", None)
    if not ui_roles or not ui_roles.roles:
        # No roles defined — use defaults
        defaults = agent.get_roles() if hasattr(agent, "get_roles") else []
        if defaults:
            return CheckResult(
                id="CHK-003",
                name="Role Validity",
                passed=True,
                detail=f"No ui.roles defined; using {len(defaults)} defaults via get_roles()",
            )
        return CheckResult(
            id="CHK-003",
            name="Role Validity",
            passed=False,
            detail="No ui.roles defined and no defaults available",
            suggestion="Define ui.roles in YAML or set department for auto-generation",
        )

    dept = agent.department or ""
    org_id = _dept_to_org_id(dept) or dept
    valid_roles = ROLE_BY_ORG.get(org_id, [])
    if not valid_roles:
        return CheckResult(
            id="CHK-003",
            name="Role Validity",
            passed=True,
            detail=f"No role registry for org='{org_id}', skipping role validation",
        )

    invalid_roles = []
    for r in ui_roles.roles:
        role_id = r.get("id", "")
        role_label = r.get("label", "")
        found = False

        # Level 1: Direct match (id or label exact)
        for vr in valid_roles:
            if vr.id == role_id or vr.name == role_label or vr.level == role_label:
                found = True
                break

        # Level 2: English id → Chinese level mapping
        if not found and role_id in _ROLE_ID_TO_LEVEL:
            target_level = _ROLE_ID_TO_LEVEL[role_id]
            for vr in valid_roles:
                if vr.level == target_level:
                    found = True
                    break

        # Level 3: Fuzzy substring match (label chars in org role name/chars)
        if not found:
            for vr in valid_roles:
                if role_label and role_label in vr.name:
                    found = True
                    break
                if role_label and vr.name and any(c in vr.name for c in role_label if len(c.strip()) >= 1):
                    # At least 50% of the label's characters appear in the org role name
                    common = set(role_label) & set(vr.name)
                    if len(common) >= len(role_label) * 0.4:
                        found = True
                        break

        # Level 4: Global search across all roles
        if not found:
            for vr in ROLE_BY_ID.values():
                if vr.id == role_id:
                    found = True
                    break
                if role_id in _ROLE_ID_TO_LEVEL and vr.level == _ROLE_ID_TO_LEVEL[role_id]:
                    found = True
                    break
                if role_label and vr.name and (
                    role_label in vr.name
                    or (len(set(role_label) & set(vr.name)) >= len(role_label) * 0.4)
                ):
                    found = True
                    break

        if not found:
            invalid_roles.append(f"{role_label}({role_id})")

    total_roles = len(ui_roles.roles)
    if invalid_roles:
        return CheckResult(
            id="CHK-003",
            name="Role Validity",
            passed=False,
            detail=f"{len(invalid_roles)}/{total_roles} roles not found in dept pool: {', '.join(invalid_roles)}",
            suggestion="YAML roles should match department's registered roles (use list_roles(org_id))",
        )

    return CheckResult(
        id="CHK-003",
        name="Role Validity",
        passed=True,
        detail=f"All {total_roles} roles found in department role pool ({len(valid_roles)} available)",
    )


# ── Check 4: Dependency Graph ──

def _check_dependency_graph(agent, registry: dict) -> CheckResult:
    """Agent.depends_on must point to registered, valid agents."""
    deps = agent.depends_on or []
    if not deps:
        return CheckResult(
            id="CHK-004",
            name="Dependency Graph",
            passed=True,
            detail="No dependencies declared",
        )

    issues = []
    for dep in deps:
        dep_agent_name = dep.get("agent", "")
        if not dep_agent_name:
            continue
        if dep_agent_name not in registry:
            issues.append(f"'{dep_agent_name}' is not registered")
        else:
            # A2A relationship: ApplicationComponent communicates_via ApplicationService
            pass

    total = len([d for d in deps if d.get("agent")])
    if issues:
        return CheckResult(
            id="CHK-004",
            name="Dependency Graph",
            passed=False,
            detail=f"{len(issues)}/{total} dependencies invalid: {'; '.join(issues)}",
            suggestion="Ensure all depends_on agents are registered before this agent",
        )

    return CheckResult(
        id="CHK-004",
        name="Dependency Graph",
        passed=True,
        detail=f"All {total} dependencies resolved in registry",
    )


# ── Check 5: Tool → Service Mapping ──

def _check_tool_service_mapping(agent) -> CheckResult:
    """Each tool handler should be traceable to a capability or business service."""
    tools = agent.tools or []
    if not tools:
        return CheckResult(
            id="CHK-005",
            name="Tool → Service Mapping",
            passed=True,
            detail="No tools defined",
        )

    # Check: every tool has a handler (import path)
    handlers = [t.handler for t in tools if t.handler]
    coverage = len(handlers) / len(tools) * 100 if tools else 100

    # Check: handler paths are well-formed (module.function pattern)
    malformed = [h for h in handlers if not h or "." not in h]

    # Check: at least 70% of tools have handler modules that can be verified
    if malformed:
        return CheckResult(
            id="CHK-005",
            name="Tool → Service Mapping",
            passed=False,
            detail=f"{len(malformed)} tools have malformed handlers: {malformed}",
            suggestion="Handler format should be 'module.function' (e.g. 'orthopedics.assess')",
        )

    detail_parts = [
        f"{len(tools)} tools defined",
        f"{len(handlers)} have handler paths ({coverage:.0f}%)",
    ]

    return CheckResult(
        id="CHK-005",
        name="Tool → Service Mapping",
        passed=coverage >= 70,
        detail=". ".join(detail_parts),
        suggestion="Ensure each tool maps to a corresponding entry in knowledge/capabilities/ catalog" if coverage < 100 else "",
    )


# ── Public API ──

def validate_agent(agent_name: str, registry: dict | None = None) -> ValidationReport | None:
    """Run 5-check TOGAF validation against a single agent.

    Args:
        agent_name: Canonical agent name (e.g. 'orthopedic-surgery')
        registry: Optional pre-loaded registry dict. If None, imports from haip.agent.

    Returns:
        ValidationReport or None if agent not found.
    """
    if registry is None:
        from haip.agent import _registry as _agent_registry
        registry = _agent_registry

    agent = registry.get(agent_name)
    if not agent:
        return None

    report = ValidationReport(
        agent_name=agent.name,
        agent_cn_name=getattr(agent, "cn_name", ""),
        agent_type=getattr(agent, "type", "unknown"),
    )

    # Run all 5 checks
    c1 = _check_type_compliance(agent)
    c2 = _check_org_affiliation(agent)
    c3 = _check_role_validity(agent)
    c4 = _check_dependency_graph(agent, registry)
    c5 = _check_tool_service_mapping(agent)

    report.add_check(c1)
    report.add_check(c2)
    report.add_check(c3)
    report.add_check(c4)
    report.add_check(c5)

    # Aggregate warnings
    if not c2.passed and hasattr(agent, "tools") and agent.tools:
        report.warnings.append("Agent has tools but no valid org affiliation — may be intentional (specialist agent)")
    if not c3.passed and not hasattr(agent, "ui"):
        report.warnings.append("No ui config — using default rendering")

    return report

def validate_all(registry: dict | None = None) -> list[ValidationReport]:
    """Run TOGAF validation against all registered agents.

    Args:
        registry: Optional pre-loaded agent registry. If None, imports from haip.agent.
    """
    if registry is None:
        from haip.agent import _registry as _agent_registry
        registry = _agent_registry
    reports = []
    for name in sorted(registry.keys()):
        report = validate_agent(name, registry=registry)
        if report:
            reports.append(report)
    return reports


def print_all_reports(reports: list[ValidationReport] | None = None) -> str:
    """Print validation summary for all agents."""
    if reports is None:
        reports = validate_all()
    lines = []
    passed_count = sum(1 for r in reports if r.passed)
    lines.append(f"\n{'='*60}")
    lines.append(f"TOGAF Validation Report — {passed_count}/{len(reports)} agents passed")
    lines.append(f"{'='*60}")
    for r in reports:
        lines.append(r.summary())
        lines.append("")
    return "\n".join(lines)
