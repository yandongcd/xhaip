"""Debug RuleEngine respiratory rules."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
from haip.togaf.rule_engine import RuleEngine

e = RuleEngine()
e.load_all()

# Check respiratory rules directly
dept = '呼吸内科'
if dept in e._rules:
    rules = e._rules[dept]
    print(f'Found {len(rules)} rule groups for {dept}')
    for rg in rules:
        print(f'  type={rg["rule_type"]} rules={len(rg.get("rules",[]))}')
else:
    print(f'{dept} NOT found in _rules')
    print(f'Available: {list(e._rules.keys())}')

# Test condition
rules = e.get_rules(dept, 'diagnosis')
print(f'\nget_rules({dept}, diagnosis): {len(rules)} groups')

# Test rule evaluation
if rules:
    rg = rules[0]
    r = rg['rules'][0]
    p = {'diagnosis': 'COPD急性加重', 'lab_results': {'FEV1': 26.2}}
    ok, desc = e._check_condition(r['condition'], p)
    print(f'Rule {r["id"]}: matched={ok} — {desc}')

# Full pipeline
p2 = {'diagnosis': 'COPD急性加重', 'lab_results': {'FEV1': 26.2, 'PaO2': 39, 'WBC': 16, 'CRP': 160}}
pipeline = e.run_pipeline(p2, department=dept)
s = pipeline.summary()
print(f'\nPipeline summary: {s}')
