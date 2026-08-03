import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packages" / "haip-core"))
from haip.meta_harness import MetaHarness


def summarize_stage(key, st):
    if key == "auto_testing":
        return f"passed={st.get('passed',0)}/{st.get('total_tests',0)}"
    if key == "runtime_a2a":
        return f"passed={st.get('passed',0)}/{st.get('total',0)}  timing={st.get('timing',{}).get('p50_ms',0)}ms"
    if key == "rlaif_audit":
        return f"critical={st.get('critical_violations',0)} total={st.get('total_violations',0)}"
    if key == "rule_compliance":
        return f"passed={st.get('passed',0)}/{st.get('total_rules_checked',0)}"
    if key == "guard_effectiveness":
        return f"blocked={st.get('correctly_blocked',0)} missed={st.get('missed_blocks',0)} false={st.get('false_positives',0)}"
    if key == "quality_intelligence":
        return f"pass_rate={st.get('pass_rate',0)}% trend={st.get('trend','?')}"
    if key == "causal_diagnosis":
        return f"clusters={st.get('clusters_count',0)} failed={st.get('failed_cases',0)}"
    return ""

mh = MetaHarness()
r = mh.run_full_cycle(run_proposer=False)

s = r["stages"]
print(f"Version: {r['version']}")
print(f"Unified: {r['unified_score']}")
print(f"Duration: {r['duration_ms']}ms")
print()

stages_to_show = [
    ("auto_testing", "Static"),
    ("runtime_a2a", "Runtime"),
    ("rlaif_audit", "RLAIF"),
    ("rule_compliance", "RuleComp"),
    ("guard_effectiveness", "GuardEff"),
    ("quality_intelligence", "QualIntel"),
    ("causal_diagnosis", "CausalDiag"),
]

for key, label in stages_to_show:
    st = s.get(key, {})
    print(f"  [{label:12s}] score={st.get('score','?'):>3}%  {summarize_stage(key, st)}")

print()
print("Top actions:")
for a in r.get("top_actions", [])[:8]:
    print(f"  - {a}")
