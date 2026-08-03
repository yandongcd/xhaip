"""TOGAF Architecture Dashboard — Full Hospital 4A Landscape.

Server-rendered visualization with:
  - 39 dept maturity heatmap (grouped by type)
  - Audit stats (nodes, edges, agents)
  - Dept × Agent mapping table
  - Quick validation status
"""

from __future__ import annotations


def _build_dept_agents_map(registry: dict) -> dict[str, list[dict]]:
    """Build department-name -> list of agent infos."""
    dept_map: dict[str, list[dict]] = {}
    for name, agent in registry.items():
        dept = getattr(agent, 'department', '') or ''
        if not dept:
            continue
        if dept not in dept_map:
            dept_map[dept] = []
        dept_map[dept].append({
            "name": agent.name,
            "cn_name": agent.cn_name,
            "type": agent.type,
            "port": agent.port,
        })

    # Hard-coded multi-dept → single agent (mirrors _find_agent in analysis.py)
    hard_coded = {
        "创伤骨科": "orthopedic-surgery",
        "脊柱骨科": "orthopedic-surgery",
        "关节骨科": "orthopedic-surgery",
    }
    # Ensure hard-coded mappings appear even if dept field doesn't match
    for dept_name, agent_name in hard_coded.items():
        if agent_name in registry and agent_name not in [a["name"] for a in dept_map.get(dept_name, [])]:
            agent = registry[agent_name]
            if dept_name not in dept_map:
                dept_map[dept_name] = []
            dept_map[dept_name].append({
                "name": agent.name,
                "cn_name": agent.cn_name,
                "type": agent.type,
                "port": agent.port,
            })

    return dept_map


def _load_analysis_data() -> dict:
    try:
        from haip.agent import _registry
        from haip.togaf.analysis import analyze_all_v2
        # If registry is empty, try loading from default location
        if not _registry:
            from pathlib import Path

            from haip.agent import load_from_dir
            yaml_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "packages" / "haip-hospital" / "agents" / "definitions"
            if yaml_dir.exists():
                load_from_dir(str(yaml_dir))
        results = analyze_all_v2()
        depts = []
        for r in results:
            depts.append({
                "name": r.org_name,
                "type": r.template_type,
                "score": r.score.total,
                "tier": r.score.tier,
                "has_agent": r.has_agent,
                "agent": r.agent_name,
                "stages": r.stage_count,
                "roles": r.role_count,
                "guideline": r.has_guideline,
                "validation_passed": r.validation_passed,
                "gaps": r.gaps,
                "dimensions": r.score.to_dict(),
            })
        tiers = {"L3 成熟": 0, "L2 发展中": 0, "L1 起步": 0, "L0 未覆盖": 0}
        for d in depts:
            tiers[d["tier"]] = tiers.get(d["tier"], 0) + 1
        avg = sum(d["score"] for d in depts) // max(len(depts), 1)
        return {
            "depts": depts,
            "dept_agents": _build_dept_agents_map(_registry),
            "tiers": tiers,
            "avg_score": avg,
            "total": len(depts),
        }
    except Exception as e:
        return {"error": str(e), "depts": [], "dept_agents": {}, "tiers": {}, "avg_score": 0, "total": 0}


def render_dashboard_json() -> dict:
    """Return dashboard data as JSON."""
    return _load_analysis_data()
