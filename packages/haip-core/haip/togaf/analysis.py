"""TOGAF 科室 4A 分析方法论 v2.0 — Full Pipeline Engine.

5 层分析 → 成熟度评分 → 热力图数据 → 开发路线图
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter

from haip.togaf.organization import list_orgs, list_roles
from haip.togaf.templates_dept import get_dept_template, get_guideline_info
from haip.togaf.validator import validate_agent, _ROLE_ID_TO_LEVEL


@dataclass
class MaturityScore:
    """5-dimension maturity score (0-100)."""
    role_completeness: int = 0
    data_coverage: int = 0
    guideline_adherence: int = 0
    a2a_connectivity: int = 0
    validation_pass_rate: int = 0

    @property
    def total(self) -> int:
        return (self.role_completeness + self.data_coverage
                + self.guideline_adherence + self.a2a_connectivity
                + self.validation_pass_rate) // 5

    @property
    def tier(self) -> str:
        if self.total >= 80:
            return "L3 成熟"
        if self.total >= 50:
            return "L2 发展中"
        if self.total >= 20:
            return "L1 起步"
        return "L0 未覆盖"

    def to_dict(self) -> dict:
        return {
            "role_completeness": self.role_completeness,
            "data_coverage": self.data_coverage,
            "guideline_adherence": self.guideline_adherence,
            "a2a_connectivity": self.a2a_connectivity,
            "validation_pass_rate": self.validation_pass_rate,
            "total": self.total,
            "tier": self.tier,
        }


@dataclass
class DepartmentAnalysisV2:
    org_id: str
    org_name: str
    parent_id: str
    template_type: str
    # Layer 1: Org
    role_count: int = 0
    dept_roles: list[dict] = field(default_factory=list)
    # Layer 2: Guidelines
    has_guideline: bool = False
    guidelines: list[dict] = field(default_factory=list)
    # Layer 3: Architecture
    template_vs_count: int = 0
    template_bp_count: int = 0
    data_entities: list[str] = field(default_factory=list)
    # Layer 4: Agent
    has_agent: bool = False
    agent_name: str = ""
    stage_count: int = 0
    tool_count: int = 0
    stage_role_coverage: float = 0.0
    validation_passed: bool = False
    validation_detail: dict = field(default_factory=dict)
    # Layer 5: Scoring
    score: MaturityScore = field(default_factory=MaturityScore)
    gaps: list[str] = field(default_factory=list)
    # Priority
    priority: int = 99  # lower = higher priority


def analyze_all_v2() -> list[DepartmentAnalysisV2]:
    """Run full v2.0 analysis on all clinical departments."""
    registry = {}
    try:
        from haip.agent import _registry as _agent_registry, load_from_dir
        if not _agent_registry:
            load_from_dir("")
        registry = _agent_registry
    except Exception:
        pass

    all_orgs = list_orgs()
    # Build parent lookup
    org_parent: dict[str, str] = {}
    for o in all_orgs:
        if hasattr(o, 'parent') and o.parent:
            org_parent[o.id] = o.parent

    clinical_orgs = [o for o in all_orgs if o.type == "clinical" and o.parent]
    results: list[DepartmentAnalysisV2] = []

    for org in sorted(clinical_orgs, key=lambda o: o.name):
        parent_id = org_parent.get(org.id, "")
        template = get_dept_template(org.id, parent_id)
        template_type = template.type_kr if template else "通用"

        a = DepartmentAnalysisV2(
            org_id=org.id,
            org_name=org.name,
            parent_id=parent_id,
            template_type=template_type,
        )

        # ── Layer 1: Organization Roles ──
        dept_roles = list_roles(org_id=org.id)
        a.role_count = len(dept_roles)
        a.dept_roles = [
            {"id": r.id, "level": r.level, "focus_count": len(r.focus_areas)}
            for r in dept_roles
        ]

        # ── Layer 2: Guidelines ──
        guidelines = get_guideline_info(org.id)
        a.has_guideline = len(guidelines) > 0
        a.guidelines = guidelines

        # ── Layer 3: Architecture (Template-based) ──
        if template:
            a.template_vs_count = len(template.value_streams)
            a.template_bp_count = len(template.business_processes)
            a.data_entities = template.common_data_entities
        else:
            a.data_entities = ["患者信息", "检验报告"]

        # ── Layer 4: Agent ──
        agent, agent_obj = _find_agent(org.name, registry)
        if agent_obj:
            a.has_agent = True
            a.agent_name = agent
            stages = agent_obj.get_stages() if hasattr(agent_obj, 'get_stages') else []
            a.stage_count = len(stages)
            a.tool_count = len(agent_obj.tools) if hasattr(agent_obj, 'tools') else 0

            # Stage role coverage: how many dept roles are used in stages
            if stages and dept_roles:
                dept_levels = {r.level for r in dept_roles}
                stage_levels: set[str] = set()
                for s in stages:
                    for rid in s.get("role_ids", []):
                        level = _ROLE_ID_TO_LEVEL.get(rid, rid)
                        stage_levels.add(level)
                covered = dept_levels & stage_levels
                a.stage_role_coverage = round(len(covered) / len(dept_levels) * 100, 1) if dept_levels else 100

            # Validation
            try:
                report = validate_agent(agent, registry=registry)
                if report:
                    a.validation_passed = report.passed
                    a.validation_detail = {
                        "checks": len(report.checks),
                        "passed_checks": sum(1 for c in report.checks if c.passed),
                        "warnings": report.warnings,
                    }
            except Exception:
                pass

        # ── Layer 5: Maturity Scoring ──
        a.score = _calculate_score(a)
        a.gaps = _find_gaps(a)
        a.priority = _calculate_priority(a)

        results.append(a)

    return results


def _find_agent(org_name: str, registry: dict) -> tuple[str, object | None]:
    """Map Chinese department name to agent by scanning department field."""
    # Priority: explicit mappings for multi-dept agents
    dept_agent_map = {
        "创伤骨科": "orthopedic-surgery", "脊柱骨科": "orthopedic-surgery",
        "关节骨科": "orthopedic-surgery",
    }
    agent_name = dept_agent_map.get(org_name, "")
    if agent_name and agent_name in registry:
        return agent_name, registry[agent_name]
    # Fallback: search by department field
    for name, agent in registry.items():
        dept = getattr(agent, 'department', '') or ''
        if dept == org_name:
            return name, agent
    return "", None


def _calculate_score(a: DepartmentAnalysisV2) -> MaturityScore:
    """5-dimension maturity scoring."""
    s = MaturityScore()

    # 1. Role completeness: YAML roles covered / TOGAF roles
    if a.role_count > 0:
        s.role_completeness = min(100, int(a.stage_role_coverage))

    # 2. Data coverage: entities referenced / template entities
    if a.data_entities:
        # Score based on whether data entities are referenced in any stage
        s.data_coverage = 40 if a.has_agent else 0
        if a.stage_count >= 6:
            s.data_coverage = 60
        if a.has_guideline:
            s.data_coverage = min(100, s.data_coverage + 20)

    # 3. Guideline adherence
    if a.has_guideline:
        s.guideline_adherence = 70
        if a.template_bp_count >= 6:
            s.guideline_adherence = 90
    elif a.template_bp_count >= 5:
        s.guideline_adherence = 40  # Has template, no specific guideline
    else:
        s.guideline_adherence = 0

    # 4. A2A connectivity
    if a.has_agent:
        s.a2a_connectivity = 50  # Agent registered
        if a.validation_detail.get("checks", 0) >= 5:
            s.a2a_connectivity = 80
        if a.validation_passed:
            s.a2a_connectivity = 100

    # 5. Validation pass rate
    if a.validation_detail:
        total = a.validation_detail.get("checks", 5)
        passed = a.validation_detail.get("passed_checks", 0)
        s.validation_pass_rate = int(passed / total * 100) if total > 0 else 0
    elif a.has_agent:
        s.validation_pass_rate = 0

    return s


def _find_gaps(a: DepartmentAnalysisV2) -> list[str]:
    gaps: list[str] = []
    if not a.has_agent:
        gaps.append("无Agent")
    if a.stage_count == 0 and a.has_agent:
        gaps.append("无诊疗阶段定义")
    if a.template_vs_count == 0:
        gaps.append("无价值流模板")
    if a.stage_role_coverage < 50 and a.has_agent:
        gaps.append(f"角色覆盖率低({a.stage_role_coverage:.0f}%)")
    return gaps


def _calculate_priority(a: DepartmentAnalysisV2) -> int:
    """Lower = higher priority for agent development."""
    p = 99
    if not a.has_agent:
        p -= 50  # No agent = urgent
    if a.has_guideline:
        p -= 20  # Has guideline = easier to implement
    if a.template_vs_count >= 5:
        p -= 10  # Template available
    if a.score.total >= 30:
        p -= 5   # Already partially covered
    return max(1, p)


def print_report_v2(results: list[DepartmentAnalysisV2] | None = None) -> str:
    if results is None:
        results = analyze_all_v2()

    lines: list[str] = []
    lines.append("=" * 120)
    lines.append("南方医院全院科室 TOGAF 4A 分析方法论 v2.0 报告")
    lines.append("=" * 120)

    # Summary
    total = len(results)
    has_agent = sum(1 for r in results if r.has_agent)
    has_guideline = sum(1 for r in results if r.has_guideline)
    tiers = Counter(r.score.tier for r in results)
    lines.append(f"科室总数: {total} | 有Agent: {has_agent} | 有指南: {has_guideline}")
    lines.append(f"成熟度分布: {dict(tiers)}")
    avg_score = sum(r.score.total for r in results) // max(total, 1)
    lines.append(f"平均成熟度: {avg_score}/100")

    lines.append(f"\n{'科室':14s} | {'类型':6s} | {'角色':>3s} | {'指南':3s} | {'VS':>2s} | {'BP':>2s} | {'Agent':>25s} | {'阶段':>3s} | {'评分':>3s} | {'等级':8s} | {'优先级':>3s} | Gap")
    lines.append("-" * 120)

    for r in sorted(results, key=lambda x: x.priority):
        agent_disp = r.agent_name[:25] if r.has_agent else "—"
        guideline_mark = "✓" if r.has_guideline else "—"
        score = r.score.total
        gaps = ", ".join(r.gaps[:2]) if r.gaps else "—"

        lines.append(
            f"{r.org_name:14s} | {r.template_type:6s} | {r.role_count:>3d} | {guideline_mark:>3s} | "
            f"{r.template_vs_count:>2d} | {r.template_bp_count:>2d} | {agent_disp:>25s} | "
            f"{r.stage_count:>3d} | {score:>3d} | {r.score.tier:8s} | {r.priority:>3d} | {gaps}"
        )

    return "\n".join(lines)


def export_heatmap_data(results: list[DepartmentAnalysisV2] | None = None) -> dict:
    """Export maturity data as JSON for heatmap visualization."""
    if results is None:
        results = analyze_all_v2()
    return {
        "departments": [
            {
                "name": r.org_name,
                "type": r.template_type,
                "score": r.score.to_dict(),
                "has_agent": r.has_agent,
                "agent": r.agent_name,
                "priority": r.priority,
                "gaps": r.gaps,
            }
            for r in sorted(results, key=lambda x: x.priority)
        ],
        "summary": {
            "total": len(results),
            "avg_score": sum(r.score.total for r in results) // max(len(results), 1),
            "tiers": dict(Counter(r.score.tier for r in results)),
        },
    }
