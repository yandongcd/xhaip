import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-core"))
from haip.meta_harness import MetaHarness

mh = MetaHarness()
r = mh.run_full_cycle(run_proposer=False)
s = r["stages"]

issues = []

# Static auto-test failures
at = s.get("auto_testing", {})
for f in at.get("failures", []):
    issues.append(f"[Static] {f['agent']}/{f.get('test','?')}: {f['result']}")

# RLAIF violations
rlaif = s.get("rlaif_audit", {})
for v in rlaif.get("violations", []):
    issues.append(f"[RLAIF/{v.get('severity','')}] {v['agent']}: {v['detail']}")

# Runtime A2A failures
a2a = s.get("runtime_a2a", {})
for f in a2a.get("failures", []):
    issues.append(f"[Runtime] {f['agent']}/{f['tool']}: {f.get('error_type','?')} — {f.get('error_message','')[:80]}")

# Rule compliance violations
rc = s.get("rule_compliance", {})
for v in rc.get("top_violations", []):
    issues.append(f"[Rule] {v['agent']}: {v.get('rule_description','')[:100]}")

# Guard effectiveness misses
ge = s.get("guard_effectiveness", {})
by_agent = ge.get("by_agent", {})
for agent, stats in by_agent.items():
    if stats.get("missed", 0) > 0:
        issues.append(f"[Guard] {agent}: {stats['missed']}/{stats['scenarios']} scenarios missed")

# Self-improvement suggestions
si = s.get("self_improvement", {})
for sug in si.get("suggestions", []):
    issues.append(f"[History] {sug.get('agent','?')}/{sug.get('tool','?')}: {sug.get('suggestion','')[:80]}")

# Multi-agent review needs_fix
mar = s.get("multi_agent_review", {})
for nf in mar.get("needs_fix", []):
    for iss in nf.get("issues", []):
        issues.append(f"[Review] {iss}")

# Stage completeness issues
rlaif_viols = rlaif.get("violations", [])
for v in rlaif_viols:
    if v.get("principle") in ("C3", "C4"):
        issues.append(f"[Structure] {v['agent']}: {v['detail']}")

# Dedup
seen = set()
unique = []
for i in issues:
    key = i[:120]
    if key not in seen:
        seen.add(key)
        unique.append(i)

# Stats
by_category = {}
for i in unique:
    cat = i.split("]")[0].replace("[", "")
    by_category[cat] = by_category.get(cat, 0) + 1

print(f"Total issues found: {len(unique)}")
print()
print("By category:")
for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
    print(f"  {cat:12s}: {count}")
print()

categories_order = ["RLAIF/critical", "Runtime", "Rule", "Guard", "RLAIF/warn", "Structure", "History", "Review"]
for cat in categories_order:
    matching = [i for i in unique if i.startswith(f"[{cat}]")]
    if matching:
        print(f"=== {cat} ({len(matching)}) ===")
        for m in matching:
            print(f"  {m}")
        print()
