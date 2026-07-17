"""Debug RuleEngine evaluation."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "packages" / "haip-core"))
from haip.togaf.rule_engine import RuleEngine
import json

engine = RuleEngine()
engine.load_all()

# Test with real patient data
with open(ROOT / "packages" / "haip-hospital" / "data" / "patients.json", encoding='utf-8') as f:
    patients = json.load(f)['patients']

# Match patients to rules
matched = 0
total = 0
for p in patients:
    dept = p.get('department', '')
    if dept not in engine._rules:
        continue
    total += 1
    pipeline = engine.run_pipeline(p, department=dept)
    s = pipeline.summary()
    diag = s.get('diagnosis', {})
    if diag:
        matched += 1
        print(f'{p["patient_id"]}: {p["diagnosis"][:20]} → {diag.get("diagnosis","?")} ({diag.get("severity","?")})')

print(f'\nMatched: {matched}/{total} patients')
print(f'Rules loaded: {len(engine._rules)} departments')
