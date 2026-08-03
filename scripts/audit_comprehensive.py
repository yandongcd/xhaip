"""Comprehensive xhaip agent audit - cross-referencing YAML, modules, knowledge, and data."""
import json
import pathlib
import sys
from collections import defaultdict

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital"))
sys.path.insert(0, str(ROOT / "packages" / "haip-hospital" / "modules"))

agents_dir = ROOT / "packages/haip-hospital/agents/definitions"
modules_dir = ROOT / "packages/haip-hospital/modules"
rules_dir = ROOT / "packages/haip-hospital/knowledge/rules"
patients_path = ROOT / "packages/haip-hospital/data/patients.json"


def load_all_agents():
    agents = {}
    for yf in sorted(agents_dir.glob("*.yaml")):
        data = yaml.safe_load(yf.read_text(encoding="utf-8"))
        if data:
            agents[data["name"]] = data
    return agents


def scan_modules():
    existing = {}
    for d in sorted(modules_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        py_files = list(d.rglob("*.py"))
        init_file = d / "__init__.py"
        has_init = init_file.exists()
        init_size = init_file.stat().st_size if has_init else 0
        funcs_in_init = []
        if has_init and init_size > 0:
            try:
                content = init_file.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.strip().startswith("def "):
                        funcs_in_init.append(line.strip().split("(")[0].replace("def ", ""))
            except Exception:
                pass
        other_funcs = []
        for pf in py_files:
            if pf.name == "__init__.py":
                continue
            try:
                content = pf.read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.strip().startswith("def "):
                        other_funcs.append({
                            "file": str(pf.relative_to(modules_dir)).replace("\\", "/"),
                            "func": line.strip().split("(")[0].replace("def ", ""),
                        })
            except Exception:
                pass
        existing[d.name] = {
            "is_stub": has_init and init_size == 0,
            "py_files": len(py_files),
            "init_funcs": funcs_in_init,
            "other_funcs": other_funcs,
        }
    return existing


def handler_to_signature(handler):
    """Convert 'module.sub.file.func' or 'module.func' into (module_name, full_func_path)."""
    if "." not in handler:
        return (handler, "")
    parts = handler.split(".")
    return (parts[0], ".".join(parts[1:]))


def check_yaml_to_module_handlers(agents, modules):
    results = {"ok": [], "missing_module": [], "missing_func": []}
    for name, agent in agents.items():
        for tool in agent.get("tools", []):
            handler = tool.get("handler", "")
            if not handler or "." not in handler:
                continue
            mod_name, func_path = handler_to_signature(handler)
            mod_info = modules.get(mod_name)
            if not mod_info:
                results["missing_module"].append({
                    "agent": name, "tool": tool.get("name", "?"), "handler": handler, "module": mod_name,
                })
                continue

            # Try to match the function
            found = _find_func_in_module(mod_info, mod_name, func_path)
            if found:
                results["ok"].append({"agent": name, "tool": tool.get("name", "?"), "handler": handler})
            else:
                results["missing_func"].append({
                    "agent": name, "tool": tool.get("name", "?"), "handler": handler,
                    "module_has_init_funcs": mod_info.get("init_funcs", []),
                    "module_has_other_funcs": len(mod_info.get("other_funcs", [])),
                })
    return results


def _find_func_in_module(mod_info, mod_name, func_path):
    """Check if a function path exists in the module."""
    # Direct match in __init__.py
    if func_path in mod_info.get("init_funcs", []):
        return True
    # Match in other files
    for f_entry in mod_info.get("other_funcs", []):
        fname = f_entry["func"]
        ffile = f_entry["file"].replace("\\", "/")
        full = ffile.replace(".py", "").replace("/", ".").replace("__init__.", "")
        if func_path == full or func_path == fname:
            return True
        # Also try module.func_path
        if f"{mod_name}.{func_path}" == f"{mod_name}.{full}":
            return True
    return False


def check_guard_vs_knowledge(agents):
    results = {"has_triggers": 0, "no_triggers": 0, "has_rules_no_triggers": [], "triggers_no_rules": []}
    existing_rules = set()
    if rules_dir.exists():
        for rd in sorted(rules_dir.iterdir()):
            if rd.is_dir() and not rd.name.startswith("_"):
                existing_rules.add(rd.name)

    for name, agent in agents.items():
        agent_type = agent.get("type", "business")
        if agent_type == "master_data":
            continue
        triggers = agent.get("guard", {}).get("triggers", [])
        agent_key = name.replace("-", "_")
        has_rules = any(agent_key in rname for rname in existing_rules)
        if triggers:
            results["has_triggers"] += 1
            if not has_rules:
                results["triggers_no_rules"].append(name)
        else:
            results["no_triggers"] += 1
            if has_rules:
                results["has_rules_no_triggers"].append(name)
    return results


def check_stages_completeness(agents):
    results = {"no_stages": [], "fewer_than_3": [], "missing_role_ids": [], "short_description": [], "ok": 0}
    for name, agent in agents.items():
        agent_type = agent.get("type", "business")
        if agent_type == "master_data":
            continue
        stages = agent.get("stages", [])
        if not stages:
            results["no_stages"].append(name)
            continue
        if len(stages) < 3:
            results["fewer_than_3"].append({"agent": name, "count": len(stages)})
        for s in stages:
            if not s.get("role_ids"):
                results["missing_role_ids"].append({"agent": name, "stage": s.get("label", s.get("id", "?"))})
            desc = s.get("desc", "")
            if not desc or len(desc) < 10:
                results["short_description"].append({"agent": name, "stage": s.get("label", s.get("id", "?"))})
    return results


def check_role_consistency(agents):
    results = {"orphan_roles": [], "no_ui_roles": [], "no_default_role": []}
    for name, agent in agents.items():
        if agent.get("type") == "master_data":
            continue
        ui_roles = {r.get("id") for r in agent.get("ui", {}).get("roles", [])}
        if not ui_roles:
            results["no_ui_roles"].append(name)
            continue
        stage_roles = set()
        for s in agent.get("stages", []):
            stage_roles.update(s.get("role_ids", []))
        orphan = stage_roles - ui_roles
        if orphan:
            results["orphan_roles"].append({"agent": name, "orphan": sorted(orphan)})
        has_default = any(r.get("default") for r in agent.get("ui", {}).get("roles", []))
        if not has_default:
            results["no_default_role"].append(name)
    return results


def check_citation_enforcement(agents):
    results = {"high_risk_no_citation": [], "has_citation": 0, "no_high_risk": 0}
    for name, agent in agents.items():
        high_risk = agent.get("guard", {}).get("high_risk_scenarios", [])
        citation = agent.get("guard", {}).get("citation", {})
        if high_risk:
            if not citation.get("required"):
                results["high_risk_no_citation"].append(name)
            else:
                results["has_citation"] += 1
        else:
            results["no_high_risk"] += 1
    return results


def check_prompt_quality(agents):
    results = {"short_prompt": [], "no_prompt": [], "ok": 0}
    for name, agent in agents.items():
        if agent.get("type") == "master_data":
            continue
        prompt = agent.get("prompt", {}).get("system", "")
        if not prompt:
            results["no_prompt"].append(name)
        elif len(prompt) < 20:
            results["short_prompt"].append({"agent": name, "len": len(prompt)})
        else:
            results["ok"] += 1
    return results


def check_patient_data(agents):
    if not patients_path.exists():
        return {"error": "patients.json not found", "total": 0}
    try:
        patients = json.loads(patients_path.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "patients.json parse error", "total": 0}
    if not isinstance(patients, list):
        return {"error": "patients.json not a list", "total": 0}

    agent_departments = {}
    for name, agent in agents.items():
        dept = agent.get("department", "") or agent.get("cn_name", "")
        agent_departments[name] = dept

    total = len(patients)
    dept_counts = defaultdict(int)
    for p in patients:
        dept = str(p.get("department", "") or p.get("科室", "") or "")
        dept_counts[dept] += 1

    return {"total_patients": total, "by_department": dict(dept_counts), "agent_departments": agent_departments}


if __name__ == "__main__":
    agents = load_all_agents()
    modules = scan_modules()
    print(f"Agents: {len(agents)}")
    print(f"Modules: {len(modules)}")

    # 1. Handler audit
    print()
    print("=" * 60)
    print("1. HANDLER Audit (YAML -> Module)")
    print("=" * 60)
    h = check_yaml_to_module_handlers(agents, modules)
    print(f"  OK: {len(h['ok'])}")
    print(f"  Module not found: {len(h['missing_module'])}")
    for m in h["missing_module"]:
        print(f"    [{m['agent']}] {m['tool']} -> {m['handler']}")

    missing_func = h["missing_func"]
    stub_agents = sorted(set(x["agent"] for x in missing_func))
    print(f"  Function not found: {len(missing_func)} handlers")
    print(f"  Affected agents: {len(stub_agents)}")
    for a in stub_agents:
        count = sum(1 for x in missing_func if x["agent"] == a)
        print(f"    {a}: {count} missing handlers")

    # 2. Guard vs Knowledge
    print()
    print("=" * 60)
    print("2. GUARD Triggers vs Knowledge Rules")
    print("=" * 60)
    g = check_guard_vs_knowledge(agents)
    print(f"  Has triggers: {g['has_triggers']}")
    print(f"  No triggers: {g['no_triggers']}")
    if g["has_rules_no_triggers"]:
        print(f"  Has rules but no triggers: {len(g['has_rules_no_triggers'])} agents")
        for a in g["has_rules_no_triggers"]:
            print(f"    [{a}]")
    if g["triggers_no_rules"]:
        print(f"  Has triggers but no rules: {len(g['triggers_no_rules'])} agents")

    # 3. Stages
    print()
    print("=" * 60)
    print("3. Stage Completeness")
    print("=" * 60)
    s = check_stages_completeness(agents)
    print(f"  No stages: {len(s['no_stages'])}")
    for a in s["no_stages"]:
        print(f"    [{a}]")
    if s["fewer_than_3"]:
        print("  Fewer than 3 stages:")
        for item in s["fewer_than_3"]:
            print(f"    [{item['agent']}] count={item['count']}")
    print(f"  Missing role_ids: {len(s['missing_role_ids'])} occurrences")
    print(f"  Short descriptions: {len(s['short_description'])} occurrences")

    # 4. Roles
    print()
    print("=" * 60)
    print("4. Role Consistency (Stage role_ids vs UI roles)")
    print("=" * 60)
    r = check_role_consistency(agents)
    print(f"  No UI roles: {len(r['no_ui_roles'])}")
    if r["orphan_roles"]:
        print(f"  Orphan role references: {len(r['orphan_roles'])}")
        for item in r["orphan_roles"]:
            print(f"    [{item['agent']}] {item['orphan']}")
    print(f"  No default role: {len(r['no_default_role'])}")

    # 5. Citation
    print()
    print("=" * 60)
    print("5. Citation Enforcement")
    print("=" * 60)
    c = check_citation_enforcement(agents)
    print(f"  Has citation: {c['has_citation']}")
    print(f"  No high_risk_scenarios: {c['no_high_risk']}")
    if c["high_risk_no_citation"]:
        print(f"  High risk but no citation: {len(c['high_risk_no_citation'])}")
        for a in c["high_risk_no_citation"]:
            print(f"    [{a}]")

    # 6. Prompts
    print()
    print("=" * 60)
    print("6. Prompt Quality")
    print("=" * 60)
    p = check_prompt_quality(agents)
    print(f"  OK: {p['ok']}")
    print(f"  No prompt: {len(p['no_prompt'])}")
    for a in p["no_prompt"]:
        print(f"    [{a}]")
    if p["short_prompt"]:
        print(f"  Short prompt (<20 chars): {len(p['short_prompt'])}")

    # 7. Patient data
    print()
    print("=" * 60)
    print("7. Patient Data")
    print("=" * 60)
    pd = check_patient_data(agents)
    if "error" in pd:
        print(f"  {pd['error']}")
    else:
        print(f"  Total patients: {pd['total_patients']}")
        agent_depts = pd.get("agent_departments", {})
        patient_depts = pd.get("by_department", {})
        matched = 0
        unmatched_agents = []
        for name, dept in agent_depts.items():
            if dept in patient_depts:
                matched += 1
            else:
                unmatched_agents.append(f"{name}({dept})")
        print(f"  Agents with patient data: {matched}/{len(agent_depts)}")
        if unmatched_agents:
            print(f"  Unmatched: {unmatched_agents[:10]}")

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print("  6 systemic issue dimensions found:")
    print()
    issues = []
    if stub_agents:
        issues.append(f"  Handler stubs:               {len(stub_agents)} agents (no function implementation)")
    if g.get("has_rules_no_triggers"):
        issues.append(f"  Rules without guard triggers: {len(g['has_rules_no_triggers'])} agents")
    if s["no_stages"]:
        issues.append(f"  No clinical stages:          {len(s['no_stages'])} agents")
    if r["orphan_roles"]:
        issues.append(f"  Stage/UI role mismatch:      {len(r['orphan_roles'])} agents")
    if c.get("high_risk_no_citation"):
        issues.append(f"  High risk, no citation:      {len(c['high_risk_no_citation'])} agents")
    if p["no_prompt"]:
        issues.append(f"  No system prompt:            {len(p['no_prompt'])} agents")
    for iss in issues:
        print(iss)
